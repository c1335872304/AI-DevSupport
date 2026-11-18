"""Replay frozen real Qwen query vectors on a migrated copy; no provider calls."""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main():
    checkpoint = ROOT / "data/checkpoints/phase1-start"
    target = ROOT / "data/checkpoints/retrieval-after.sqlite"
    if target.exists():
        raise RuntimeError("After-copy already exists; select a fresh checkpoint instead of overwriting it")
    shutil.copy2(checkpoint / "database.sqlite", target)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + target.as_posix()
    os.environ["SEARCH_BACKEND"] = "database"
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
    from app.knowledge.embedding import embedding_service
    from scripts.evaluate_rag import main_async

    cache = json.loads((checkpoint / "query-vectors.json").read_text(encoding="utf-8"))

    async def frozen(texts):
        return [cache[t] for t in texts]  # Missing queries fail rather than call a provider.

    embedding_service.embed = frozen
    report = ROOT / "data/checkpoints/retrieval-after.json"
    await main_async(
        Namespace(dataset=str(ROOT / "eval/vendor_full_rag.jsonl"), username="admin", k=6, output=str(report))
    )
    before = json.loads((checkpoint / "retrieval-before.json").read_text(encoding="utf-8"))
    after = json.loads(report.read_text(encoding="utf-8"))
    assert before["caseCount"] == after["caseCount"] == 120
    assert all(abs(before["summary"][k] - after["summary"][k]) < 1e-10 for k in ("hitRate", "mrr", "ndcg"))
    (ROOT / "data/checkpoints/retrieval-comparison.json").write_text(
        json.dumps(
            {
                "passed": True,
                "method": "Replay frozen real Qwen query vectors; no new embedding calls",
                "before": before["summary"],
                "after": after["summary"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
