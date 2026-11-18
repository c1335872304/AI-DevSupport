"""Canonical source revision API behind a stable FileUpload.id/opaque handle."""

import hashlib
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.deps import current_user
from app.core.response import ok
from app.db.models import FileUpload, User
from app.db.session import get_db
from app.documents.jobs import create_processing_job, dispatch_processing_job
from app.documents.storage import storage_service
from app.documents.upload import upload_service
from app.knowledge.metadata import apply_metadata_to_file, stage_metadata
from app.documents.revision_snapshot import remember_revision, source_revision
from app.db.models import DocumentRevision

router = APIRouter()


async def read_source(upload):
    name = upload_service._safe_file_name(upload.filename or "document.md")
    if Path(name).suffix.lower() not in {".md", ".txt", ".html", ".pdf", ".docx"}:
        raise HTTPException(400, "Unsupported revision document format")
    raw = await upload.read(get_settings().document_parse_max_bytes + 1)
    if not raw or len(raw) > get_settings().document_parse_max_bytes:
        raise HTTPException(413, "Empty or oversized document")
    return name, raw


def parse_metadata(value):
    try:
        data = json.loads(value)
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data
    except Exception as exc:
        raise HTTPException(400, "Invalid metadata JSON") from exc


@router.post("/content")
async def create_content_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    name, raw = await read_source(file)
    values = parse_metadata(metadata)
    if int(user.embedding_token_balance or 0) < max(1, len(raw) // 4):
        raise HTTPException(402, "Insufficient embedding token balance")
    handle = uuid.uuid4().hex
    key = f"source-documents/{user.id}/{handle}/{uuid.uuid4().hex}/{name}"
    await db.commit()
    document = FileUpload(
        file_md5=handle,
        source_md5=hashlib.md5(raw).hexdigest(),
        file_name=name,
        storage_key=key,
        status=1,
        process_status="PENDING",
        user_id=str(user.id),
        is_public=False,
        org_tag=None,
        total_size=len(raw),
    )
    try:
        apply_metadata_to_file(document, values)
    except ValueError as exc:
        raise HTTPException(400, "Invalid knowledge metadata") from exc
    await storage_service.put_bytes(key, raw)
    db.add(document)
    await db.flush()
    await remember_revision(db, document, raw, key)
    job = await create_processing_job(document.id, db=db)
    background_tasks.add_task(dispatch_processing_job, job)
    return ok(
        {
            "documentId": document.id,
            "fileMd5": handle,
            "contentMd5": document.source_md5,
            "inputRevision": document.input_revision,
            "processingJobId": job,
        },
        "Document created",
    )


@router.post("/by-id/{document_id}/content-revisions")
async def replace_content_revision(
    document_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    expectedRevision: int = Form(..., ge=0),
    metadata: str = Form("{}"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(FileUpload, document_id)
    if (
        not document
        or document.deleted_at is not None
        or (user.role != "ADMIN" and document.user_id != str(user.id))
    ):
        raise HTTPException(404, "Document not found")
    name, raw = await read_source(file)
    values = parse_metadata(metadata)
    if int(user.embedding_token_balance or 0) < max(1, len(raw) // 4):
        raise HTTPException(402, "Insufficient embedding token balance")
    if expectedRevision != document.input_revision:
        raise HTTPException(409, "Document input revision changed")
    owner = document.user_id
    handle = document.file_md5
    legacy_source = None
    if document.active_vector_version and not document.active_source_key:
        # Snapshot the existing published source before changing its desired pointer.
        old_raw = await storage_service.get_bytes(document.storage_key)
        legacy_source = source_revision(
            document, old_raw, document.storage_key, apply_desired=False, revision_number=0
        )
    await db.commit()
    key = f"source-documents/{owner}/{handle}/{uuid.uuid4().hex}/{name}"
    await storage_service.put_bytes(key, raw)
    document = await db.scalar(
        select(FileUpload)
        .where(FileUpload.id == document_id, FileUpload.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not document or document.input_revision != expectedRevision:
        raise HTTPException(409, "Document input revision changed")
    if document.active_vector_version and not document.active_source_key:
        document.active_source_key = document.storage_key
        document.active_file_name = document.file_name
    if legacy_source and not await db.get(DocumentRevision, legacy_source.revision_id):
        db.add(legacy_source)
    try:
        stage_metadata(document, values)
    except ValueError as exc:
        raise HTTPException(400, "Invalid knowledge metadata") from exc
    document.storage_key = key
    document.file_name = name
    document.source_md5 = hashlib.md5(raw).hexdigest()
    document.total_size = len(raw)
    document.input_revision += 1
    await remember_revision(db, document, raw, key)
    job = await create_processing_job(document.id, db=db)
    background_tasks.add_task(dispatch_processing_job, job)
    return ok(
        {
            "documentId": document.id,
            "fileMd5": handle,
            "contentMd5": document.source_md5,
            "inputRevision": document.input_revision,
            "processingJobId": job,
        },
        "Content revision queued",
    )
