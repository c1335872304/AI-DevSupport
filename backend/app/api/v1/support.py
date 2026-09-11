from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import admin_user, current_user
from app.core.response import ok
from app.db.models import SupportHandoff, User
from app.db.session import get_db
from app.support.handoff import serialize_handoff, serialize_handoff_list_item, update_handoff

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
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    keyword: str | None = Query(None, max_length=200),
    user_id: str | None = Query(None, alias="userId", max_length=64),
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(SupportHandoff.status == status.strip().upper())
    if priority:
        filters.append(SupportHandoff.priority == priority.strip().upper())
    if category:
        filters.append(SupportHandoff.category == category.strip().upper())
    if user_id:
        filters.append(SupportHandoff.user_id == user_id.strip())
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(
            SupportHandoff.handoff_id.ilike(pattern),
            SupportHandoff.user_id.ilike(pattern),
            SupportHandoff.summary.ilike(pattern),
            SupportHandoff.reason.ilike(pattern),
        ))

    count_stmt = select(func.count()).select_from(SupportHandoff)
    rows_stmt = select(SupportHandoff).order_by(SupportHandoff.created_at.desc()).offset((page - 1) * size).limit(size)
    if filters:
        count_stmt = count_stmt.where(*filters)
        rows_stmt = rows_stmt.where(*filters)
    total = int((await db.scalar(count_stmt)) or 0)
    status_counts_stmt = select(SupportHandoff.status, func.count()).group_by(SupportHandoff.status)
    priority_counts_stmt = select(SupportHandoff.priority, func.count()).group_by(SupportHandoff.priority)
    if filters:
        status_counts_stmt = status_counts_stmt.where(*filters)
        priority_counts_stmt = priority_counts_stmt.where(*filters)
    status_counts = {str(value): int(count) for value, count in (await db.execute(status_counts_stmt)).all()}
    priority_counts = {str(value): int(count) for value, count in (await db.execute(priority_counts_stmt)).all()}
    rows = list((await db.scalars(rows_stmt)).all())

    numeric_user_ids = {int(row.user_id) for row in rows if row.user_id.isdigit()}
    users_by_id: dict[str, str] = {}
    if numeric_user_ids:
        users = list((await db.scalars(select(User).where(User.id.in_(numeric_user_ids)))).all())
        users_by_id = {str(item.id): item.username for item in users}

    data = [serialize_handoff_list_item(row, username=users_by_id.get(row.user_id)) for row in rows]
    return ok({
        "content": data,
        "data": data,
        "number": page,
        "size": size,
        "totalElements": total,
        "statistics": {"status": status_counts, "priority": priority_counts},
    })


@router.get("/admin/handoffs/{handoff_id}")
async def admin_handoff(
    handoff_id: str,
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(SupportHandoff, handoff_id)
    if not row:
        raise HTTPException(status_code=404, detail="Support handoff not found")
    payload = serialize_handoff(row)
    user = await db.get(User, int(row.user_id)) if row.user_id.isdigit() else None
    payload["username"] = user.username if user else None
    return ok(payload)


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
