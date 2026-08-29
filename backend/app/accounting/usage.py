from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserTokenRecord


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
        user = await db.get(User, user_id)
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
