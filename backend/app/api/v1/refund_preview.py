from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated

from app.core.config import get_settings
from app.core.deps import admin_user, current_user
from app.core.response import ok
from app.db.models import ConversationSession, RefundApprovalPreview, RefundSandboxIntent, SupportHandoff, SupportInvoice, User
from app.db.session import get_db
from app.support.refund_preview import advance
from app.support.refund_sandbox import minor_units, reconcile


def enabled() -> None:
    if not get_settings().refund_preview_enabled:
        raise HTTPException(404, "Refund approval preview unavailable")


router = APIRouter(prefix="/support", tags=["refund-approval-preview"], dependencies=[Depends(enabled)])
discovery_router = APIRouter(prefix="/support", tags=["refund-approval-preview"])
Key = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoiceId: Key | None = None
    handoffId: Key | None = None
    conversationId: Key | None = None
    requestKey: Key
    reason: Note

    @model_validator(mode="after")
    def one_target(self):
        if bool(self.invoiceId) == bool(self.handoffId):
            raise ValueError("Select exactly one approval target")
        return self


class RefundDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    note: Note


def payload(row: RefundApprovalPreview, status: str) -> dict:
    data = {"requestId": row.request_id, "invoiceId": row.invoice_id, "status": status}
    if row.conversation_id:
        data["conversationId"] = row.conversation_id
    if row.handoff_id:
        data["handoffId"] = row.handoff_id
    return data


def approval_status(row: RefundApprovalPreview) -> str:
    return {"approve": "APPROVED_PREVIEW", "reject": "REJECTED"}.get(row.decision, "PENDING_APPROVAL")


def summary(row: RefundApprovalPreview, intent: RefundSandboxIntent | None) -> dict:
    status = approval_status(row)
    if status == "APPROVED_PREVIEW":
        if row.closure_status:
            status = row.closure_status
        elif intent and intent.refund_id:
            return {**payload(row, "SANDBOX_REFUNDED"), "receipt": {
                "refundId": intent.refund_id, "amountMinor": intent.amount_minor, "currency": "CNY",
            }}
        elif intent:
            status = "SANDBOX_REJECTED" if intent.rejection else "REFUND_RECONCILING"
    data = payload(row, status)
    if intent:
        data["amountMinor"] = intent.amount_minor
        data["currency"] = "CNY"
    return data


def with_intents():
    return select(RefundApprovalPreview, RefundSandboxIntent).outerjoin(
        RefundSandboxIntent, RefundSandboxIntent.request_id == RefundApprovalPreview.request_id,
    )


