"""Create a real-indexed fixture, then inject a missing source for a failed rebuild."""

import asyncio
import hashlib
import json
import time
from pathlib import Path
import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.models import FileUpload, ProcessingJob

ROOT = Path(__file__).resolve().parents[1]


async def main():
    engine = create_async_engine("mysql+aiomysql://root:rag-test-only@127.0.0.1:13316/rag_http_acceptance")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    with httpx.Client(base_url="http://127.0.0.1:18016/api/v1", trust_env=False, timeout=30) as c:
        response = c.post("/users/login", json={"username": "ragaccept", "password": "RagAccept123"})
        response.raise_for_status()
        c.headers["Authorization"] = "Bearer " + response.json()["data"]["token"]
        raw = b"# UI acceptance\nThe active knowledge remains readable when rebuilding fails. HTTP 401 requires a valid token.\n"
        md5 = hashlib.md5(raw).hexdigest()
        response = c.post(
            "/upload/chunk",
            data={
                "fileMd5": md5,
                "chunkIndex": 0,
                "totalSize": len(raw),
                "fileName": "ui-old-version.md",
                "isPublic": "false",
            },
            files={"file": ("sample.md", raw)},
        )
        response.raise_for_status()
        response = c.post("/upload/merge", json={"fileMd5": md5})
        response.raise_for_status()
        job = response.json()["data"]["processingJobId"]

        def wait(job_id, status):
            end = time.monotonic() + 40
            while time.monotonic() < end:
                response = c.get("/documents/processing-jobs/" + job_id)
                response.raise_for_status()
                result = response.json()["data"]
                if result["status"] == status:
                    return result
                time.sleep(0.2)
            raise RuntimeError("UI fixture job timed out")

        initial = wait(job, "COMPLETED")
        async with sessions() as db:
            file = await db.scalar(select(FileUpload).where(FileUpload.file_md5 == md5))
            original = file.storage_key
            file_id = file.id
            file.storage_key = "missing-ui-fixture"
            await db.commit()
        try:
            response = c.post("/documents/" + md5 + "/reindex")
            response.raise_for_status()
            job = response.json()["data"]["processingJobId"]
            failed = wait(job, "FAILED")
            assert (
                failed["activeIndexAvailable"]
                and failed["activeVectorVersion"] == initial["activeVectorVersion"]
            )
            async with sessions() as db:
                await db.execute(update(ProcessingJob).where(ProcessingJob.job_id == job).values(attempts=3))
                await db.commit()
        finally:
            async with sessions() as db:
                await db.execute(
                    update(FileUpload).where(FileUpload.id == file_id).values(storage_key=original)
                )
                await db.commit()
        (ROOT / "data/checkpoints/ui-fixture.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "fileMd5": md5,
                    "name": "ui-old-version.md",
                    "fault": "dedicated fixture source missing during rebuild, restored after failure",
                    "activeVersionPreserved": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
