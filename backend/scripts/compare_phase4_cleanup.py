"""Reproduce frozen baseline cleanup race on disposable SQLite, without providers."""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "data/checkpoints/phase4"
os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///" + (OUTPUT / f"baseline-race-{uuid.uuid4().hex[:8]}.sqlite").as_posix()
)
os.environ.update(LLM_API_KEY="", EMBEDDING_API_KEY="", SEARCH_BACKEND="database")


async def main():
    from sqlalchemy import func, select
    from sqlalchemy.sql.dml import Delete
    from app.db.models import Base, User, FileUpload, DocumentVector
    from app.db.session import SessionLocal, engine

    with zipfile.ZipFile(ROOT / "data/checkpoints/phase1-start/source.zip") as archive:
        path = OUTPUT / "baseline_indexer.py"
        path.write_bytes(archive.read("backend/app/knowledge/indexer.py"))
    spec = importlib.util.spec_from_file_location("baseline_indexer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def raw(*_):
        return b"# Authentication\n401 requires a valid Bearer token."

    async def encode(texts):
        return [[1.0] + [0.0] * 255 for _ in texts]

    async def nothing(*_, **__):
        pass

    module.storage_service.get_bytes = raw
    module.embedding_service.embed = encode
    for name in ("bulk_index", "verify_version", "delete_other_versions", "delete_version"):
        setattr(module.elasticsearch_service, name, nothing)
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        user = User(username="race", password="unused", embedding_token_balance=100000)
        db.add(user)
        await db.flush()
        file = FileUpload(
            file_name="race.md", file_md5=uuid.uuid4().hex, user_id=str(user.id), storage_key="fixture"
        )
        db.add(file)
        await db.commit()
        file_id = file.id
    interleaved = False
    async with SessionLocal() as first:
        original_execute = first.execute

        async def gated(statement, *args, **kwargs):
            nonlocal interleaved
            if (
                not interleaved
                and isinstance(statement, Delete)
                and statement.table.name == "document_vectors"
            ):
                interleaved = True
                async with SessionLocal() as second:
                    await module.process_file(second, file_id)
            return await original_execute(statement, *args, **kwargs)

        first.execute = gated
        await module.process_file(first, file_id)
    async with SessionLocal() as db:
        active = (await db.get(FileUpload, file_id)).active_vector_version
        count = await db.scalar(
            select(func.count()).select_from(DocumentVector).where(DocumentVector.vector_version == active)
        )
    assert interleaved and count == 0, "Frozen baseline race was not reproduced"
    report = {
        "reproduced": True,
        "baselineActiveRowsAfterRace": count,
        "baselineInvariantPassed": False,
        "scope": "real frozen indexer and two DB sessions; embeddings/storage/ES explicitly stubbed; disposable SQLite",
        "finalWitness": "phase4-integration.xml::test_gc_interleaved_with_new_publication_keeps_new_version",
        "providerCalls": 0,
    }
    (OUTPUT / "index-cleanup-comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
