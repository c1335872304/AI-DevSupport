"""Auditable supplier usage reconciliation; restricted to billing administrators."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.provider_ledger import expire_inflight, reconcile_statement
from app.core.deps import admin_user
from app.core.response import ok
from app.db.models import ProviderAttempt, User
from app.db.session import get_db

router = APIRouter(prefix='/admin/provider-usage', tags=['provider-usage'])


class Statement(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    kind: Literal['LLM', 'EMBEDDING']
    model: str = Field(min_length=1, max_length=128)
    promptTokens: int = Field(ge=0, le=10**12)
    completionTokens: int = Field(ge=0, le=10**12)
    providerRequestId: str | None = Field(None, max_length=255)
    evidenceRef: str = Field(min_length=3, max_length=500)


@router.get('')
async def list_attempts(status: str | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                        admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    await expire_inflight(db)
    query = select(ProviderAttempt).order_by(ProviderAttempt.created_at.desc(), ProviderAttempt.attempt_id).offset(offset).limit(limit)
    if status:
        query = query.where(ProviderAttempt.status == status)
    rows = (await db.scalars(query)).all()
    return ok([{'attemptId': r.attempt_id, 'userId': r.user_id, 'generationId': r.generation_id,
        'kind': r.kind, 'model': r.model, 'status': r.status, 'providerRequestId': r.provider_request_id,
        'totalTokens': r.total_tokens, 'createdAt': r.created_at.isoformat(),
        'evidenceRef': r.evidence_ref, 'reconciledBy': r.reconciled_by} for r in rows])


@router.post('/{attempt_id}/reconcile')
async def reconcile(attempt_id: str, statement: Statement, admin: User = Depends(admin_user),
                     db: AsyncSession = Depends(get_db)):
    if statement.kind == 'EMBEDDING' and statement.completionTokens:
        raise HTTPException(422, 'Embedding usage cannot contain completion tokens')
    try:
        row = await reconcile_statement(db, attempt_id, statement.model_dump(), admin.id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return ok({'attemptId': row.attempt_id, 'status': row.status, 'totalTokens': row.total_tokens,
               'customerBalanceChanged': False})
