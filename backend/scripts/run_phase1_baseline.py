"""Freeze retrieval baseline on a DB copy; only the 120 queries call Qwen."""

from __future__ import annotations
import asyncio
import json
import os
import sys
import zipfile
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main():
    snapshot = ROOT / "data/checkpoints/phase1-start"
    runtime = snapshot / "baseline-runtime"
    with zipfile.ZipFile(snapshot / "source.zip") as archive:
        for item in archive.infolist():
            if item.filename.startswith(("backend/app/", "backend/scripts/")):
                archive.extract(item, runtime)
    sys.path.insert(0, str(runtime / "backend"))
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (snapshot / "database.sqlite").as_posix()
    os.environ["SEARCH_BACKEND"] = "database"
    from app.accounting.embedding_usage import capture_embedding_usage
    from app.knowledge.embedding import embedding_service
    from scripts.evaluate_rag import main_async

    original = embedding_service.embed
    submitted = 0
    cached = {}

    async def bounded(texts):
        nonlocal submitted
        submitted += sum(len(text.encode("utf-8")) for text in texts)
        if submitted > 30000:
            raise RuntimeError("Baseline input exceeds reserved 30,000 UTF-8 byte budget")
        result = await original(texts)
        cached.update(zip(texts, result))
        return result

    embedding_service.embed = bounded
    with capture_embedding_usage() as usage:
        await main_async(
            Namespace(
                dataset=str(ROOT / "eval/vendor_full_rag.jsonl"),
                username="admin",
                k=6,
                output=str(snapshot / "retrieval-before.json"),
            )
        )
    (snapshot / "query-vectors.json").write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
    (snapshot / "usage.json").write_text(
        json.dumps(
            {
                "providerTokens": usage.total_tokens,
                "submittedUtf8Bytes": submitted,
                "maxSubmittedUtf8Bytes": 30000,
                "documentEncodingCalls": 0,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
