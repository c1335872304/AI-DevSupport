from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GenerationState, SupportHandoff, User

VALID_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}


def serialize_handoff(row: SupportHandoff) -> dict:
    return {
        "handoffId": row.handoff_id,
        "userId": row.user_id,
        "conversationId": row.conversation_id,
        "generationId": row.generation_id,
        "category": row.category,
        "priority": row.priority,
        "status": row.status,
        "reason": row.reason,
        "summary": row.summary,
        "requestedBy": row.requested_by,
        "assignedTo": row.assigned_to,
        "resolutionNote": row.resolution_note,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


async def create_handoff(
    db: AsyncSession,
    user: User,
    *,
    generation_id: str | None,
    reason: str,
    summary: str,
    category: str = "GENERAL",
    priority: str = "NORMAL",
    requested_by: str = "AI",
) -> SupportHandoff:
    reason = reason.strip()[:2000]
    summary = summary.strip()[:6000]
    if not reason or not summary:
        raise ValueError("reason and summary are required")
    category = (category or "GENERAL").strip().upper()[:64]
    priority = (priority or "NORMAL").strip().upper()
    if priority not in VALID_PRIORITIES:
        raise ValueError("invalid priority")

    # Tool retries must not generate duplicate human tickets for one Agent generation.
    if generation_id:
        existing = await db.scalar(
            select(SupportHandoff).where(
                SupportHandoff.generation_id == generation_id,
                SupportHandoff.user_id == str(user.id),
            )
        )
        if existing:
            return existing

    conversation_id = None
    if generation_id:
        generation = await db.get(GenerationState, generation_id)
        if generation and generation.user_id == str(user.id):
            conversation_id = generation.conversation_id

    row = SupportHandoff(
        handoff_id="CS_" + uuid.uuid4().hex[:20],
        user_id=str(user.id),
        conversation_id=conversation_id,
        generation_id=generation_id,
        category=category,
        priority=priority,
        status="OPEN",
        reason=reason,
        summary=summary,
        requested_by=(requested_by or "AI")[:20],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_user_handoff(db: AsyncSession, user: User, handoff_id: str | None = None) -> SupportHandoff | None:
    stmt = select(SupportHandoff)
    if user.role != "ADMIN":
        stmt = stmt.where(SupportHandoff.user_id == str(user.id))
    if handoff_id:
        stmt = stmt.where(SupportHandoff.handoff_id == handoff_id)
    return await db.scalar(stmt.order_by(SupportHandoff.created_at.desc()).limit(1))


async def update_handoff(
    db: AsyncSession,
    row: SupportHandoff,
    *,
    status: str | None = None,
    assigned_to: str | None = None,
    resolution_note: str | None = None,
) -> SupportHandoff:
    if status is not None:
        normalized = status.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError("invalid status")
        row.status = normalized
    if assigned_to is not None:
        row.assigned_to = assigned_to.strip()[:64] or None
    if resolution_note is not None:
        row.resolution_note = resolution_note.strip()[:6000] or None
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row
