"""Atomic job claims, transactional outbox and bounded restart recovery."""

import asyncio
import json
import logging
import uuid
from contextlib import suppress
from datetime import timedelta
from sqlalchemy import or_, select, update
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import FileUpload, IndexBuild, IndexOutbox, ProcessingJob
from app.db.session import SessionLocal
from app.documents.coordination import IndexBusy, LeaseLost, database_now
from app.knowledge.indexer import process_file

logger = logging.getLogger(__name__)


async def create_processing_job(file_id, *, force=False, db=None, idempotency_key=None):
    if db is not None:
        return await _create_processing_job(db, file_id, force, idempotency_key)
    async with SessionLocal() as session:
        return await _create_processing_job(session, file_id, force, idempotency_key)


async def _create_processing_job(db, file_id, force, idempotency_key=None):
    file = await db.scalar(
        select(FileUpload).where(FileUpload.id == file_id, FileUpload.deleted_at.is_(None)).with_for_update()
    )
    if not file:
        raise ValueError("Document not found or deleted")
    request_key = None
    if idempotency_key:
        from app.knowledge.build_pipeline import digest

        if len(idempotency_key) > 200:
            raise ValueError("Idempotency key is too long")
        request_key = digest({"document": file_id, "key": idempotency_key})
        existing_key = await db.scalar(select(ProcessingJob).where(ProcessingJob.request_key == request_key))
        if existing_key:
            if existing_key.input_revision != file.input_revision:
                raise ValueError("Idempotency key belongs to a different input revision")
            await db.commit()
            return existing_key.job_id
    existing = await db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.file_id == file_id,
            or_(
                ProcessingJob.status.in_(["PENDING", "RUNNING"]),
                (ProcessingJob.status == "FAILED")
                & (ProcessingJob.attempts < max(1, get_settings().index_max_attempts)),
            ),
            ProcessingJob.input_revision == file.input_revision,
        )
        .order_by(ProcessingJob.created_at.desc())
    )
    if existing and (request_key is None or existing.request_key == request_key):
        if existing.status == "FAILED":
            existing.status = "PENDING"
            file.process_status = "PENDING"
            file.process_error = None
        await db.commit()
        return existing.job_id
    job_id = uuid.uuid4().hex
    if not force and file.active_vector_version:
        from app.knowledge.build_pipeline import digest
        from app.knowledge.parser import parser_service

        settings = get_settings()
        profile_id = digest(
            {
                "parser": parser_service.profile(),
                "model": settings.embedding_model,
                "dimension": settings.embedding_dimension,
            }
        )
        active = await db.get(IndexBuild, file.active_vector_version)
        if active and active.input_revision == file.input_revision and active.profile_id == profile_id:
            db.add(
                ProcessingJob(
                    job_id=job_id,
                    file_id=file_id,
                    input_revision=file.input_revision,
                    status="COMPLETED",
                    completed_at=utcnow(),
                    request_key=request_key,
                )
            )
            await db.commit()
            return job_id
    db.add(
        ProcessingJob(
            job_id=job_id,
            file_id=file_id,
            input_revision=file.input_revision,
            status="PENDING",
            request_key=request_key,
        )
    )
    db.add(IndexOutbox(event_id=uuid.uuid4().hex, job_id=job_id))
    file.process_status = "PENDING"
    file.process_error = None
    await db.commit()
    return job_id


async def dispatch_processing_job(job_id):
    settings = get_settings()
    async with SessionLocal() as db:
        job = await db.get(ProcessingJob, job_id)
        if not job or job.status in {"COMPLETED", "CANCELLED"}:
            return
        file_id = job.file_id
        await db.execute(
            update(IndexOutbox).where(IndexOutbox.job_id == job_id).values(attempts=IndexOutbox.attempts + 1)
        )
        await db.commit()
    if settings.task_mode.lower() == "kafka":
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await producer.start()
        try:
            await producer.send_and_wait(
                settings.kafka_topic, json.dumps({"fileId": file_id, "jobId": job_id}).encode()
            )
        finally:
            await producer.stop()
    else:
        await run_processing_job(job_id)
    async with SessionLocal() as db:
        await db.execute(
            update(IndexOutbox).where(IndexOutbox.job_id == job_id).values(delivered_at=utcnow())
        )
        await db.commit()


