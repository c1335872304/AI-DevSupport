from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow `python scripts/evaluate_rag.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.rag import EvalExpectation, aggregate_metrics, evaluate_ranking


def load_dataset(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
        if not str(item.get("question") or "").strip():
            raise ValueError(f"Line {line_no}: question is required")
        if not item.get("expectedFileMd5") and not item.get("expectedFileName"):
            raise ValueError(f"Line {line_no}: expectedFileMd5 or expectedFileName is required")
        rows.append(item)
    return rows


async def main_async(args) -> None:
    # Import DB-dependent modules lazily so `--help` and dataset validation do not require
    # the configured async database driver to be installed first.
    from sqlalchemy import select

    from app.db.models import User
    from app.db.session import SessionLocal, engine
    from app.knowledge.rag import rag_service
    from app.knowledge.elasticsearch import elasticsearch_service

    dataset = load_dataset(Path(args.dataset))
    metric_rows: list[dict[str, float]] = []
    metric_rows_by_case_type: dict[str, list[dict[str, float]]] = {}
    details: list[dict] = []
    try:
        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.username == args.username))
            if not user:
                raise SystemExit(f"User not found: {args.username}")
            for item in dataset:
                results = await rag_service.search(db, user, item["question"], args.k, metadata_filters=item.get("filters"))
                expected = EvalExpectation(
                    file_md5=item.get("expectedFileMd5"),
                    file_name=item.get("expectedFileName"),
                    chunk_ids=frozenset(int(v) for v in item.get("expectedChunkIds", [])),
                )
                metrics = evaluate_ranking(results, expected, args.k)
                metric_rows.append(metrics)
                case_type = str(item.get("caseType") or "uncategorized")
                metric_rows_by_case_type.setdefault(case_type, []).append(metrics)
                details.append(
                    {
                        "id": item.get("id"),
                        "caseType": case_type,
                        "expectedBehavior": item.get("expectedBehavior"),
                        "question": item["question"],
                        "filters": item.get("filters") or {},
                        "metrics": metrics,
                        "topResults": [
                            {
                                "fileMd5": row.get("fileMd5"),
                                "fileName": row.get("fileName"),
                                "chunkId": row.get("chunkId"),
                                "parentChunkId": row.get("parentChunkId"),
                                "score": row.get("score"),
                                "category": row.get("category"),
                                "product": row.get("product"),
                                "region": row.get("region"),
                                "channel": row.get("channel"),
                                "plan": row.get("plan"),
                            }
                            for row in results[: args.k]
                        ],
                    }
                )
    finally:
        await elasticsearch_service.close()
        await engine.dispose()

    report = {
        "k": args.k,
        "caseCount": len(dataset),
        "summary": aggregate_metrics(metric_rows),
        "byCaseType": {
            case_type: {"caseCount": len(rows), "metrics": aggregate_metrics(rows)}
            for case_type, rows in sorted(metric_rows_by_case_type.items())
        },
        "details": details,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate API Assistant RAG retrieval from a JSONL dataset")
    parser.add_argument("dataset", help="JSONL dataset path")
    parser.add_argument("--username", default="admin", help="Existing API Assistant username used for permission-aware retrieval")
    parser.add_argument("-k", type=int, default=6, help="Evaluation cutoff")
    parser.add_argument("--output", help="Optional JSON report path")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
