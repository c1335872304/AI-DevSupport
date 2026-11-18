from __future__ import annotations

import mimetypes
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Header
from pydantic import BaseModel
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user, user_orgs
from app.core.response import ok
from app.db.models import DocumentParentChunk, DocumentVector, FileUpload, User, ProcessingJob
from app.db.session import get_db
from app.documents.storage import storage_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.metadata import apply_metadata_to_file, file_metadata, stage_metadata
from app.documents.jobs import create_processing_job, dispatch_processing_job

router = APIRouter(prefix="/documents", tags=["documents"])


class KnowledgeMetadataRequest(BaseModel):
    category: str | None = None
    product: str | None = None
    region: str | None = None
    channel: str | None = None
    effectiveDate: str | None = None
    effectiveUntil: str | None = None
    supersededBy: str | None = None
    version: str | None = None
    errorCode: str | None = None
    plan: str | None = None
    reindex: bool = True


def _can_access(user: User, file: FileUpload) -> bool:
    return file.deleted_at is None and (file.user_id == str(user.id) or file.is_public or bool(file.org_tag and file.org_tag in user_orgs(user)) or user.role == "ADMIN")


def _public_index_error(message):
    if not message:
        return None
    if "No such file" in message or "checksum" in message:
        return "源文件无法读取或校验失败，请检查文件存储后重试"
    if "OCR_REQUIRED" in message:
        return "当前暂不支持扫描件，请上传可提取文字的 PDF"
    if "PARSE_" in message:
        return "文档解析失败，请检查文件格式、大小及解析服务"
    return "知识库构建失败，请稍后重试或联系管理员查看处理记录"


def _serialize(file: FileUpload) -> dict:
    return {
        "id": file.id,
        "fileMd5": file.file_md5,
        "fileName": file.active_file_name or file.file_name,
        "contentMd5": file.source_md5 or file.file_md5,
        "totalSize": file.total_size,
        "status": file.status,
        "userId": file.user_id,
        "orgTag": file.org_tag,
        "orgTagName": file.org_tag,
        "public": file.is_public,
        "isPublic": file.is_public,
        "estimatedEmbeddingTokens": file.estimated_embedding_tokens,
        "estimatedChunkCount": file.estimated_chunk_count,
        "actualEmbeddingTokens": file.actual_embedding_tokens,
        "actualChunkCount": file.actual_chunk_count,
        "vectorizationStatus": file.process_status,
        "activeVectorVersion": file.active_vector_version,
        "activeIndexAvailable": bool(file.active_vector_version) and file.deleted_at is None,
        "writeEpoch": file.write_epoch,
        "inputRevision": file.input_revision,
        "vectorizationErrorMessage": _public_index_error(file.process_error),
        "createdAt": file.created_at.isoformat(),
        "mergedAt": file.merged_at.isoformat() if file.merged_at else None,
        "knowledgeMetadata": file_metadata(file),
    }


@router.get("/accessible")
async def accessible(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=200),
    keyword: str | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [FileUpload.deleted_at.is_(None)]
    if user.role != "ADMIN":
        access_clauses = [FileUpload.user_id == str(user.id), FileUpload.is_public.is_(True)]
        orgs = sorted(user_orgs(user))
        if orgs:
            access_clauses.append(FileUpload.org_tag.in_(orgs))
        filters.append(or_(*access_clauses))
    if keyword:
        filters.append(FileUpload.file_name.ilike(f"%{keyword.strip()}%"))

    count_stmt = select(func.count()).select_from(FileUpload)
    rows_stmt = select(FileUpload).order_by(FileUpload.created_at.desc()).offset((page - 1) * size).limit(size)
    if filters:
        count_stmt = count_stmt.where(*filters)
        rows_stmt = rows_stmt.where(*filters)
    total = int((await db.scalar(count_stmt)) or 0)
    rows = list((await db.scalars(rows_stmt)).all())
    payload = [_serialize(f) for f in rows]
    return ok({"content": payload, "data": payload, "number": page, "size": size, "totalElements": total})