async def claim_job(job_id):
    settings = get_settings()
    async with SessionLocal() as db:
        now = await database_now(db)
        owner = uuid.uuid4().hex
        result = await db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.job_id == job_id,
                ProcessingJob.attempts < max(1, settings.index_max_attempts),
                select(FileUpload.id)
                .where(
                    FileUpload.id == ProcessingJob.file_id,
                    FileUpload.input_revision == ProcessingJob.input_revision,
                    FileUpload.deleted_at.is_(None),
                )
                .exists(),
                or_(
                    ProcessingJob.status.in_(["PENDING", "FAILED"]),
                    (ProcessingJob.status == "RUNNING")
                    & or_(ProcessingJob.lease_until <= now, ProcessingJob.lease_until.is_(None)),
                ),
            )
            .values(
                status="RUNNING",
                lease_owner=owner,
                lease_until=now + timedelta(seconds=max(3, settings.index_lease_seconds)),
                attempts=ProcessingJob.attempts + 1,
                last_error=None,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            return None
        job = await db.get(ProcessingJob, job_id)
        await db.commit()
        return owner, job.file_id, job.input_revision


async def run_processing_job(job_id):
    claimed = await claim_job(job_id)
    if not claimed:
        return
    owner, file_id, expected_revision = claimed
    settings = get_settings()
    job_lost = False

    async def execute():
        async with SessionLocal() as db:
            await process_file(db, file_id, expected_revision=expected_revision)

    work = asyncio.create_task(execute(), name=f"index-job:{job_id}")

    async def heartbeat():
        nonlocal job_lost
        while True:
            await asyncio.sleep(max(1, settings.index_lease_seconds / 3))
            async with SessionLocal() as db:
                now = await database_now(db)
                result = await db.execute(
                    update(ProcessingJob)
                    .where(
                        ProcessingJob.job_id == job_id,
                        ProcessingJob.status == "RUNNING",
                        ProcessingJob.lease_owner == owner,
                        ProcessingJob.lease_until > now,
                    )
                    .values(lease_until=now + timedelta(seconds=max(3, settings.index_lease_seconds)))
                )
                await db.commit()
                if result.rowcount != 1:
                    job_lost = True
                    work.cancel()
                    return

    pulse = asyncio.create_task(heartbeat())
    status, error = "COMPLETED", None
    busy = False
    try:
        await work
    except asyncio.CancelledError as exc:
        status, error = "FAILED", "Job lease lost or execution interrupted"
        if job_lost:
            raise LeaseLost("Job no longer owns its execution lease") from exc
        raise
    except IndexBusy as exc:
        status, error, busy = "PENDING", str(exc), True
    except BaseException as exc:
        status, error = "FAILED", str(exc)[:2000]
        raise
    finally:
        pulse.cancel()
        with suppress(asyncio.CancelledError):
            await pulse
        async with SessionLocal() as db:
            values = {
                "status": status,
                "last_error": error,
                "lease_owner": None,
                "lease_until": None,
                "completed_at": utcnow() if status == "COMPLETED" else None,
            }
            if busy:
                values["attempts"] = ProcessingJob.attempts - 1
            await db.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.job_id == job_id,
                    ProcessingJob.lease_owner == owner,
                    ProcessingJob.status == "RUNNING",
                )
                .values(**values)
            )
            await db.commit()


async def resume_processing_jobs(*, user_id=None):
    # Repair the legacy upload-commit -> request-create crash window. New
    # metadata updates create request+outbox in their own update transaction.
    valid_input = (
        select(FileUpload.id)
        .where(
            FileUpload.id == ProcessingJob.file_id,
            FileUpload.input_revision == ProcessingJob.input_revision,
            FileUpload.deleted_at.is_(None),
        )
        .exists()
    )
    owner_scope = (
        ProcessingJob.file_id.in_(select(FileUpload.id).where(FileUpload.user_id == str(user_id)))
        if user_id is not None
        else True
    )
    async with SessionLocal() as db:
        await db.execute(
            update(ProcessingJob)
            .where(owner_scope, ~valid_input, ProcessingJob.status.in_(["PENDING", "FAILED", "RUNNING"]))
            .values(status="CANCELLED", lease_owner=None, lease_until=None)
        )
        await db.commit()
    async with SessionLocal() as db:
        missing = list(
            (
                await db.scalars(
                    select(FileUpload.id)
                    .where(
                        FileUpload.status == 1,
                        FileUpload.user_id == str(user_id) if user_id is not None else True,
                        FileUpload.process_status == "PENDING",
                        FileUpload.deleted_at.is_(None),
                        FileUpload.storage_key.is_not(None),
                        ~select(ProcessingJob.job_id)
                        .where(
                            ProcessingJob.file_id == FileUpload.id,
                            ProcessingJob.input_revision == FileUpload.input_revision,
                        )
                        .exists(),
                    )
                    .limit(20)
                )
            ).all()
        )
    for file_id in missing:
        await create_processing_job(file_id)
    async with SessionLocal() as db:
        now = await database_now(db)
        rows = list(
            (
                await db.scalars(
                    select(ProcessingJob)
                    .where(
                        ProcessingJob.attempts < max(1, get_settings().index_max_attempts),
                        valid_input,
                        ProcessingJob.file_id.in_(
                            select(FileUpload.id).where(FileUpload.user_id == str(user_id))
                        )
                        if user_id is not None
                        else True,
                        or_(
                            ProcessingJob.status.in_(["PENDING", "FAILED"]),
                            (ProcessingJob.status == "RUNNING")
                            & or_(ProcessingJob.lease_until <= now, ProcessingJob.lease_until.is_(None)),
                        ),
                    )
                    .order_by(ProcessingJob.updated_at)
                    .limit(20)
                )
            ).all()
        )
        ids = [row.job_id for row in rows]

    # Await completion so the periodic scanner cannot spawn unbounded copies.
    async def dispatch_safely(job_id):
        try:
            await dispatch_processing_job(job_id)
        except Exception:
            logger.exception("Index job dispatch/execution failed: %s", job_id)

    await asyncio.gather(*(dispatch_safely(job_id) for job_id in ids))
    return ids


async def maintenance_loop():
    from app.documents.lifecycle import collect_garbage, reconcile_usage

    while True:
        try:
            await resume_processing_jobs()
            await collect_garbage()
            await reconcile_usage()
        except Exception:
            logger.exception("Index maintenance failed")
        await asyncio.sleep(5)


async def enqueue_file_processing(file_id):
    await dispatch_processing_job(await create_processing_job(file_id))
