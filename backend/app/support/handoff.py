from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.db.models import (
    DiagnosisExecution,
    DiagnosisSession,
    DiagnosisTurn,
    GenerationState,
    SupportHandoff,
    User,
)
from app.support.handoff_contract import HandoffAuthorization, VALID_PRIORITIES, normalize_handoff

if TYPE_CHECKING:
    from app.diagnosis.execution import Lease

logger = logging.getLogger(__name__)

VALID_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}


class HandoffPayloadConflict(ValueError):
    """A generation already created a ticket with different input."""


def _check_generation_replay(
    row: SupportHandoff, *, reason: str, summary: str, category: str, priority: str, requested_by: str,
) -> None:
    if row.diagnosis_id is None and (
        row.reason, row.summary, row.category, row.priority, row.requested_by
    ) != (reason, summary, category, priority, requested_by):
        logger.info("Handoff conflict generation=%s ticket=%s", row.generation_id, row.handoff_id)
        raise HandoffPayloadConflict("Handoff input differs from the ticket already created for this generation")


def serialize_handoff(row: SupportHandoff) -> dict:
    return {
        "handoffId": row.handoff_id,
        "userId": row.user_id,
        "conversationId": row.conversation_id,
        "generationId": row.generation_id,
        "diagnosisId": row.diagnosis_id,
        "category": row.category,
        "priority": row.priority,
        "status": row.status,
        "reason": row.reason,
        "summary": row.summary[:500],
        "requestedBy": row.requested_by,
        "assignedTo": row.assigned_to,
        "resolutionNote": row.resolution_note,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def serialize_handoff_list_item(row: SupportHandoff, *, username: str | None = None) -> dict:
    """Return the bounded fields needed by the administrator ticket table.

    Full handoff reasons and resolution notes are intentionally kept on the
    detail endpoint. This prevents an administrative list request from
    becoming a bulk export of customer conversation content.
    """
    return {
        "handoffId": row.handoff_id,
        "userId": row.user_id,
        "username": username,
        "conversationId": row.conversation_id,
        "generationId": row.generation_id,
        "diagnosisId": row.diagnosis_id,
        "category": row.category,
        "priority": row.priority,
        "status": row.status,
        # The list endpoint is intentionally bounded. Full summaries are
        # available only from the authorized detail endpoint.
        "summary": row.summary[:500],
        "requestedBy": row.requested_by,
        "assignedTo": row.assigned_to,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


async def create_handoff(
    db: AsyncSession,
    user: User,
    *,
    generation_id: str | None,
    reason: str = "",
    summary: str = "",
    category: str = "GENERAL",
    priority: str = "NORMAL",
    diagnosis_lease: Lease | None = None,
    authorization: HandoffAuthorization | None = None,
) -> SupportHandoff:
    def denied(reason: str) -> PermissionError:
        logger.info("Handoff denied generation=%s reason=%s", generation_id, reason)
        return PermissionError(reason)

    # The case identity survives generations and restarts. It is server-derived.
    if not generation_id:
        raise denied("Handoff creation requires a generation")
    turn = await db.get(DiagnosisTurn, generation_id)
    case = await db.get(DiagnosisSession, turn.diagnosis_id) if turn else None
    if turn and not case:
        raise denied("Diagnostic handoff unavailable")
    if case and case.user_id != str(user.id):
        raise denied("Diagnostic handoff owner mismatch")
    diagnosis_id = case.diagnosis_id if case else None
    generation = await db.get(GenerationState, generation_id) if not case else None
    if not case and (not generation or generation.user_id != str(user.id)):
        raise denied("Handoff generation unavailable")
    existing_query = select(SupportHandoff).where(SupportHandoff.user_id == str(user.id))
    if diagnosis_id:
        existing_query = existing_query.where(SupportHandoff.diagnosis_id == diagnosis_id)
    else:
        existing_query = existing_query.where(SupportHandoff.generation_id == generation_id)
    existing = await db.scalar(existing_query)
    if existing and case:
        await attach_diagnostic_handoff(db, existing)
        logger.info("Handoff replay generation=%s ticket=%s", generation_id, existing.handoff_id)
        return existing
    if case:
        from app.diagnosis.execution import ExecutionLost, guard
        from app.diagnosis.loop import handoff_summary

        if not diagnosis_lease or diagnosis_lease.generation_id != generation_id:
            raise denied("Diagnostic handoff requires its execution lease")
        try:
            execution, case, _ = await guard(db, diagnosis_lease)
        except ExecutionLost as exc:
            raise denied("Diagnostic handoff lease unavailable") from exc
        decision = json.loads(case.workflow_json).get("decision") or {}
        if execution.status != "HANDOFF_PENDING" or not decision.get("handoffRequired"):
            raise denied("Diagnostic handoff intent is unavailable")
        reason = "; ".join(decision.get("handoffReasons") or ["需要人工核查"])
        summary = handoff_summary(case)
        category, priority = "API", "NORMAL"
        conversation_id = case.conversation_id
    else:
        conversation_id = generation.conversation_id

    payload = normalize_handoff(reason, summary, category, priority)
    if not payload["reason"] or not payload["summary"]:
        raise ValueError("reason and summary are required")
    if payload["priority"] not in VALID_PRIORITIES:
        raise ValueError("invalid priority")
    if not case and (not authorization or not authorization.permits(str(user.id), generation_id, payload)):
        raise denied("Handoff authorization missing, expired or mismatched")
    replay_input = {**payload, "requested_by": "AI"}
    if existing:
        _check_generation_replay(existing, **replay_input)
        logger.info("Handoff replay generation=%s ticket=%s", generation_id, existing.handoff_id)
        return existing
    if not case:
        # Fence cancellation and terminal updates in the same transaction as
        # the ticket insert. The conditional write also takes the SQLite lock.
        active_generation = await db.execute(
            update(GenerationState)
            .where(
                GenerationState.generation_id == generation_id,
                GenerationState.user_id == str(user.id),
                GenerationState.status == "STREAMING",
            )
            .values(updated_at=GenerationState.updated_at)
        )
        if active_generation.rowcount != 1:
            raise denied("Handoff generation is not active")

    auth_id = f"lease:{diagnosis_lease.epoch}" if case else authorization.authorization_id
    logger.info("Handoff authorized generation=%s diagnosis=%s authorization=%s", generation_id, diagnosis_id, auth_id)
    row = SupportHandoff(
        handoff_id="CS_" + uuid.uuid4().hex[:20],
        user_id=str(user.id),
        conversation_id=conversation_id,
        generation_id=generation_id,
        diagnosis_id=diagnosis_id,
        status="OPEN",
        **replay_input,
    )
    db.add(row)
    from app.db.models import SupportHandoffAudit
    db.add(SupportHandoffAudit(handoff_id=row.handoff_id, actor_id=str(user.id), source="agent-create",
        before_json="{}", after_json=json.dumps({"status": "OPEN", "assignedTo": None, "resolutionNote": None})))
    try:
        await db.commit()
        await db.refresh(row)
    except Exception:
        # Covers a racing insert AND a committed write with a lost acknowledgement.
        # Never retry the write until the unique identity has been checked.
        await db.rollback()
        existing = await db.scalar(existing_query)
        if not existing:
            raise
        _check_generation_replay(existing, **replay_input)
        row = existing
        logger.info("Handoff reconciled generation=%s ticket=%s", generation_id, row.handoff_id)
    await attach_diagnostic_handoff(db, row)
    logger.info("Handoff confirmed generation=%s ticket=%s", generation_id, row.handoff_id)
    return row


async def attach_diagnostic_handoff(db, row):
    if not row.diagnosis_id:
        return
    from app.diagnosis.service import TERMINAL, lock_conversation, transition

    case = await db.get(DiagnosisSession, row.diagnosis_id)
    if not case or case.user_id != row.user_id or case.conversation_id != row.conversation_id:
        raise PermissionError("Handoff case binding mismatch")
    if not await lock_conversation(db, row.user_id, case.conversation_id):
        raise PermissionError("Diagnostic conversation unavailable")
    await db.refresh(case)
    if case.status not in TERMINAL:
        transition(
            db, case, "HANDED_OFF", "PERSISTED_HANDOFF", case.last_generation_id, handoff_confirmed=True
        )
        case.next_action = "人工工单已创建，等待人工核查"
        await db.execute(
            update(DiagnosisExecution)
            .where(
                DiagnosisExecution.diagnosis_id == case.diagnosis_id,
                DiagnosisExecution.status == "HANDOFF_PENDING",
            )
            .values(status="COMPLETED", owner=None, lease_until=None)
        )
        await db.commit()


async def get_user_handoff(
    db: AsyncSession, user: User, handoff_id: str | None = None
) -> SupportHandoff | None:
    stmt = select(SupportHandoff)
    if user.role != "ADMIN":
        stmt = stmt.where(SupportHandoff.user_id == str(user.id))
    if handoff_id:
        stmt = stmt.where(SupportHandoff.handoff_id == handoff_id)
    return await db.scalar(stmt.order_by(SupportHandoff.created_at.desc()).limit(1))


async def update_handoff(
    db: AsyncSession, row: SupportHandoff, *, status: str | None = None,
    assigned_to: str | None = None, resolution_note: str | None = None,
    actor_id: str, source: str = "operator", expected_status: str | None = None,
) -> SupportHandoff:
    from app.db.models import SupportHandoffAudit
    await db.execute(update(SupportHandoff).where(SupportHandoff.handoff_id == row.handoff_id)
                     .values(updated_at=SupportHandoff.updated_at))
    await db.refresh(row)
    before = {"status": row.status, "assignedTo": row.assigned_to, "resolutionNote": row.resolution_note}
    if expected_status and expected_status != row.status:
        raise ValueError("Ticket changed; refresh before editing")
    target = status.strip().upper() if status is not None else row.status
    transitions = {"OPEN": {"IN_PROGRESS"}, "IN_PROGRESS": {"OPEN", "RESOLVED"},
                   "RESOLVED": {"IN_PROGRESS", "CLOSED"}, "CLOSED": set()}
    approval_close = source == "approval" and target == "CLOSED" and row.status in {"OPEN", "IN_PROGRESS", "RESOLVED"}
    if target not in VALID_STATUSES or (target != row.status and target not in transitions.get(row.status, set()) and not approval_close):
        raise ValueError("Invalid ticket status transition")
    note = resolution_note.strip()[:6000] if resolution_note is not None else row.resolution_note
    assignment = (assigned_to.strip()[:64] or None) if assigned_to is not None else row.assigned_to
    after = {"status": target, "assignedTo": assignment, "resolutionNote": note}
    if before == after:
        return row
    if row.status == "CLOSED":
        raise ValueError("Closed tickets are immutable")
    if target in {"RESOLVED", "CLOSED"} and not note:
        raise ValueError("Resolution note required")
    row.status, row.assigned_to, row.resolution_note = target, assignment, note
    row.updated_at = utcnow()
    db.add(SupportHandoffAudit(handoff_id=row.handoff_id, actor_id=actor_id, source=source,
                              before_json=json.dumps(before, ensure_ascii=False),
                              after_json=json.dumps(after, ensure_ascii=False)))
    await db.commit()
    await db.refresh(row)
    return row
