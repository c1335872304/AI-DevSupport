from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ProcessingJob
from app.db.session import SessionLocal
from app.knowledge.indexer import process_file


async def create_processing_job(file_id: int) -> str:
    job_id = uuid.uuid4().hex
    async with SessionLocal() as db:
        db.add(ProcessingJob(job_id=job_id, file_id=file_id, status="PENDING"))
        await db.commit()
    return job_id


async def dispatch_processing_job(job_id: str) -> None:
    settings = get_settings()
    if settings.task_mode.lower() == "kafka":
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            raise RuntimeError("TASK_MODE=kafka requires the 'aiokafka' package") from exc
        async with SessionLocal() as db:
            job = await db.get(ProcessingJob, job_id)
            if not job:
                return
            file_id = job.file_id
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await producer.start()
        try:
            await producer.send_and_wait(settings.kafka_topic, json.dumps({"fileId": file_id, "jobId": job_id, "attempt": 0}).encode("utf-8"))
        finally:
            await producer.stop()
        return
    await run_processing_job(job_id)


async def run_processing_job(job_id: str) -> None:
    async with SessionLocal() as db:
        job = await db.get(ProcessingJob, job_id)
        if not job or job.status == "COMPLETED":
            return
        job.status = "RUNNING"
        job.attempts = int(job.attempts or 0) + 1
        job.last_error = None
        await db.commit()
        try:
            await process_file(db, job.file_id)
            job = await db.get(ProcessingJob, job_id)
            if job:
                job.status = "COMPLETED"
                job.completed_at = datetime.utcnow()
                await db.commit()
        except Exception as exc:
            await db.rollback()
            job = await db.get(ProcessingJob, job_id)
            if job:
                job.status = "FAILED"
                job.last_error = str(exc)[:2000]
                await db.commit()
            raise


async def resume_processing_jobs() -> list[str]:
    """Resume jobs left behind by a process restart in background mode."""
    settings = get_settings()
    if settings.task_mode.lower() != "background":
        return []
    async with SessionLocal() as db:
        rows = list((await db.scalars(select(ProcessingJob).where(ProcessingJob.status.in_(["PENDING", "RUNNING"])))).all())
        ids = [row.job_id for row in rows]
        for row in rows:
            if row.status == "RUNNING":
                row.status = "PENDING"
        await db.commit()
    for job_id in ids:
        asyncio.create_task(run_processing_job(job_id), name=f"processing-job:{job_id}")
    return ids


# Backward-compatible helper used by older callers/tests.
async def enqueue_file_processing(file_id: int) -> None:
    job_id = await create_processing_job(file_id)
    await dispatch_processing_job(job_id)