async def require_conversation(db: AsyncSession, conversation_id: str, user_id: str) -> None:
    row = await db.get(ConversationSession, conversation_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Conversation not found")


async def close_ticket(db: AsyncSession, request_id: str) -> str:
    await db.execute(update(RefundApprovalPreview).where(RefundApprovalPreview.request_id == request_id)
                     .values(updated_at=RefundApprovalPreview.updated_at))
    row = await db.get(RefundApprovalPreview, request_id, populate_existing=True)
    if not row.closure_status:
        applied = await db.execute(update(SupportHandoff).where(
            SupportHandoff.handoff_id == row.handoff_id, SupportHandoff.user_id == row.user_id,
            SupportHandoff.status.in_(("OPEN", "IN_PROGRESS", "RESOLVED")),
        ).values(status="CLOSED"))
        row.closure_status = "TICKET_CLOSED" if applied.rowcount else "TICKET_UNAVAILABLE"
    await db.commit()
    return row.closure_status


async def result(db: AsyncSession, row: RefundApprovalPreview, status: str, *, allow_submit: bool = False):
    if status == "APPROVED_PREVIEW":
        if row.handoff_id:
            outcome = await close_ticket(db, row.request_id) if allow_submit else row.closure_status or status
            return ok(payload(row, outcome))
        status, receipt = await reconcile(db, row, get_settings().refund_sandbox_url, allow_submit=allow_submit)
        if receipt:
            return ok({**payload(row, status), "receipt": receipt.model_dump()})
    return ok(payload(row, status))


@discovery_router.get("/approval-capabilities")
async def capabilities(user: User = Depends(current_user)):
    return ok({"enabled": get_settings().refund_preview_enabled})


@router.get("/refund-options")
async def options(conversationId: Key, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    uid = str(user.id)
    await require_conversation(db, conversationId, uid)
    invoices = (await db.scalars(select(SupportInvoice).where(SupportInvoice.user_id == uid,
                SupportInvoice.status == "PAID").order_by(SupportInvoice.month.desc()).limit(25))).all()
    tickets = (await db.scalars(select(SupportHandoff).where(
        SupportHandoff.user_id == uid, SupportHandoff.conversation_id == conversationId,
        SupportHandoff.status.in_(("OPEN", "IN_PROGRESS", "RESOLVED")),
    ).order_by(SupportHandoff.created_at.desc()).limit(25))).all()
    return ok({"invoices": [{"id": item.id, "month": item.month, "amount": item.amount} for item in invoices],
               "tickets": [{"id": item.handoff_id, "summary": item.summary[:120]} for item in tickets]})


@router.get("/refund-requests")
async def list_for_chat(conversationId: Key, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await require_conversation(db, conversationId, str(user.id))
    rows = (await db.execute(with_intents().where(
        RefundApprovalPreview.user_id == str(user.id), RefundApprovalPreview.conversation_id == conversationId,
    ).order_by(RefundApprovalPreview.created_at.desc()).limit(25))).all()
    return ok([summary(row, intent) for row, intent in rows])


@router.get("/admin/refund-requests")
async def review_queue(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db),
                       offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    rows = (await db.execute(with_intents()
            .order_by(case((
                (RefundApprovalPreview.decision == "approve") &
                (RefundApprovalPreview.closure_status.is_(None)) &
                (RefundSandboxIntent.refund_id.is_(None)) &
                (RefundSandboxIntent.rejection.is_(None)), 0,
            ), (RefundApprovalPreview.decision_id.is_(None), 1), else_=2),
                RefundApprovalPreview.created_at.desc(), RefundApprovalPreview.request_id)
            .offset(offset).limit(limit))).all()
    return ok([{**summary(row, intent), "userId": row.user_id, "reason": row.reason,
                "decision": row.decision, "decidedBy": row.decided_by, "decisionNote": row.decision_note,
                "createdAt": row.created_at.isoformat()} for row, intent in rows])


@router.post("/refund-requests")
async def submit(body: RefundRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user_id = str(user.id)
    lookup = select(RefundApprovalPreview).where(
        RefundApprovalPreview.user_id == user_id, RefundApprovalPreview.request_key == body.requestKey,
    )
    row = await db.scalar(lookup)
    if not row:
        if body.conversationId:
            await require_conversation(db, body.conversationId, user_id)
        invoice = None
        if body.invoiceId:
            invoice = await db.get(SupportInvoice, body.invoiceId)
            if not invoice or invoice.user_id != user_id:
                raise HTTPException(404, "Invoice not found")
            if invoice.status != "PAID":
                raise HTTPException(409, "Preview requires a paid invoice")
        else:
            ticket = await db.get(SupportHandoff, body.handoffId)
            if not ticket or ticket.user_id != user_id or not body.conversationId or ticket.conversation_id != body.conversationId:
                raise HTTPException(404, "Conversation ticket not found")
            if ticket.status not in {"OPEN", "IN_PROGRESS", "RESOLVED"}:
                raise HTTPException(409, "Ticket cannot be closed")
        row = RefundApprovalPreview(
            request_id=uuid4().hex, user_id=user_id, invoice_id=body.invoiceId,
            handoff_id=body.handoffId, conversation_id=body.conversationId,
            request_key=body.requestKey, reason=body.reason,
        )
        db.add(row)
        sandbox_amount = None
        if get_settings().refund_sandbox_url and invoice and invoice.id.startswith("sandbox-"):
            try:
                sandbox_amount = minor_units(invoice.amount)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
        try:
            await db.flush()
            if sandbox_amount is not None:
                db.add(RefundSandboxIntent(request_id=row.request_id, payment_id=row.invoice_id, amount_minor=sandbox_amount))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            row = await db.scalar(lookup)
            if not row:
                raise
    if (row.invoice_id, row.handoff_id, row.conversation_id, row.reason) != (
        body.invoiceId, body.handoffId, body.conversationId, body.reason,
    ):
        raise HTTPException(409, "Request key belongs to different input")
    status = await advance(db, row.request_id, get_settings().refund_checkpoint_path)
    return await result(db, row, status)


@router.get("/refund-requests/{request_id}")
async def detail(request_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(RefundApprovalPreview, request_id)
    if not row or row.user_id != str(user.id):
        raise HTTPException(404, "Refund request not found")
    return await result(db, row, approval_status(row))


@router.get("/admin/refund-requests/{request_id}")
async def review(request_id: str, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(RefundApprovalPreview, request_id)
    if not row:
        raise HTTPException(404, "Refund request not found")
    return ok({"requestId": row.request_id, "invoiceId": row.invoice_id, "userId": row.user_id, "reason": row.reason,
               "decisionId": row.decision_id, "decision": row.decision, "decidedBy": row.decided_by})


@router.post("/admin/refund-requests/{request_id}/decision")
async def decide(
    request_id: str, body: RefundDecision, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db),
):
    if not await db.get(RefundApprovalPreview, request_id):
        raise HTTPException(404, "Refund request not found")
    checkpoint = get_settings().refund_checkpoint_path
    await advance(db, request_id, checkpoint)
    await db.execute(
        update(RefundApprovalPreview)
        .where(RefundApprovalPreview.request_id == request_id, RefundApprovalPreview.decision_id.is_(None))
        .values(decision_id=uuid4().hex, decision=body.decision, decided_by=str(admin.id), decision_note=body.note)
    )
    row = await db.get(RefundApprovalPreview, request_id, populate_existing=True)
    if (row.decision, row.decided_by, row.decision_note) != (body.decision, str(admin.id), body.note):
        raise HTTPException(409, "Refund request already decided")
    await db.commit()
    status = await advance(db, request_id, checkpoint)
    return await result(db, row, status, allow_submit=True)


@router.post("/admin/refund-requests/{request_id}/resume")
async def resume(request_id: str, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(RefundApprovalPreview, request_id)
    if not row:
        raise HTTPException(404, "Refund request not found")
    if not row.decision_id:
        raise HTTPException(409, "Approval decision required")
    # The existing decision and its author remain the sole execution authority.
    status = await advance(db, request_id, get_settings().refund_checkpoint_path)
    return await result(db, row, status, allow_submit=True)
