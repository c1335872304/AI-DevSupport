from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import ChatFeedback, DiagnosisSession, DiagnosisTurn, GenerationState, User
from app.db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


class FeedbackRequest(BaseModel):
    generationId: str
    rating: str


def serialize_generation(row: GenerationState) -> dict:
    return {
        "generationId": row.generation_id,
        "userId": row.user_id,
        "conversationId": row.conversation_id,
        "question": row.question,
        "status": row.status,
        "content": row.content,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "errorMessage": row.error,
        "referenceMappings": json.loads(row.reference_mappings_json) if row.reference_mappings_json else {},
    }


async def generation_payload(db, row):
    if not row:
        return None
    payload = serialize_generation(row)
    payload["diagnosisId"] = await db.scalar(select(DiagnosisTurn.diagnosis_id)
        .join(DiagnosisSession, DiagnosisSession.diagnosis_id == DiagnosisTurn.diagnosis_id)
        .where(DiagnosisTurn.generation_id == row.generation_id, DiagnosisSession.user_id == row.user_id))
    return payload


@router.get("/websocket-token")
async def websocket_token(user: User = Depends(current_user)):
    # Kept for frontend stop-command compatibility. Current Python server binds stop to the authenticated socket.
    return ok({"cmdToken": secrets.token_urlsafe(24)})


@router.get("/generation/{generation_id}")
async def generation(generation_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(GenerationState, generation_id)
    if not row or row.user_id != str(user.id):
        return ok(None)
    return ok(await generation_payload(db, row))


@router.get("/active-generation")
async def active_generation(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(GenerationState)
        .where(GenerationState.user_id == str(user.id), GenerationState.status.in_(["PENDING", "STREAMING"]))
        .order_by(GenerationState.updated_at.desc())
    )
    return ok(await generation_payload(db, row))


@router.post("/feedback")
async def feedback(payload: FeedbackRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    generation = await db.get(GenerationState, payload.generationId)
    if not generation or generation.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Generation not found")
    rating = payload.rating.strip()[:32]
    if not rating:
        raise HTTPException(status_code=422, detail="rating is required")
    db.add(ChatFeedback(generation_id=payload.generationId, user_id=str(user.id), rating=rating))
    await db.commit()
    return ok(message="Feedback saved")
