"""Real Kafka delivery + DB/ES indexing with an explicit embedding fixture."""

import asyncio
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(
    {
        "DATABASE_URL": "mysql+aiomysql://root:rag-test-only@127.0.0.1:13316/rag_kafka_acceptance",
        "SEARCH_BACKEND": "elasticsearch",
        "ELASTICSEARCH_URL": "http://127.0.0.1:19216",
        "ELASTICSEARCH_INDEX": "rag-acceptance-kafka",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(ROOT / "data/kafka-acceptance-storage"),
        "TASK_MODE": "kafka",
        "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:19092",
        "KAFKA_TOPIC": "rag-acceptance-" + uuid.uuid4().hex[:10],
    }
)


async def main():
    from aiokafka import AIOKafkaConsumer
    from sqlalchemy import select, func
    from app.core.config import get_settings
    from app.db.session import SessionLocal, engine
    from app.db.models import User, FileUpload, IndexBuild, ProcessingJob
    from app.documents.storage import storage_service
    from app.documents import job_runtime as jobs
    from app.knowledge.embedding import embedding_service
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.accounting.embedding_usage import record_embedding_usage

    calls = 0

    async def fixture(texts):
        nonlocal calls
        calls += 1
        record_embedding_usage({"total_tokens": 5}, "kafka-fixture-" + str(calls))
        return [[1.0] + [0.0] * 255 for _ in texts]

    embedding_service.embed = fixture
    settings = get_settings()
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="acceptance-" + uuid.uuid4().hex,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    try:
        await asyncio.wait_for(consumer.start(), 30)
        async with SessionLocal() as db:
            user = User(username="kafka-" + uuid.uuid4().hex[:10], password="unused")
            db.add(user)
            await db.commit()
            user_id = user.id

        async def create_file(label):
            raw = ("# " + label + "\n401 requires a valid token.").encode()
            key = "tests/" + uuid.uuid4().hex + ".md"
            await storage_service.put_bytes(key, raw)
            async with SessionLocal() as db:
                file = FileUpload(
                    file_name=label + ".md",
                    file_md5=hashlib.md5(raw).hexdigest(),
                    user_id=str(user_id),
                    storage_key=key,
                    status=1,
                )
                db.add(file)
                await db.commit()
                return file.id

        first = await create_file("duplicate-" + uuid.uuid4().hex[:6])
        job_id = await jobs.create_processing_job(first)
        await jobs.dispatch_processing_job(job_id)
        await jobs.dispatch_processing_job(job_id)
        for _ in range(2):
            message = await asyncio.wait_for(consumer.getone(), 30)
            await jobs.run_processing_job(json.loads(message.value)["jobId"])
            await consumer.commit()
        assert calls == 1
        second = await create_file("lost-notification-" + uuid.uuid4().hex[:6])
        lost = await jobs.create_processing_job(second)
        await jobs.resume_processing_jobs()  # No direct notification: durable scan republishes it.
        message = await asyncio.wait_for(consumer.getone(), 30)
        assert json.loads(message.value)["jobId"] == lost
        await jobs.run_processing_job(lost)
        await consumer.commit()
        async with SessionLocal() as db:
            assert (await db.get(ProcessingJob, job_id)).status == "COMPLETED"
            assert (await db.get(ProcessingJob, lost)).status == "COMPLETED"
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(IndexBuild)
                    .where(IndexBuild.file_id.in_([first, second]))
                )
                == 2
            )
        assert calls == 2
        report = {
            "passed": True,
            "duplicateMessages": 2,
            "duplicateBuilds": 1,
            "lostNotificationRecovered": True,
            "embedding": "explicit fixture; zero provider calls",
            "dependencies": ["Kafka", "MySQL", "Elasticsearch"],
        }
        (ROOT / "data/checkpoints/kafka-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
    finally:
        await consumer.stop()
        await elasticsearch_service.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
