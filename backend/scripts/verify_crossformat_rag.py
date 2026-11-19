"""Real Docling + Qwen + MySQL + ES check on equal-content synthetic documents."""

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
        "DATABASE_URL": "mysql+aiomysql://root:rag-test-only@127.0.0.1:13316/rag_acceptance",
        "SEARCH_BACKEND": "elasticsearch",
        "ELASTICSEARCH_URL": "http://127.0.0.1:19216",
        "ELASTICSEARCH_INDEX": "rag-acceptance-format",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(ROOT / "data/format-storage"),
    }
)


async def main():
    from sqlalchemy import select
    from app.db.session import SessionLocal, engine
    from app.db.models import FileUpload, User
    from app.documents.storage import storage_service
    from app.knowledge.build_pipeline import process_file
    from app.knowledge.rag import rag_service
    from app.knowledge.embedding import embedding_service
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.accounting.embedding_usage import capture_embedding_usage

    original = embedding_service.embed
    submitted = 0
    calls = 0
    checks = []

    async def bounded(texts):
        nonlocal submitted, calls
        submitted += sum(len(t.encode()) for t in texts)
        calls += 1
        if submitted > 5000 or calls > 10:
            raise RuntimeError("Cross-format provider budget exceeded")
        return await original(texts)

    embedding_service.embed = bounded
    try:
        with capture_embedding_usage() as usage:
            async with SessionLocal() as db:
                user = User(username="format-" + uuid.uuid4().hex[:10], password="unused", role="USER")
                db.add(user)
                await db.commit()
                for suffix in ("md", "pdf", "docx"):
                    path = ROOT / f"tests/fixtures/docling/equivalent.{suffix}"
                    raw = path.read_bytes()
                    key = f"format/{user.id}/{path.name}"
                    await storage_service.put_bytes(key, raw)
                    file = FileUpload(
                        file_name=path.name,
                        file_md5=hashlib.md5(raw).hexdigest(),
                        user_id=str(user.id),
                        status=1,
                        storage_key=key,
                        knowledge_product="Format " + suffix,
                    )
                    db.add(file)
                    await db.commit()
                    await process_file(db, file.id)
                    results = await rag_service.search(
                        db,
                        user,
                        "AUTH_KEY_INVALID 401 Authorization",
                        6,
                        metadata_filters={"product": "Format " + suffix},
                    )
                    assert any("AUTH_KEY_INVALID" in r.get("textContent", "") for r in results)
                    assert all(r["fileName"] == path.name for r in results)
                    checks.append(
                        {
                            "format": suffix,
                            "passed": True,
                            "results": len(results),
                            "citations": all(r.get("citationId") for r in results),
                        }
                    )
                results = await rag_service.search(db, user, "AUTH_KEY_INVALID returns HTTP 401", 12)
                assert {r["fileName"] for r in results} == {
                    "equivalent.md",
                    "equivalent.pdf",
                    "equivalent.docx",
                }
        report = {
            "checks": checks,
            "naturalQueryAllFormatsFound": True,
            "calls": calls,
            "providerTokens": usage.total_tokens,
            "submittedUtf8Bytes": submitted,
            "scope": "Synthetic equal-content format plumbing; not a general retrieval benchmark",
        }
        (ROOT / "data/checkpoints/crossformat-rag.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
    finally:
        await elasticsearch_service.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
