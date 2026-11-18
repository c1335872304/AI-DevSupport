from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import User
from app.db.session import get_db
from app.knowledge.rag import rag_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/evidence")
async def evidence_search(query: str = Query(..., min_length=1), topK: int = Query(6, ge=1, le=50),
                          user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return ok(await rag_service.search_evidence(db, user, query, topK))


@router.get("/hybrid")
async def hybrid_search(
    query: str = Query(..., min_length=1),
    topK: int = Query(6, ge=1, le=50),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(await rag_service.search(db, user, query, topK))
