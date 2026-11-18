"""Matched three-way retrieval replay using frozen real Qwen query vectors."""

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


async def main(args):
    checkpoint = ROOT / "data/checkpoints"
    output = checkpoint / "phase4"
    output.mkdir(parents=True, exist_ok=True)
    if args.system == "baseline":
        runtime = output / "baseline-runtime"
        with zipfile.ZipFile(checkpoint / "phase1-start/source.zip") as archive:
            for item in archive.infolist():
                if item.filename.startswith("backend/app/") and ".." not in Path(item.filename).parts:
                    archive.extract(item, runtime)
        sys.path.insert(0, str(runtime / "backend"))
    else:
        sys.path.insert(0, str(ROOT))
    target = output / f"retrieval-{args.system}-{uuid.uuid4().hex[:8]}.sqlite"
    with sqlite3.connect(checkpoint / "phase4-start/database.sqlite") as db:
        with sqlite3.connect(target) as saved:
            db.backup(saved)
    os.environ.update(
        DATABASE_URL="sqlite+aiosqlite:///" + target.as_posix(),
        SEARCH_BACKEND="database",
        LLM_API_KEY="",
        EMBEDDING_API_KEY="",
        REDIS_ENABLED="false",
    )
    from sqlalchemy import select

    from app.db.models import User
    from app.db.session import SessionLocal, engine
    from app.evaluation.rag import EvalExpectation, aggregate_metrics, evaluate_ranking
    from app.knowledge.embedding import embedding_service
    from app.knowledge.rag import rag_service

    cached = json.loads((checkpoint / "phase1-start/query-vectors.json").read_text(encoding="utf-8"))

    async def frozen(texts):
        return [cached[text] for text in texts]  # Missing means error, never live fallback.

    embedding_service.embed = frozen
    dataset_path = ROOT / "eval/vendor_full_rag.jsonl"
    dataset = [
        json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if args.system == "plain":
        # Dense-only ablation: same ACL, metadata, active pointers and vectors;
        # no lexical component, reranker or parent expansion.
        rag_service._terms = lambda _: []
    details = []
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == "admin"))
        for case in dataset:
            start = time.perf_counter()
            method = rag_service._search_database if args.system == "plain" else rag_service.search
            results = await method(db, user, case["question"], 6, metadata_filters=case.get("filters"))
            metrics = evaluate_ranking(
                results,
                EvalExpectation(file_md5=case.get("expectedFileMd5"), file_name=case.get("expectedFileName")),
                6,
            )
            details.append(
                {
                    "id": case["id"],
                    "caseType": case["caseType"],
                    "metrics": metrics,
                    "durationMs": (time.perf_counter() - start) * 1000,
                    "results": [
                        {k: r.get(k) for k in ("fileName", "fileMd5", "chunkId", "indexVersion")}
                        for r in results
                    ],
                }
            )

    def latency(rows):
        values = sorted(r["durationMs"] for r in rows)
        import math

        return {
            "n": len(values),
            "p50Ms": values[math.ceil(len(values) * 0.5) - 1],
            "p95Ms": values[math.ceil(len(values) * 0.95) - 1],
        }

    report = {
        "system": args.system,
        "k": 6,
        "providerCalls": 0,
        "queryEncoding": "frozen-real-Qwen-v4-256",
        "documentEncodingCalls": 0,
        "datasetSha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "summary": aggregate_metrics([r["metrics"] for r in details]),
        "latency": latency(details),
        "byCaseType": {
            kind: {
                "metrics": aggregate_metrics([r["metrics"] for r in details if r["caseType"] == kind]),
                "latency": latency([r for r in details if r["caseType"] == kind]),
            }
            for kind in {r["caseType"] for r in details}
        },
        "failures": [r["id"] for r in details if not r["metrics"]["hit"]],
        "details": details,
        "scope": "sequential SQLite; no Provider latency; not a load test; legacy 120 queries are regression, not a blind holdout",
    }
    (output / f"retrieval-{args.system}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k not in {"details", "byCaseType"}}))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["plain", "baseline", "final"], required=True)
    asyncio.run(main(parser.parse_args()))
