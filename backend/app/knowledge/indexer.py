from __future__ import annotations

import json
import uuid
from collections import defaultdict

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import DocumentParentChunk, DocumentVector, FileUpload, User, UserTokenRecord
from app.knowledge.embedding import embedding_service
from app.accounting.embedding_usage import capture_embedding_usage
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.metadata import es_metadata
from app.knowledge.parser import parser_service
from app.documents.storage import storage_service


async def process_file(db: AsyncSession, file_id: int) -> None:
    """Build a new vector version without destroying the active version.

    New DB rows and Elasticsearch documents carry the same immutable version id. If any
    embedding/bulk/verification step fails, the DB transaction rolls back and the old
    FileUpload.active_vector_version remains authoritative. After the DB pointer switches,
    stale versions are best-effort garbage collected; retrieval always filters by the DB
    active version, so delayed cleanup cannot leak stale content into answers.
    """
    settings = get_settings()
    file = await db.get(FileUpload, file_id)
    if not file or not file.storage_key:
        return
    new_version = uuid.uuid4().hex
    previous_version = file.active_vector_version or "legacy"
    try:
        file.process_status = "PROCESSING"
        file.process_error = None
        await db.commit()

        raw = await storage_service.get_bytes(file.storage_key)
        blocks = parser_service.parse(file.file_name, raw)
        parents, chunks = parser_service.hierarchical_chunk(blocks)

        child_ranges: dict[int, list[int]] = defaultdict(list)
        for child_id, chunk in enumerate(chunks):
            child_ranges[chunk.parent_chunk_id].append(child_id)

        parent_rows: list[DocumentParentChunk] = []
        for parent in parents:
            child_ids = child_ranges.get(parent.parent_chunk_id)
            if not child_ids:
                continue
            parent_rows.append(
                DocumentParentChunk(
                    file_md5=file.file_md5,
                    parent_chunk_id=parent.parent_chunk_id,
                    vector_version=new_version,
                    text_content=parent.text,
                    page_number=parent.page_number,
                    start_chunk_id=child_ids[0],
                    end_chunk_id=child_ids[-1],
                    user_id=file.user_id,
                    org_tag=file.org_tag,
                    is_public=file.is_public,
                )
            )
        db.add_all(parent_rows)

        with capture_embedding_usage() as embedding_usage_meter:
            estimated_tokens = 0
            embedding_batch_size = max(1, settings.embedding_batch_size)
            es_bulk_size = max(1, settings.elasticsearch_bulk_size)
            es_buffer: list[dict] = []

            for start in range(0, len(chunks), embedding_batch_size):
                batch = chunks[start : start + embedding_batch_size]
                vectors = await embedding_service.embed([item.text for item in batch])
                db_rows: list[DocumentVector] = []

                for idx, (chunk, vector) in enumerate(zip(batch, vectors), start=start):
                    estimated_tokens += max(1, len(chunk.text) // 2)
                    db_rows.append(
                        DocumentVector(
                            file_md5=file.file_md5,
                            chunk_id=idx,
                            vector_version=new_version,
                            text_content=chunk.text,
                            page_number=chunk.page_number,
                            anchor_text=chunk.text[:80],
                            model_version=settings.embedding_model if settings.embedding_api_key else "local-hash-v1",
                            user_id=file.user_id,
                            org_tag=file.org_tag,
                            is_public=file.is_public,
                            vector_json=json.dumps(vector, ensure_ascii=False),
                        )
                    )
                    es_buffer.append(
                        {
                            "fileMd5": file.file_md5,
                            "fileName": file.file_name,
                            "chunkId": idx,
                            "parentChunkId": chunk.parent_chunk_id,
                            "indexVersion": new_version,
                            "textContent": chunk.text,
                            "pageNumber": chunk.page_number,
                            "anchorText": chunk.text[:80],
                            "userId": file.user_id,
                            "orgTag": file.org_tag,
                            "isPublic": file.is_public,
                            **es_metadata(file),
                            "vector": vector,
                        }
                    )

                db.add_all(db_rows)
                while len(es_buffer) >= es_bulk_size:
                    await elasticsearch_service.bulk_index(es_buffer[:es_bulk_size])
                    del es_buffer[:es_bulk_size]

            if es_buffer:
                await elasticsearch_service.bulk_index(es_buffer)
        total_tokens = embedding_usage_meter.total_tokens or estimated_tokens

        await elasticsearch_service.verify_version(file.file_md5, file.user_id, new_version, len(chunks))

        # Atomic pointer switch in the durable DB transaction. Old rows stay intact until
        # after this commit, so rollback can always return to the previous complete version.
        file.active_vector_version = new_version
        file.actual_chunk_count = len(chunks)
        file.actual_embedding_tokens = total_tokens
        file.process_status = "COMPLETED"
        await db.commit()

        # Charge actual embedding usage after the version becomes active. Accounting is
        # durable and never makes a successfully indexed document unreadable if billing
        # bookkeeping itself fails.
        try:
            user = await db.get(User, int(file.user_id))
            if user:
                before = int(user.embedding_token_balance or 0)
                charged = min(before, total_tokens)
                user.embedding_token_balance = before - charged
                db.add(
                    UserTokenRecord(
                        user_id=str(user.id), token_type="EMBEDDING", change_type="CONSUME",
                        request_count=1, amount=-charged, balance_before=before,
                        balance_after=before - charged, reason="document_index", remark=file.file_md5,
                    )
                )
                await db.commit()
        except Exception:
            await db.rollback()

        # Garbage collection is deliberately after the pointer switch. Retrieval filters by
        # active_vector_version, so cleanup may safely retry later without correctness loss.
        try:
            await db.execute(
                delete(DocumentVector).where(
                    DocumentVector.file_md5 == file.file_md5,
                    DocumentVector.user_id == file.user_id,
                    DocumentVector.vector_version != new_version,
                )
            )
            await db.execute(
                delete(DocumentParentChunk).where(
                    DocumentParentChunk.file_md5 == file.file_md5,
                    DocumentParentChunk.user_id == file.user_id,
                    DocumentParentChunk.vector_version != new_version,
                )
            )
            await db.commit()
            await elasticsearch_service.delete_other_versions(file.file_md5, file.user_id, new_version)
        except Exception:
            await db.rollback()
    except Exception as exc:
        await db.rollback()
        # Remove only the unactivated new ES version; the previous searchable copy remains.
        try:
            await elasticsearch_service.delete_version(file.file_md5, file.user_id, new_version)
        except Exception:
            pass
        file = await db.get(FileUpload, file_id)
        if file:
            file.active_vector_version = previous_version if file.active_vector_version is None else file.active_vector_version
            file.process_status = "FAILED"
            file.process_error = str(exc)[:2000]
            await db.commit()
        raise
