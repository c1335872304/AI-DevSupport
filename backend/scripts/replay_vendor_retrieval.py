"""Read-only Docker retrieval regression using frozen real Qwen query vectors."""

import asyncio
import json
from pathlib import Path


async def main():
    from sqlalchemy import select

    from app.db.models import User
    from app.db.session import SessionLocal, engine
    from app.evaluation.rag import EvalExpectation, aggregate_metrics, evaluate_ranking
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.knowledge.embedding import embedding_service
    from app.knowledge.product_scope import scoped_filters
    from app.knowledge.rag import rag_service

    output = Path("/evaluation")
    vectors = json.loads((output / "query-vectors.json").read_text())

    async def frozen(texts):
        return [vectors[text] for text in texts]

    embedding_service.embed = frozen
    cases = [
        json.loads(line)
        for line in Path("/app/eval/vendor_full_rag.jsonl").read_text().splitlines()
        if line.strip()
    ]
    details = []
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == "admin"))
        for case in cases:
            results = await rag_service.search(
                db, user, case["question"], 6, metadata_filters=case.get("filters")
            )
            scope = scoped_filters(case["question"], case.get("filters")).get("product")
            allowed = [scope] if isinstance(scope, str) else scope
            details.append(
                {
                    "id": case["id"],
                    "scoped": bool(allowed),
                    "foreign": [r["fileName"] for r in results if allowed and r["product"] not in allowed],
                    "metrics": evaluate_ranking(
                        results, EvalExpectation(file_name=case["expectedFileName"]), 6
                    ),
                }
            )
    report = {
        "providerCalls": 0,
        "queryEncoding": "frozen-real-Qwen-v4-256",
        "summary": aggregate_metrics([r["metrics"] for r in details]),
        "scopedCases": sum(r["scoped"] for r in details),
        "scopeViolations": [r for r in details if r["foreign"]],
        "details": details,
    }
    (output / "retrieval-replay.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "details"}))
    await elasticsearch_service.client.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
