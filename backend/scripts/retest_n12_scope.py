"""Bounded live N12 retest using a private backup of the local knowledge DB."""

import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/checkpoints/n12-retest-20261119"


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "knowledge.sqlite"
    if target.exists():
        raise RuntimeError("Keep first attempts intact; use a fresh output directory")
    with sqlite3.connect(f"file:{ROOT / 'data/paismart.db'}?mode=ro", uri=True) as source:
        with sqlite3.connect(target) as dest:
            source.backup(dest)
    os.environ.update(
        DATABASE_URL="sqlite+aiosqlite:///" + target.as_posix(),
        REDIS_ENABLED="false", BILLING_MCP_ENABLED="false", LANGFUSE_ENABLED="false",
        LLM_MAX_RETRIES="0", LLM_MAX_TOKENS="2000",
    )
    from app.accounting.llm_usage import capture_llm_usage
    from app.accounting.embedding_usage import capture_embedding_usage
    from app.agent.runtime import AgentRuntime
    from app.core.config import get_settings
    from app.db.models import User, Base
    from app.db.session import SessionLocal, engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    settings = get_settings()
    assert settings.llm_api_key and settings.embedding_api_key
    original = json.loads((ROOT / "eval/answer_quality_new_v1.json").read_text(encoding="utf-8"))
    cases = [("N12", next(c["question"] for c in original["cases"] if c["id"] == "N12")),
             ("REGION", "按现有Qwen文档，text-embedding-v4在北京和新加坡的价格与免费额度是否相同？请分别注明地域、计费单位和资料时间，不要把一个地域泛化成全部地域。"),
             ("BATCH", "按现有Qwen文档，text-embedding-v4单次请求最多提交多少条文本？这与RPM、TPM限流以及Batch API是否受限流是同一个限制吗？请分别说明并引用。"),
             ("FUTURE", "现有Qwen资料可以保证北京地域text-embedding-v4在2099年仍有当前免费额度、单次批量条数不变吗？新加坡地域的价格能直接当成北京价格吗？")]
    manifest = {"model": settings.llm_model, "cases": cases,
                "databaseSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "mode": "actual AgentRuntime, actual database retrieval and provider calls"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    async with SessionLocal() as db:
        user = await db.get(User, 1)
        assert user
        for case_id, question in cases:
            events = []
            async def send(event):
                events.append(event)
            async def chunk(text):
                pass
            row = {"id": case_id, "question": question}
            with capture_llm_usage() as usage, capture_embedding_usage() as embedding:
                try:
                    async with asyncio.timeout(240):
                        answer, references = await AgentRuntime().run(
                            user=user, question=question, history=[], generation_id=uuid.uuid4().hex,
                            send_json=send, on_chunk=chunk,
                        )
                    row.update(answer=answer, references=references, status="completed")
                except Exception as exc:
                    row.update(status="error", error=repr(exc))
                row.update(usage=asdict(usage), embedding=asdict(embedding), events=events)
            (OUT / f"{case_id}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(case_id, row["status"], usage.total_tokens, flush=True)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True,
                        help="Authorize four live questions, transmitting retrieved excerpts to providers")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    asyncio.run(main())
