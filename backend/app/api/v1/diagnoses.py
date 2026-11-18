"""Owner-scoped views and bounded diagnostic commands; no client 'verified' flags."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import DiagnosisExecution, DiagnosisSession, DiagnosisTurn, User
from app.db.session import get_db
from app.diagnosis.service import detail

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


class RecheckRequest(BaseModel):
    requestId: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    expectedRevision: int = Field(ge=1)
    idempotencyKey: str = Field(min_length=3, max_length=100)


@router.post("/{diagnosis_id}/rechecks", status_code=202)
async def submit_recheck(
    diagnosis_id: str,
    payload: RecheckRequest,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.redaction import redact_text
    from app.diagnosis.execution import digest, recover_execution
    from app.diagnosis.service import begin_turn

    case = await db.get(DiagnosisSession, diagnosis_id)
    if not case or case.user_id != str(user.id):
        raise HTTPException(404, "Diagnosis not found")
    if redact_text(payload.requestId) != payload.requestId:
        raise HTTPException(422, "Provide a request identifier, never credentials")
    generation_id = "recheck_" + digest([diagnosis_id, payload.idempotencyKey])[:48]
    conversation_id = case.conversation_id
    await db.commit()
    try:
        result = await begin_turn(
            user_id=str(user.id),
            conversation_id=conversation_id,
            generation_id=generation_id,
            question=f"用户明确关联本故障复查，请求 {payload.requestId}",
            entities={"request_id": payload.requestId},
            sources={"request_id": "current"},
            diagnostic=True,
            recheck_case_id=diagnosis_id,
            expected_revision=payload.expectedRevision,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not result:
        raise HTTPException(409, "Diagnosis unavailable")
    background.add_task(recover_execution, generation_id)
    return ok({"diagnosisId": result, "generationId": generation_id, "status": "SUBMITTED"})


class ResumeRequest(BaseModel):
    generationId: str = Field(min_length=3, max_length=64)


@router.post("/{diagnosis_id}/resume", status_code=202)
async def resume_diagnosis(
    diagnosis_id: str,
    payload: ResumeRequest,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.diagnosis.execution import recover_execution

    case = await db.get(DiagnosisSession, diagnosis_id)
    execution = await db.get(DiagnosisExecution, payload.generationId)
    if not case or case.user_id != str(user.id) or not execution or execution.diagnosis_id != diagnosis_id:
        raise HTTPException(404, "Diagnosis not found")
    if execution.status not in {"COMPLETED", "CANCELLED"}:
        background.add_task(recover_execution, payload.generationId)
    return ok({"diagnosisId": diagnosis_id, "generationId": payload.generationId, "status": execution.status})


@router.get("")
async def list_diagnoses(
    conversationId: str | None = Query(None, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(DiagnosisSession).where(DiagnosisSession.user_id == str(user.id))
    if conversationId:
        query = query.where(DiagnosisSession.conversation_id == conversationId)
    rows = (await db.scalars(query.order_by(DiagnosisSession.updated_at.desc()).limit(limit))).all()
    return ok(
        [
            {
                "diagnosisId": row.diagnosis_id,
                "conversationId": row.conversation_id,
                "status": row.status,
                "nextAction": row.next_action,
                "updatedAt": row.updated_at.isoformat() + "Z",
            }
            for row in rows
        ]
    )


@router.get("/by-generation/{generation_id}")
async def diagnosis_by_generation(
    generation_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    turn = await db.get(DiagnosisTurn, generation_id)
    result = await detail(db, user, turn.diagnosis_id) if turn else None
    if not result:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return ok(result)


@router.get("/{diagnosis_id}")
async def diagnosis_detail(
    diagnosis_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    result = await detail(db, user, diagnosis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return ok(result)
