from __future__ import annotations

import math

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import ChunkInfo, FileUpload, User
from app.db.session import get_db
from app.documents.jobs import create_processing_job, dispatch_processing_job
from app.documents.upload import upload_service

router = APIRouter(prefix="/upload", tags=["upload"])
CHUNK_BYTES = 5 * 1024 * 1024


class MergeRequest(BaseModel):
    fileMd5: str
    fileName: str | None = None


@router.post("/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    fileMd5: str = Form(...),
    chunkIndex: int = Form(...),
    totalSize: int = Form(...),
    fileName: str = Form(...),
    orgTag: str | None = Form(None),
    isPublic: bool = Form(False),
    chunkMd5: str | None = Form(None),
    knowledgeCategory: str | None = Form(None),
    knowledgeProduct: str | None = Form(None),
    knowledgeRegion: str | None = Form(None),
    knowledgeChannel: str | None = Form(None),
    knowledgeEffectiveDate: str | None = Form(None),
    knowledgeVersion: str | None = Form(None),
    knowledgeErrorCode: str | None = Form(None),
    knowledgePlan: str | None = Form(None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await file.read()
        if len(payload) > CHUNK_BYTES:
            raise ValueError(f"Chunk exceeds {CHUNK_BYTES} byte limit")
        total_chunks = max(1, math.ceil(totalSize / CHUNK_BYTES))
        await upload_service.save_chunk(
            db,
            user,
            fileMd5,
            fileName,
            chunkIndex,
            total_chunks,
            totalSize,
            payload,
            chunkMd5,
            orgTag,
            isPublic,
            {
                "category": knowledgeCategory,
                "product": knowledgeProduct,
                "region": knowledgeRegion,
                "channel": knowledgeChannel,
                "effective_date": knowledgeEffectiveDate,
                "version": knowledgeVersion,
                "error_code": knowledgeErrorCode,
                "plan": knowledgePlan,
            },
        )
        rows = list((await db.scalars(select(ChunkInfo).where(ChunkInfo.file_md5 == fileMd5, ChunkInfo.user_id == str(user.id)))).all())
        uploaded = sorted({r.chunk_index for r in rows})
        return ok({"uploaded": uploaded, "progress": round(len(uploaded) / total_chunks * 100, 2), "totalChunks": total_chunks})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
async def upload_status(
    file_md5: str = Query(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    upload = await db.scalar(select(FileUpload).where(FileUpload.file_md5 == file_md5, FileUpload.user_id == str(user.id)))
    rows = list((await db.scalars(select(ChunkInfo).where(ChunkInfo.file_md5 == file_md5, ChunkInfo.user_id == str(user.id)))).all())
    uploaded = sorted({r.chunk_index for r in rows})
    total_chunks = max(1, math.ceil((upload.total_size if upload else 0) / CHUNK_BYTES)) if upload else max(1, len(uploaded))
    progress = 100.0 if upload and upload.status == 1 else round(len(uploaded) / total_chunks * 100, 2)
    return ok({"uploaded": uploaded, "progress": progress, "totalChunks": total_chunks})


@router.post("/merge")
async def merge_file(
    payload: MergeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        upload = await upload_service.merge(db, user, payload.fileMd5)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Rough estimate before parsing; actual values are written by processor.
    estimated_tokens = max(1, upload.total_size // 4)
    estimated_chunks = max(1, math.ceil(estimated_tokens / 350))
    upload.estimated_embedding_tokens = estimated_tokens
    upload.estimated_chunk_count = estimated_chunks
    if int(user.embedding_token_balance or 0) < estimated_tokens:
        upload.process_status = "PENDING"
        upload.process_error = "Insufficient embedding token balance"
        await db.commit()
        raise HTTPException(status_code=402, detail="Insufficient embedding token balance; file is merged and can be retried after recharge")
    await db.commit()
    job_id = await create_processing_job(upload.id)
    background_tasks.add_task(dispatch_processing_job, job_id)
    return ok(
        {
            "objectUrl": upload.storage_key,
            "estimatedEmbeddingTokens": estimated_tokens,
            "estimatedChunkCount": estimated_chunks,
            "processingJobId": job_id,
        },
        "File merged successfully",
    )


@router.get("/supported-types")
async def supported_types():
    return ok([".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".json", ".html"])
