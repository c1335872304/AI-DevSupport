from __future__ import annotations

import asyncio
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.knowledge.indexer import process_file
from app.documents.jobs import run_processing_job


async def run() -> None:
    settings = get_settings()
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await consumer.start()
    await producer.start()
    try:
        async for message in consumer:
            attempt = 0
            file_id = None
            try:
                payload = json.loads(message.value.decode("utf-8"))
                file_id = int(payload["fileId"])
                job_id = str(payload.get("jobId") or "").strip()
                attempt = int(payload.get("attempt") or 0)
                if job_id:
                    await run_processing_job(job_id)
                else:
                    async with SessionLocal() as db:
                        await process_file(db, file_id)
                await consumer.commit()
            except Exception as exc:
                error = str(exc)[:1000]
                envelope = {"fileId": file_id, "jobId": str(locals().get("job_id") or ""), "attempt": attempt + 1, "error": error}
                if file_id is not None and attempt < max(0, settings.kafka_retry_attempts):
                    await asyncio.sleep(max(0.0, settings.kafka_retry_backoff_seconds) * (2 ** attempt))
                    await producer.send_and_wait(settings.kafka_topic, json.dumps(envelope).encode("utf-8"))
                else:
                    envelope.update({"raw": message.value.decode("utf-8", errors="replace")[:4000]})
                    await producer.send_and_wait(settings.kafka_dlq_topic, json.dumps(envelope).encode("utf-8"))
                # Commit only after retry/DLQ publication succeeds; poison messages no longer
                # block the partition forever and no failed job disappears silently.
                await consumer.commit()
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run())
