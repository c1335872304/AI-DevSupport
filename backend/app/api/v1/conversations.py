from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import ConversationMessage, ConversationSession, User
from app.db.session import get_db

router = APIRouter(tags=["conversations"])


def serialize_session(item: ConversationSession) -> dict:
    return {
        "id": abs(hash(item.conversation_id)) % 2_000_000_000,
        "conversationId": item.conversation_id,
        "title": item.title,
        "status": item.status,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }


@router.get("/users/conversations")
async def list_sessions(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = list(
        (
            await db.scalars(
                select(ConversationSession)
                .where(ConversationSession.user_id == str(user.id))
                .order_by(ConversationSession.updated_at.desc())
            )
        ).all()
    )
    return ok([serialize_session(x) for x in rows])


@router.post("/users/conversations")
async def create_session(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = ConversationSession(conversation_id=uuid.uuid4().hex, user_id=str(user.id), title="新对话", status="ACTIVE")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ok(serialize_session(item))


async def _session(conversation_id: str, user: User, db: AsyncSession) -> ConversationSession:
    item = await db.get(ConversationSession, conversation_id)
    if not item or item.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


@router.put("/users/conversations/{conversation_id}/switch")
async def switch_session(conversation_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await _session(conversation_id, user, db)
    item.status = "ACTIVE"
    item.updated_at = datetime.utcnow()
    await db.commit()
    return ok(serialize_session(item))


@router.put("/users/conversations/{conversation_id}/archive")
async def archive_session(conversation_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await _session(conversation_id, user, db)
    item.status = "ARCHIVED"
    await db.commit()
    return ok(serialize_session(item))


@router.put("/users/conversations/{conversation_id}/unarchive")
async def unarchive_session(conversation_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await _session(conversation_id, user, db)
    item.status = "ACTIVE"
    await db.commit()
    return ok(serialize_session(item))


@router.get("/users/conversation")
async def messages(
    conversationId: str = Query(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _session(conversationId, user, db)
    rows = list(
        (
            await db.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversationId, ConversationMessage.user_id == str(user.id))
                .order_by(ConversationMessage.id)
            )
        ).all()
    )
    data = []
    for row in rows:
        refs = json.loads(row.reference_mappings_json) if row.reference_mappings_json else None
        data.append(
            {
                "role": row.role,
                "content": row.content,
                "timestamp": row.created_at.isoformat(),
                "conversationId": row.conversation_id,
                "generationId": row.generation_id,
                "referenceMappings": refs,
                "status": "finished" if row.role == "assistant" else None,
            }
        )
    return ok(data)
