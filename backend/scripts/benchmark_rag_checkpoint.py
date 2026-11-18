"""Small matched latency check with the same frozen query vectors in both modes."""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--old", action="store_true")
args = parser.parse_args()
checkpoint = ROOT / "data/checkpoints/phase1-start"
sys.path.insert(0, str(checkpoint / "baseline-runtime/backend") if args.old else str(ROOT))
os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///"
    + (
        checkpoint / "database.sqlite" if args.old else ROOT / "data/checkpoints/retrieval-after.sqlite"
    ).as_posix()
)
os.environ["SEARCH_BACKEND"] = "database"


async def main():
    from sqlalchemy import select
    from app.db.session import SessionLocal, engine
    from app.db.models import User
    from app.knowledge.rag import rag_service
    from app.knowledge.embedding import embedding_service

    cache = json.loads((checkpoint / "query-vectors.json").read_text(encoding="utf-8"))

    async def frozen(texts):
        return [cache[t] for t in texts]

    embedding_service.embed = frozen
    dataset = [
        json.loads(line)
        for line in (ROOT / "eval/vendor_full_rag.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    samples = []
    try:
        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.username == "admin"))
            for i in range(0, len(dataset), 10):
                case = dataset[i]
                start = time.monotonic()
                await rag_service.search(db, user, case["question"], 6, metadata_filters=case.get("filters"))
                samples.append((time.monotonic() - start) * 1000)
    finally:
        await engine.dispose()
    mode = "before" if args.old else "after"
    report = {
        "mode": mode,
        "samplesMs": samples,
        "p50Ms": statistics.median(samples),
        "p95Ms": sorted(samples)[max(0, __import__("math").ceil(len(samples) * 0.95) - 1)],
        "scope": "12 sequential queries on SQLite copy with frozen real Qwen vectors; no provider latency; not a load test",
    }
    (ROOT / f"data/checkpoints/latency-{mode}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
