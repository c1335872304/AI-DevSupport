"""Fenced, recoverable RAG builds. No provider I/O inside a write transaction."""

import asyncio
import hashlib
import json
import uuid
import time
import logging
from collections import defaultdict
from contextlib import suppress
from sqlalchemy import func, select, update
from app.accounting.embedding_usage import capture_embedding_usage
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import (
    DocumentParentChunk,
    DocumentRevision,
    DocumentVector,
    EmbeddingAttempt,
    FileUpload,
    IndexBuild,
    User,
    UserTokenRecord,
)
from app.documents.coordination import (
    LeaseLost,
    claim_document,
    lease_predicate,
    release_document,
    renew_document,
    session_factory,
)
from app.documents.storage import storage_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.embedding import embedding_service
from app.knowledge.metadata import es_metadata, apply_metadata_to_file, SCALAR_FIELDS
from app.knowledge.parser import parser_service
from app.documents.revision_snapshot import source_revision

logger = logging.getLogger(__name__)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


async def settle_attempt(sessions, attempt_id, user_id):
    async with sessions() as db:
        attempt = await db.scalar(
            select(EmbeddingAttempt).where(EmbeddingAttempt.attempt_id == attempt_id).with_for_update()
        )
        if not attempt or attempt.provider_tokens is None or attempt.settled_at:
            return
        user = await db.scalar(select(User).where(User.id == int(user_id)).with_for_update())
        if not user:
            return
        before = int(user.embedding_token_balance or 0)
        charged = min(before, attempt.provider_tokens)
        result = await db.execute(
            update(EmbeddingAttempt)
            .where(EmbeddingAttempt.attempt_id == attempt_id, EmbeddingAttempt.settled_at.is_(None))
            .values(settled_at=utcnow(), settled_tokens=charged)
        )
        if result.rowcount != 1:
            await db.rollback()
            return
        user.embedding_token_balance = before - charged
        db.add(
            UserTokenRecord(
                user_id=str(user_id),
                token_type="EMBEDDING",
                change_type="CONSUME",
                request_count=1,
                amount=-charged,
                balance_before=before,
                balance_after=before - charged,
                reason="document_index",
                remark=attempt_id,
            )
        )
        await db.commit()


async def process_file(db, file_id, *, expected_revision=None):
    await db.commit()
    sessions = session_factory(db)
    lease = await claim_document(sessions, file_id)
    if lease is None:
        return
    if expected_revision is not None and lease.input_revision != expected_revision:
        await release_document(sessions, lease)
        raise LeaseLost("Index request refers to an obsolete input revision")
    build_id = uuid.uuid4().hex
    lost = asyncio.Event()

    async def heartbeat():
        while True:
            await asyncio.sleep(max(1, get_settings().index_lease_seconds / 3))
            try:
                await renew_document(sessions, lease)
            except Exception:
                lost.set()
                return

    pulse = asyncio.create_task(heartbeat(), name=f"index-lease:{build_id}")
    try:
        await _build(sessions, lease, build_id, lost)
    except BaseException as exc:
        # Publication may have committed despite a lost response. Leave exact
        # terminal builds to GC; never delete possibly active ES data here.
        async with sessions() as state:
            file = await state.get(FileUpload, file_id)
            history = await state.get(IndexBuild, build_id)
            published = (file is not None and file.active_vector_version == build_id) or (
                history is not None
                and (
                    history.status in {"PUBLISHED", "SUPERSEDED"}
                    or json.loads(history.manifest_json).get("phase") == "PUBLISHED"
                )
            )
            if not published:
                await state.execute(
                    update(IndexBuild)
                    .where(IndexBuild.build_id == build_id, IndexBuild.status == "BUILDING")
                    .values(status="FAILED", error=str(exc)[:2000])
                )
                await state.execute(
                    update(FileUpload)
                    .where(*lease_predicate(lease))
                    .values(process_status="FAILED", process_error=str(exc)[:2000])
                )
                await state.commit()
        if not published:
            raise
    finally:
        pulse.cancel()
        with suppress(asyncio.CancelledError):
            await pulse
        await release_document(sessions, lease)
        # Keep caller ORM objects usable; refresh explicitly rather than expire
        # everything (callers often read scalar ids after this returns).
        await db.rollback()
        file = await db.get(FileUpload, file_id)
        if file:
            await db.refresh(file)


