"""Logical deletion first; exact-build physical cleanup is retryable."""

from datetime import timedelta
from sqlalchemy import delete, or_, select, update
from app.core.config import get_settings
from app.db.models import (
    ChunkInfo,
    DocumentParentChunk,
    DocumentRevision,
    DocumentVector,
    EmbeddingAttempt,
    FileUpload,
    IndexBuild,
    ProcessingJob,
)
from app.db.session import SessionLocal
from app.documents.coordination import database_now
from app.documents.storage import storage_service
from app.knowledge.elasticsearch import elasticsearch_service


async def tombstone_document(db, file_id):
    now = await database_now(db)
    await db.execute(
        update(FileUpload)
        .where(FileUpload.id == file_id)
        .values(
            deleted_at=now,
            write_epoch=FileUpload.write_epoch + 1,
            input_revision=FileUpload.input_revision + 1,
            active_vector_version=None,
            process_status="DELETING",
            lease_owner=None,
            lease_until=None,
        )
    )
    await db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.file_id == file_id, ProcessingJob.status.in_(["PENDING", "RUNNING", "FAILED"]))
        .values(status="CANCELLED", lease_owner=None, lease_until=None)
    )
    await db.commit()


async def collect_garbage(*, sessions=None, retention_seconds=None, document_id=None):
    sessions = sessions or SessionLocal
    retention = get_settings().index_gc_retention_seconds if retention_seconds is None else retention_seconds
    async with sessions() as db:
        now = await database_now(db)
        # Expired abandoned builds are terminal before they become collectable.
        expired_files = select(FileUpload.id).where(
            or_(FileUpload.lease_until.is_(None), FileUpload.lease_until <= now),
            FileUpload.id == document_id if document_id is not None else True,
        )
        await db.execute(
            update(IndexBuild)
            .where(
                IndexBuild.status == "BUILDING",
                IndexBuild.file_id.in_(expired_files),
                IndexBuild.updated_at < now - timedelta(seconds=max(3, get_settings().index_lease_seconds)),
            )
            .values(status="ABANDONED")
        )
        builds = list(
            (
                await db.scalars(
                    select(IndexBuild)
                    .where(
                        IndexBuild.status.in_(["FAILED", "ABANDONED", "SUPERSEDED", "DELETING", "COLLECTED"]),
                        IndexBuild.updated_at <= now - timedelta(seconds=max(0, retention)),
                        IndexBuild.file_id == document_id if document_id is not None else True,
                    )
                    .order_by(IndexBuild.updated_at)
                    .limit(100)
                )
            ).all()
        )
        deleted = list(
            (
                await db.scalars(
                    select(FileUpload).where(
                        FileUpload.deleted_at.is_not(None),
                        FileUpload.id == document_id if document_id is not None else True,
                    )
                )
            ).all()
        )
        await db.commit()
    count = 0
    for build in builds:
        async with sessions() as db:
            file = await db.scalar(select(FileUpload).where(FileUpload.id == build.file_id).with_for_update())
            if not file or file.active_vector_version == build.build_id:
                continue
            if build.status not in {"FAILED", "ABANDONED", "SUPERSEDED", "DELETING", "COLLECTED"}:
                continue
            await db.execute(
                update(IndexBuild).where(IndexBuild.build_id == build.build_id).values(status="DELETING")
            )
            await db.commit()
        # Build IDs are never reactivated. A concurrent new publish has a different ID.
        await elasticsearch_service.delete_version(file.file_md5, file.user_id, build.build_id)
        async with sessions() as db:
            for model in (DocumentVector, DocumentParentChunk):
                await db.execute(
                    delete(model).where(
                        model.file_md5 == file.file_md5,
                        model.user_id == file.user_id,
                        model.vector_version == build.build_id,
                    )
                )
            await db.execute(
                update(IndexBuild).where(IndexBuild.build_id == build.build_id).values(status="COLLECTED")
            )
            await db.commit()
        count += 1
    for file in deleted:
        # Tombstone persists permanently; late writes are hidden and periodic
        # deletion sweeps remove them again. No logical identity is reused.
        await elasticsearch_service.delete_file(file.file_md5, file.user_id)
        if file.storage_key:
            await storage_service.delete(file.storage_key)
        if file.active_source_key and file.active_source_key != file.storage_key:
            await storage_service.delete(file.active_source_key)
        async with sessions() as db:
            revisions = list(
                (await db.scalars(select(DocumentRevision).where(DocumentRevision.file_id == file.id))).all()
            )
            profiles = (
                await db.execute(
                    select(IndexBuild.revision_id, IndexBuild.profile_id)
                    .where(IndexBuild.file_id == file.id)
                    .distinct()
                )
            ).all()
            await db.commit()
        for revision in revisions:
            await storage_service.delete(revision.storage_key)
        for revision_id, profile_id in profiles:
            for name in ("document.json", "document.md"):
                await storage_service.delete(f"parsed/{file.id}/{revision_id}/{profile_id}/{name}")
        async with sessions() as db:
            for model in (DocumentVector, DocumentParentChunk, ChunkInfo):
                await db.execute(
                    delete(model).where(model.file_md5 == file.file_md5, model.user_id == file.user_id)
                )
            await db.execute(
                update(IndexBuild).where(IndexBuild.file_id == file.id).values(status="COLLECTED")
            )
            await db.execute(
                update(FileUpload)
                .where(FileUpload.id == file.id, FileUpload.deleted_at.is_not(None))
                .values(process_status="DELETED")
            )
            await db.commit()
    return count


async def reconcile_usage(*, sessions=None):
    from app.knowledge.build_pipeline import settle_attempt

    sessions = sessions or SessionLocal
    async with sessions() as db:
        rows = (
            await db.execute(
                select(EmbeddingAttempt.attempt_id, FileUpload.user_id)
                .join(IndexBuild, IndexBuild.build_id == EmbeddingAttempt.build_id)
                .join(FileUpload, FileUpload.id == IndexBuild.file_id)
                .where(EmbeddingAttempt.provider_tokens.is_not(None), EmbeddingAttempt.settled_at.is_(None))
                .limit(100)
            )
        ).all()
    for attempt_id, user_id in rows:
        await settle_attempt(sessions, attempt_id, user_id)
    return len(rows)
