"""Durable approval execution, leases, bounded retries and receipt reconciliation."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from uuid import uuid4

from sqlalchemy import func, or_, select, update

from app.core.config import get_settings
from app.db.models import ApprovalExecution, RefundApprovalPreview, SupportHandoff
from app.support.refund_preview import advance
from app.support.refund_sandbox import reconcile

logger = logging.getLogger(__name__)


async def database_now(db):
    return await db.scalar(select(func.current_timestamp()))


async def enqueue(db, request_id):
    # Caller holds the approval business-row lock; job and decision commit together.
    if not await db.scalar(select(ApprovalExecution).where(ApprovalExecution.request_id == request_id).with_for_update()):
        db.add(ApprovalExecution(request_id=request_id, next_attempt_at=await database_now(db)))
        await db.flush()


async def close_ticket(db, row):
    from app.support.handoff import update_handoff
    await db.execute(update(RefundApprovalPreview).where(RefundApprovalPreview.request_id == row.request_id)
                     .values(updated_at=RefundApprovalPreview.updated_at))
    await db.refresh(row)
    if not row.closure_status:
        ticket = await db.get(SupportHandoff, row.handoff_id)
        if ticket and ticket.user_id == row.user_id and ticket.status in {'OPEN', 'IN_PROGRESS', 'RESOLVED'}:
            await update_handoff(db, ticket, status='CLOSED', resolution_note=row.decision_note or row.reason,
                                 actor_id=row.decided_by, source='approval')
            row.closure_status = 'TICKET_CLOSED'
        elif ticket and ticket.status == 'CLOSED' and ticket.user_id == row.user_id:
            # A previous worker may have committed closure before its result acknowledgement.
            row.closure_status = 'TICKET_CLOSED'
        else:
            row.closure_status = 'TICKET_UNAVAILABLE'
        await db.commit()
    return row.closure_status


async def execute(db, row, status, *, allow_submit=False, lease_owner=None):
    if lease_owner:
        now = await database_now(db)
        owned = await db.execute(update(ApprovalExecution).where(
            ApprovalExecution.request_id == row.request_id, ApprovalExecution.owner == lease_owner,
            ApprovalExecution.status == 'RUNNING', ApprovalExecution.lease_until > now,
        ).values(lease_until=now + timedelta(seconds=60)))
        await db.commit()
        if not owned.rowcount:
            return 'EXECUTION_SUPERSEDED', None
    receipt = None
    if status == 'APPROVED_PREVIEW':
        if row.handoff_id:
            status = await close_ticket(db, row) if allow_submit else row.closure_status or status
        else:
            status, receipt = await reconcile(db, row, get_settings().refund_sandbox_url, allow_submit=allow_submit)
    if allow_submit:
        terminal = status not in {'PENDING_APPROVAL', 'REFUND_RECONCILING'}
        job = await db.get(ApprovalExecution, row.request_id, populate_existing=True)
        attempts = job.attempts if job else 0
        next_status = 'COMPLETED' if terminal else ('NEEDS_REVIEW' if attempts >= 12 else 'PENDING')
        predicates = [ApprovalExecution.request_id == row.request_id, ApprovalExecution.status != 'COMPLETED']
        if lease_owner:
            predicates.append(ApprovalExecution.owner == lease_owner)
        elif not terminal:
            predicates.append(ApprovalExecution.status != 'RUNNING')
        now = await database_now(db)
        await db.execute(update(ApprovalExecution).where(*predicates).values(status=next_status, outcome=status,
                 next_attempt_at=now + timedelta(seconds=min(300, max(5, 2 ** min(attempts, 8)))), owner=None, lease_until=None))
        await db.commit()
    return status, receipt


async def run_once(*, sessions=None):
    from app.db.session import SessionLocal
    sessions = sessions or SessionLocal
    async with sessions() as db:
        # Also recovers decisions created before this queue existed.
        missing = (await db.scalars(select(RefundApprovalPreview).outerjoin(
            ApprovalExecution, ApprovalExecution.request_id == RefundApprovalPreview.request_id,
        ).where(RefundApprovalPreview.decision_id.is_not(None), ApprovalExecution.request_id.is_(None))
            .limit(100))).all()
        for row in missing:
            await db.execute(update(RefundApprovalPreview).where(RefundApprovalPreview.request_id == row.request_id)
                             .values(updated_at=RefundApprovalPreview.updated_at))
            await enqueue(db, row.request_id)
        await db.commit()
        now = await database_now(db)
        ids = (await db.scalars(select(ApprovalExecution.request_id).where(
            ApprovalExecution.status.in_(['PENDING', 'RUNNING']),
            ApprovalExecution.next_attempt_at <= now,
            or_(ApprovalExecution.lease_until.is_(None), ApprovalExecution.lease_until < now),
        ).order_by(ApprovalExecution.next_attempt_at).limit(50))).all()
    completed = 0
    for request_id in ids:
        owner = uuid4().hex
        async with sessions() as db:
            now = await database_now(db)
            claimed = await db.execute(update(ApprovalExecution).where(
                ApprovalExecution.request_id == request_id,
                ApprovalExecution.status.in_(['PENDING', 'RUNNING']),
                ApprovalExecution.next_attempt_at <= now,
                or_(ApprovalExecution.lease_until.is_(None), ApprovalExecution.lease_until < now),
            ).values(status='RUNNING', owner=owner, lease_until=now + timedelta(seconds=60),
                     attempts=ApprovalExecution.attempts + 1))
            await db.commit()
            if not claimed.rowcount:
                continue
        try:
            async with sessions() as db:
                row = await db.get(RefundApprovalPreview, request_id)
                if not row or not row.decision_id:
                    raise RuntimeError('Approval decision missing')
                status = await advance(db, request_id, get_settings().refund_checkpoint_path)
                outcome, _ = await execute(db, row, status, allow_submit=True, lease_owner=owner)
                if outcome != "EXECUTION_SUPERSEDED":
                    completed += 1
        except Exception as exc:
            logger.warning('Approval execution deferred request=%s error=%s', request_id, type(exc).__name__)
            async with sessions() as db:
                job = await db.get(ApprovalExecution, request_id)
                attempts = job.attempts if job else 1
                now = await database_now(db)
                await db.execute(update(ApprovalExecution).where(
                    ApprovalExecution.request_id == request_id, ApprovalExecution.owner == owner,
                ).values(status='NEEDS_REVIEW' if attempts >= 12 else 'PENDING',
                         last_error=type(exc).__name__, owner=None, lease_until=None,
                         next_attempt_at=now + timedelta(seconds=min(300, 2 ** min(attempts, 8)))))
                await db.commit()
    return completed


async def recovery_loop():
    while True:
        try:
            if get_settings().refund_preview_enabled:
                await run_once()
        except Exception:
            logger.exception('Approval recovery scan failed')
        await asyncio.sleep(5)
