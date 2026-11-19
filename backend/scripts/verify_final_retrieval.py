"""Final read-only replay on the migrated application knowledge, without provider calls."""

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main():
    from app.knowledge.embedding import embedding_service
    from app.knowledge.rag import rag_service
    from scripts.evaluate_rag import main_async

    checkpoint = ROOT / "data/checkpoints"
    cache = json.loads((checkpoint / "phase1-start/query-vectors.json").read_text(encoding="utf-8"))

    async def frozen(texts):
        return [cache[t] for t in texts]

    embedding_service.embed = frozen
    rag_service.settings.search_backend = "database"
    await main_async(
        Namespace(
            dataset=str(ROOT / "eval/vendor_full_rag.jsonl"),
            username="admin",
            k=6,
            output=str(checkpoint / "retrieval-final.json"),
        )
    )
    before = json.loads((checkpoint / "phase1-start/retrieval-before.json").read_text(encoding="utf-8"))
    after = json.loads((checkpoint / "retrieval-final.json").read_text(encoding="utf-8"))
    assert all(abs(before["summary"][k] - after["summary"][k]) < 1e-10 for k in ("hitRate", "mrr", "ndcg"))
    (checkpoint / "retrieval-final-comparison.json").write_text(
        json.dumps(
            {"passed": True, "providerCalls": 0, "before": before["summary"], "after": after["summary"]},
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