@router.get("/uploads")
async def uploads(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = list((await db.scalars(select(FileUpload).where(FileUpload.user_id == str(user.id), FileUpload.deleted_at.is_(None)).order_by(FileUpload.created_at.desc()))).all())
    return ok([_serialize(f) for f in rows])


async def _owned_file(file_md5: str, user: User, db: AsyncSession) -> FileUpload:
    stmt = select(FileUpload).where(FileUpload.file_md5 == file_md5, FileUpload.deleted_at.is_(None))
    if user.role != "ADMIN":
        stmt = stmt.where(FileUpload.user_id == str(user.id))
    file = await db.scalar(stmt.order_by(FileUpload.id.desc()).with_for_update())
    if not file:
        raise HTTPException(status_code=404, detail="Document not found")
    return file


@router.put("/{file_md5}/metadata")
async def update_metadata(
    file_md5: str,
    payload: KnowledgeMetadataRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    file = await _owned_file(file_md5, user, db)
    try:
        stage_metadata(file, {
            "category": payload.category, "product": payload.product, "region": payload.region,
            "channel": payload.channel, "effective_date": payload.effectiveDate, "version": payload.version,
            "error_code": payload.errorCode, "plan": payload.plan,
            "effective_until": payload.effectiveUntil, "superseded_by": payload.supersededBy,
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid knowledge metadata: {exc}") from exc
    file.input_revision += 1
    job_id = None
    # Existing ES chunks carry denormalized metadata, so changing metadata must reindex
    # before the new filter values can affect retrieval.
    if payload.reindex and file.status == 1 and file.storage_key:
        job_id = await create_processing_job(file.id, db=db)
        background_tasks.add_task(dispatch_processing_job, job_id)
    else:
        await db.commit()
    return ok({"fileMd5": file.file_md5, "knowledgeMetadata": file_metadata(file), "processingJobId": job_id})


@router.delete("/{file_md5}")
async def delete_document(file_md5: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    file = await _owned_file(file_md5, user, db)
    from app.documents.lifecycle import tombstone_document
    await tombstone_document(db, file.id)
    return ok(message="Document deleted; physical cleanup queued")


@router.get("/processing-jobs/{job_id}")
async def processing_job(job_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    file = await db.get(FileUpload, job.file_id)
    if not file or not _can_access(user, file):
        raise HTTPException(status_code=404, detail="Processing job not found")
    return ok({
        "jobId": job.job_id, "fileId": job.file_id, "status": job.status,
        "attempts": job.attempts, "lastError": _public_index_error(job.last_error),
        "leaseUntil": job.lease_until.isoformat() if job.lease_until else None,
        "activeVectorVersion": file.active_vector_version,
        "activeIndexAvailable": bool(file.active_vector_version),
        "createdAt": job.created_at.isoformat(), "updatedAt": job.updated_at.isoformat(),
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    })


@router.post("/{file_md5}/reindex")
@router.post("/{file_md5}/vectorization/retry")
async def retry_vectorization(
    file_md5: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    file = await _owned_file(file_md5, user, db)
    required_tokens = int(file.estimated_embedding_tokens or file.actual_embedding_tokens or 1)
    if int(user.embedding_token_balance or 0) < required_tokens:
        raise HTTPException(status_code=402, detail="Insufficient embedding token balance")
    await db.commit()
    try:
        job_id = await create_processing_job(file.id, force=True, idempotency_key=idempotency_key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(dispatch_processing_job, job_id)
    return ok({"processingJobId": job_id}, "Vectorization task submitted")


async def _load_file(file_md5: str | None, file_name: str | None, user: User, db: AsyncSession) -> FileUpload:
    stmt = select(FileUpload).where(FileUpload.deleted_at.is_(None))
    if file_md5:
        stmt = stmt.where(FileUpload.file_md5 == file_md5)
    elif file_name:
        stmt = stmt.where(FileUpload.file_name == file_name)
    else:
        raise HTTPException(status_code=400, detail="fileMd5 or fileName is required")
    candidates = list((await db.scalars(stmt.order_by(FileUpload.id.desc()))).all())
    if not candidates:
        raise HTTPException(status_code=404, detail="Document not found")
    candidates.sort(key=lambda item: item.user_id != str(user.id))
    for file in candidates:
        if _can_access(user, file):
            return file
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/download")
async def download(
    fileMd5: str | None = None,
    fileName: str | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    file = await _load_file(fileMd5, fileName, user, db)
    if not file.storage_key:
        raise HTTPException(status_code=404, detail="Stored object not found")
    content_type = mimetypes.guess_type(file.active_file_name or file.file_name)[0] or "application/octet-stream"
    return StreamingResponse(storage_service.iter_bytes(file.active_source_key or file.storage_key), media_type=content_type, headers={"Content-Disposition": f'attachment; filename="{file.active_file_name or file.file_name}"'})


@router.get("/download-by-md5")
async def download_by_md5(fileMd5: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await download(fileMd5=fileMd5, fileName=None, user=user, db=db)


@router.get("/preview")
async def preview(fileMd5: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    file = await _load_file(fileMd5, None, user, db)
    content_type = mimetypes.guess_type(file.active_file_name or file.file_name)[0] or "application/octet-stream"
    return StreamingResponse(storage_service.iter_bytes(file.active_source_key or file.storage_key or ""), media_type=content_type)


@router.get("/page-preview")
async def page_preview(fileMd5: str, page: int = 1, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    # The Vue PDF viewer can render the original PDF and navigate to page itself.
    return await preview(fileMd5, user, db)


@router.get("/reference-detail")
async def reference_detail(
    fileMd5: str,
    chunkId: int,
    referenceNumber: int = 1,
    indexVersion: str | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    file = await _load_file(fileMd5, None, user, db)
    if indexVersion and indexVersion != (file.active_vector_version or "legacy"):
        raise HTTPException(status_code=410, detail="Reference version is no longer active")
    vector = await db.scalar(select(DocumentVector).where(DocumentVector.file_md5 == fileMd5, DocumentVector.user_id == file.user_id, DocumentVector.chunk_id == chunkId, DocumentVector.vector_version == (file.active_vector_version or "legacy")))
    if not vector:
        raise HTTPException(status_code=404, detail="Reference not found")
    return ok(
        {
            "referenceNumber": referenceNumber,
            "fileMd5": fileMd5,
            "fileName": file.active_file_name or file.file_name,
            "pageNumber": vector.page_number,
            "anchorText": vector.anchor_text,
            "matchedChunkText": vector.text_content,
            "evidenceSnippet": vector.text_content[:500],
            "score": None,
            "chunkId": chunkId,
            "retrievalMode": "HYBRID",
            "retrievalLabel": "混合检索",
            "knowledgeMetadata": file_metadata(file),
            "indexVersion": file.active_vector_version or "legacy",
            "sourceLocation": __import__("json").loads(vector.location_json) if vector.location_json else None,
        }
    )


@router.get("/citation")
async def read_citation(citationId: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from app.knowledge.citations import decode_citation
    try:
        data = decode_citation(citationId)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid citation") from exc
    file = await db.scalar(select(FileUpload).where(FileUpload.file_md5 == data["md5"],
        FileUpload.user_id == data["owner"], FileUpload.deleted_at.is_(None)))
    if not file or not _can_access(user, file):
        raise HTTPException(status_code=404, detail="Citation not accessible")
    if (file.active_vector_version or "legacy") != data["build"]:
        raise HTTPException(status_code=410, detail="Citation version is no longer active")
    vector = await db.scalar(select(DocumentVector).where(DocumentVector.file_md5 == file.file_md5,
        DocumentVector.user_id == file.user_id, DocumentVector.vector_version == data["build"],
        DocumentVector.chunk_id == data["chunk"]))
    if not vector:
        raise HTTPException(status_code=410, detail="Citation content unavailable")
    from app.db.models import DocumentParentChunk
    parent = await db.scalar(select(DocumentParentChunk).where(
        DocumentParentChunk.file_md5 == file.file_md5,
        DocumentParentChunk.user_id == file.user_id,
        DocumentParentChunk.vector_version == data['build'],
        DocumentParentChunk.start_chunk_id <= vector.chunk_id,
        DocumentParentChunk.end_chunk_id >= vector.chunk_id,
    ).order_by(DocumentParentChunk.parent_chunk_id).limit(1))
    from app.core.config import get_settings
    from app.knowledge.source_context import load_parent_contexts
    if parent:
        _, contexts = await load_parent_contexts(db, file.user_id, file.file_md5, data['build'])
        context = contexts[parent.parent_chunk_id]
    else:
        context = vector.text_content
    context = context[:max(500,get_settings().rag_parent_context_max_chars)]
    if data.get('scope') == 'document':
        parents = list((await db.scalars(select(DocumentParentChunk).where(
            DocumentParentChunk.file_md5 == file.file_md5,DocumentParentChunk.user_id == file.user_id,
            DocumentParentChunk.vector_version == data['build']).order_by(DocumentParentChunk.parent_chunk_id))).all())
        if parents:
            context='\n\n'.join(item.text_content for item in parents)[:data['maxChars']]
        else:
            children=list((await db.scalars(select(DocumentVector).where(DocumentVector.file_md5==file.file_md5,
                DocumentVector.user_id==file.user_id,DocumentVector.vector_version==data['build']).order_by(DocumentVector.chunk_id))).all())
            context='\n\n'.join(item.text_content for item in children)[:data['maxChars']]
    import json
    return ok({"fileName": file.active_file_name or file.file_name, "fileMd5": file.file_md5, "indexVersion": data["build"],
        "chunkId": vector.chunk_id, "textContent": vector.text_content, "pageNumber": vector.page_number,
        "contextText": context, "contextType": data.get('scope','parent' if parent else 'chunk'),
        "sourceLocation": json.loads(vector.location_json) if vector.location_json else None})


from app.documents.revisions import router as source_revision_router
router.include_router(source_revision_router)