async def _build(sessions, lease, build_id, lost):
    started = time.monotonic()
    timings = {"embeddingMs": 0.0, "elasticsearchMs": 0.0}
    settings = get_settings()
    async with sessions() as db:
        file = await db.get(FileUpload, lease.file_id)
        if not file or file.deleted_at is not None or file.input_revision != lease.input_revision:
            raise LeaseLost("Source revision changed before build snapshot")
        await db.commit()
    if file.desired_metadata_json:
        apply_metadata_to_file(file, json.loads(file.desired_metadata_json))
    profile = {
        "parser": parser_service.profile(),
        "model": settings.embedding_model,
        "dimension": settings.embedding_dimension,
    }
    profile_id = digest(profile)
    async with sessions() as db:
        db.add(
            IndexBuild(
                build_id=build_id,
                file_id=file.id,
                owner=lease.owner,
                epoch=lease.epoch,
                input_revision=lease.input_revision,
                revision_id="PENDING",
                profile_id=profile_id,
                manifest_json=json.dumps({"profile": profile, "phase": "READING_SOURCE"}),
            )
        )
        await db.commit()
    raw = await storage_service.get_bytes(file.storage_key)
    if hashlib.md5(raw).hexdigest() != (file.source_md5 or file.file_md5):
        raise ValueError("Stored source checksum differs from document identity")
    timings["sourceMs"] = (time.monotonic() - started) * 1000
    snapshot = source_revision(file, raw, "")
    revision_id = snapshot.revision_id
    async with sessions() as db:
        existing_revision = await db.get(DocumentRevision, revision_id)
        revision_key = (
            existing_revision.storage_key
            if existing_revision
            else f"revisions/{file.id}/{revision_id}/source"
        )
    if not existing_revision:
        await storage_service.put_bytes(revision_key, raw)
    async with sessions() as db:
        if not await db.get(DocumentRevision, revision_id):
            snapshot.storage_key = revision_key
            db.add(snapshot)
        await db.execute(
            update(IndexBuild)
            .where(IndexBuild.build_id == build_id)
            .values(
                revision_id=revision_id, manifest_json=json.dumps({"profile": profile, "phase": "PARSING"})
            )
        )
        await db.commit()
    parsing_started = time.monotonic()
    blocks, artifacts = await asyncio.to_thread(parser_service.parse_with_artifacts, file.file_name, raw)
    if artifacts:
        await storage_service.put_bytes(
            f"parsed/{file.id}/{revision_id}/{profile_id}/document.json",
            json.dumps(artifacts, ensure_ascii=False).encode(),
            "application/json",
        )
        await storage_service.put_bytes(
            f"parsed/{file.id}/{revision_id}/{profile_id}/document.md",
            artifacts["markdown"].encode(),
            "text/markdown",
        )
    parents, chunks = parser_service.hierarchical_chunk(blocks)
    timings["parseAndChunkMs"] = (time.monotonic() - parsing_started) * 1000
    if not chunks:
        raise ValueError("Document parsing produced no indexable content")
    ranges = defaultdict(list)
    for i, chunk in enumerate(chunks):
        ranges[chunk.parent_chunk_id].append(i)
    async with sessions() as db:
        db.add_all(
            [
                DocumentParentChunk(
                    file_md5=file.file_md5,
                    user_id=file.user_id,
                    parent_chunk_id=p.parent_chunk_id,
                    vector_version=build_id,
                    text_content=p.text,
                    page_number=p.page_number,
                    location_json=json.dumps(p.location) if p.location else None,
                    start_chunk_id=ranges[p.parent_chunk_id][0],
                    end_chunk_id=ranges[p.parent_chunk_id][-1],
                    org_tag=file.org_tag,
                    is_public=file.is_public,
                )
                for p in parents
                if ranges[p.parent_chunk_id]
            ]
        )
        await db.commit()
    for start in range(0, len(chunks), max(1, settings.embedding_batch_size)):
        if lost.is_set():
            raise LeaseLost("Heartbeat lost")
        await renew_document(sessions, lease)
        batch = chunks[start : start + max(1, settings.embedding_batch_size)]
        attempt_id = uuid.uuid4().hex
        async with sessions() as db:
            db.add(
                EmbeddingAttempt(
                    attempt_id=attempt_id,
                    build_id=build_id,
                    batch_start=start,
                    input_hash=digest([c.text for c in batch]),
                )
            )
            await db.commit()
        try:
            embedding_started = time.monotonic()
            with capture_embedding_usage() as usage:
                vectors = await embedding_service.embed([c.text for c in batch])
            timings["embeddingMs"] += (time.monotonic() - embedding_started) * 1000
            if len(vectors) != len(batch) or any(len(v) != settings.embedding_dimension for v in vectors):
                raise ValueError("Embedding output does not match batch shape")
        except BaseException:
            async with sessions() as db:
                await db.execute(
                    update(EmbeddingAttempt)
                    .where(EmbeddingAttempt.attempt_id == attempt_id)
                    .values(
                        status="KNOWN" if usage.has_usage else "UNKNOWN",
                        provider_tokens=usage.total_tokens if usage.has_usage else None,
                        provider_request_ids_json=json.dumps(usage.request_ids),
                    )
                )
                await db.commit()
            await settle_attempt(sessions, attempt_id, file.user_id)
            raise
        async with sessions() as db:
            await db.execute(
                update(EmbeddingAttempt)
                .where(EmbeddingAttempt.attempt_id == attempt_id)
                .values(
                    status="KNOWN" if usage.has_usage else "UNKNOWN",
                    provider_tokens=usage.total_tokens if usage.has_usage else None,
                    provider_request_ids_json=json.dumps(usage.request_ids),
                )
            )
            await db.commit()
        await settle_attempt(sessions, attempt_id, file.user_id)
        await renew_document(sessions, lease)
        documents = []
        async with sessions() as db:
            for i, (chunk, vector) in enumerate(zip(batch, vectors), start):
                db.add(
                    DocumentVector(
                        file_md5=file.file_md5,
                        user_id=file.user_id,
                        chunk_id=i,
                        vector_version=build_id,
                        text_content=chunk.text,
                        page_number=chunk.page_number,
                        location_json=json.dumps(chunk.location) if chunk.location else None,
                        anchor_text=chunk.text[:80],
                        model_version=settings.embedding_model,
                        org_tag=file.org_tag,
                        is_public=file.is_public,
                        vector_json=json.dumps(vector),
                    )
                )
                documents.append(
                    {
                        "fileMd5": file.file_md5,
                        "fileName": file.file_name,
                        "chunkId": i,
                        "parentChunkId": chunk.parent_chunk_id,
                        "indexVersion": build_id,
                        "embeddingModel": settings.embedding_model,
                        "embeddingDimension": settings.embedding_dimension,
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
            await db.commit()
        es_started = time.monotonic()
        await elasticsearch_service.bulk_index(documents)
        timings["elasticsearchMs"] += (time.monotonic() - es_started) * 1000
        async with sessions() as db:
            await db.execute(
                update(IndexBuild)
                .where(IndexBuild.build_id == build_id)
                .values(completed_chunks=start + len(batch))
            )
            await db.commit()
    await elasticsearch_service.verify_version(file.file_md5, file.user_id, build_id, len(chunks))
    await elasticsearch_service.verify_documents(
        [
            {
                "fileMd5": file.file_md5,
                "userId": file.user_id,
                "indexVersion": build_id,
                "chunkId": i,
                "parentChunkId": chunk.parent_chunk_id,
                "textContent": chunk.text,
                "embeddingModel": settings.embedding_model,
                "embeddingDimension": settings.embedding_dimension,
            }
            for i, chunk in enumerate(chunks)
        ]
    )
    async with sessions() as db:
        rows = list(
            (
                await db.scalars(
                    select(DocumentVector)
                    .where(
                        DocumentVector.file_md5 == file.file_md5,
                        DocumentVector.user_id == file.user_id,
                        DocumentVector.vector_version == build_id,
                    )
                    .order_by(DocumentVector.chunk_id)
                )
            ).all()
        )
        if [(r.chunk_id, r.text_content) for r in rows] != [(i, c.text) for i, c in enumerate(chunks)]:
            raise RuntimeError("Build chunk identity/content verification failed")
        total = await db.scalar(
            select(func.sum(EmbeddingAttempt.provider_tokens)).where(EmbeddingAttempt.build_id == build_id)
        )
        manifest = {
            "profile": profile,
            "parentCount": len(parents),
            "childCount": len(chunks),
            "phase": "PUBLISHED",
            "timingsMs": {**timings, "totalMs": (time.monotonic() - started) * 1000},
            "chunkDigest": digest([(i, c.text, c.parent_chunk_id) for i, c in enumerate(chunks)]),
        }
        published_metadata = {column: getattr(file, column) for column in SCALAR_FIELDS.values()}
        published_metadata.update(
            knowledge_effective_date=file.knowledge_effective_date,
            knowledge_effective_until=file.knowledge_effective_until,
            desired_metadata_json=None,
            active_source_key=revision_key,
            active_file_name=file.file_name,
        )
        result = await db.execute(
            update(FileUpload)
            .where(*lease_predicate(lease))
            .values(
                **published_metadata,
                active_vector_version=build_id,
                process_status="COMPLETED",
                process_error=None,
                actual_chunk_count=len(chunks),
                actual_embedding_tokens=total,
            )
        )
        if result.rowcount != 1:
            raise LeaseLost("Publication rejected: document lease or input changed")
        await db.execute(
            update(IndexBuild)
            .where(IndexBuild.file_id == file.id, IndexBuild.status == "PUBLISHED")
            .values(status="SUPERSEDED")
        )
        await db.execute(
            update(IndexBuild)
            .where(IndexBuild.build_id == build_id)
            .values(status="PUBLISHED", manifest_json=json.dumps(manifest))
        )
        await db.commit()
    logger.info(
        "RAG build published file=%s build=%s epoch=%s chunks=%s timings=%s",
        file.id,
        build_id,
        lease.epoch,
        len(chunks),
        timings,
    )
