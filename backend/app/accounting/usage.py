from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMTokenReservation, User, UserTokenRecord


def estimate_tokens(text: str) -> int:
    text = text or ""
    # Conservative provider-agnostic estimate for mixed Chinese/English text.
    return max(1, (len(text) + 2) // 3)


class UsageService:
    async def ensure_llm_balance(self, user: User, minimum: int = 1) -> None:
        if int(user.llm_token_balance or 0) < max(1, minimum):
            raise HTTPException(status_code=402, detail="Insufficient LLM token balance")

    async def charge_llm(self, db: AsyncSession, user_id: int, tokens: int, reason: str, remark: str | None = None) -> int:
        amount = max(0, int(tokens))
        if amount == 0:
            return 0
        # Lock the balance row for the duration of the ledger write. Without this,
        # two concurrent generations can both read the same balance and overwrite
        # one another's deduction on transactional databases.
        user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user:
            return 0
        before = int(user.llm_token_balance or 0)
        charged = min(before, amount)
        user.llm_token_balance = before - charged
        db.add(UserTokenRecord(
            user_id=str(user.id), record_date=date.today(), token_type="LLM", change_type="CONSUME",
            request_count=1, amount=-charged, balance_before=before, balance_after=before - charged,
            reason=reason, remark=remark,
        ))
        await db.commit()
        return charged

    async def reserve_llm(self, db: AsyncSession, user_id: int, generation_id: str, tokens: int, reason: str) -> int:
        """Reserve a worst-case budget before an external LLM request starts."""
        amount = max(1, int(tokens))
        existing = await db.get(LLMTokenReservation, generation_id)
        if existing:
            return int(existing.reserved_tokens or 0)
        user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user or int(user.llm_token_balance or 0) < amount:
            raise HTTPException(status_code=402, detail="Insufficient LLM token balance for this request")
        before = int(user.llm_token_balance or 0)
        user.llm_token_balance = before - amount
        db.add(LLMTokenReservation(
            generation_id=generation_id,
            user_id=str(user_id),
            reserved_tokens=amount,
            settled_tokens=0,
            status="RESERVED",
        ))
        db.add(UserTokenRecord(
            user_id=str(user_id), record_date=date.today(), token_type="LLM", change_type="RESERVE",
            request_count=0, amount=0, balance_before=before, balance_after=before - amount,
            reason=reason, remark=f"reservation:{generation_id}",
        ))
        await db.commit()
        return amount

    async def settle_llm(self, db: AsyncSession, generation_id: str, actual_tokens: int, reason: str = "chat_generation") -> int:
        """Settle a reservation and return unused budget after a successful request."""
        reservation = await db.get(LLMTokenReservation, generation_id)
        if not reservation or reservation.status != "RESERVED":
            return int(reservation.settled_tokens or 0) if reservation else 0
        reserved = max(1, int(reservation.reserved_tokens or 0))
        requested = max(0, int(actual_tokens))
        user = await db.scalar(select(User).where(User.id == int(reservation.user_id)).with_for_update())
        if not user:
            reservation.status = "SETTLED"
            reservation.settled_tokens = 0
            await db.commit()
            return 0
        before = int(user.llm_token_balance or 0)
        if requested <= reserved:
            charged = requested
            refund = reserved - charged
            user.llm_token_balance = before + refund
            if refund:
                db.add(UserTokenRecord(
                    user_id=str(user.id), record_date=date.today(), token_type="LLM", change_type="REFUND",
                    request_count=0, amount=refund, balance_before=before, balance_after=before + refund,
                    reason=reason, remark=f"unused_reservation:{generation_id}",
                ))
        else:
            # The provider has already consumed the tokens. Charge the full reported
            # amount instead of silently undercharging when the reservation estimate
            # was too low; a negative balance becomes a debt that blocks the next run.
            extra = requested - reserved
            charged = reserved + extra
            user.llm_token_balance = before - extra
        db.add(UserTokenRecord(
            user_id=str(user.id), record_date=date.today(), token_type="LLM", change_type="CONSUME",
            request_count=1, amount=-charged, balance_before=before, balance_after=int(user.llm_token_balance or 0),
            reason=reason, remark=f"settlement:{generation_id}",
        ))
        reservation.settled_tokens = charged
        reservation.status = "SETTLED"
        await db.commit()
        return charged

    async def release_llm(self, db: AsyncSession, generation_id: str, reason: str = "failed_generation") -> int:
        """Return a still-reserved budget; safe to call repeatedly."""
        reservation = await db.get(LLMTokenReservation, generation_id)
        if not reservation or reservation.status != "RESERVED":
            return 0
        user = await db.scalar(select(User).where(User.id == int(reservation.user_id)).with_for_update())
        if user:
            before = int(user.llm_token_balance or 0)
            refund = max(0, int(reservation.reserved_tokens or 0))
            user.llm_token_balance = before + refund
            db.add(UserTokenRecord(
                user_id=str(user.id), record_date=date.today(), token_type="LLM", change_type="REFUND",
                request_count=0, amount=refund, balance_before=before, balance_after=before + refund,
                reason=reason, remark=f"released_reservation:{generation_id}",
            ))
        reservation.status = "RELEASED"
        reservation.settled_tokens = 0
        await db.commit()
        return int(reservation.reserved_tokens or 0)

    async def summary_for_user(self, db: AsyncSession, user: User) -> dict:
        rows = (await db.execute(
            select(UserTokenRecord.token_type, func.coalesce(func.sum(UserTokenRecord.amount), 0), func.coalesce(func.sum(UserTokenRecord.request_count), 0))
            .where(UserTokenRecord.user_id == str(user.id), UserTokenRecord.change_type == "CONSUME")
            .group_by(UserTokenRecord.token_type)
        )).all()
        usage = {str(t).upper(): {"used": abs(int(total or 0)), "requests": int(reqs or 0)} for t, total, reqs in rows}
        return {
            "llm": {"remainingTokens": int(user.llm_token_balance or 0), "usedTokens": usage.get("LLM", {}).get("used", 0), "requestCount": usage.get("LLM", {}).get("requests", 0)},
            "embedding": {"remainingTokens": int(user.embedding_token_balance or 0), "usedTokens": usage.get("EMBEDDING", {}).get("used", 0), "requestCount": usage.get("EMBEDDING", {}).get("requests", 0)},
        }


usage_service = UsageService()
