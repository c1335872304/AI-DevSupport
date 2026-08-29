from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import admin_user, current_user
from app.core.response import ok
from app.db.models import SupportHandoff, User
from app.db.session import get_db
from app.support.handoff import serialize_handoff, update_handoff

router = APIRouter(prefix="/support", tags=["support"])


class HandoffUpdate(BaseModel):
    status: str | None = None
    assignedTo: str | None = None
    resolutionNote: str | None = None


@router.get("/handoffs")
async def my_handoffs(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = list(
        (
            await db.scalars(
                select(SupportHandoff)
                .where(SupportHandoff.user_id == str(user.id))
                .order_by(SupportHandoff.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    return ok([serialize_handoff(row) for row in rows])


@router.get("/handoffs/{handoff_id}")
async def my_handoff(
    handoff_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(SupportHandoff, handoff_id)
    if not row or (user.role != "ADMIN" and row.user_id != str(user.id)):
        raise HTTPException(status_code=404, detail="Support handoff not found")
    return ok(serialize_handoff(row))


@router.get("/admin/handoffs")
async def admin_handoffs(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupportHandoff).order_by(SupportHandoff.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(SupportHandoff.status == status.strip().upper())
    rows = list((await db.scalars(stmt)).all())
    return ok([serialize_handoff(row) for row in rows])


@router.patch("/admin/handoffs/{handoff_id}")
async def admin_update_handoff(
    handoff_id: str,
    payload: HandoffUpdate,
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(SupportHandoff, handoff_id)
    if not row:
        raise HTTPException(status_code=404, detail="Support handoff not found")
    try:
        row = await update_handoff(
            db,
            row,
            status=payload.status,
            assigned_to=payload.assignedTo,
            resolution_note=payload.resolutionNote,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ok(serialize_handoff(row))
