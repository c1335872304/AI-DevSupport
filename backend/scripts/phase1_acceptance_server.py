"""Dedicated local acceptance API; never points to the application database."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(
    {
        "DATABASE_URL": "mysql+aiomysql://root:rag-test-only@127.0.0.1:13316/rag_http_acceptance",
        "SEARCH_BACKEND": "elasticsearch",
        "ELASTICSEARCH_URL": "http://127.0.0.1:19216",
        "ELASTICSEARCH_INDEX": "rag-acceptance-e2e",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(ROOT / "data/acceptance-storage"),
        "TASK_MODE": "background",
        "DATABASE_AUTO_CREATE_DEV": "false",
        "BOOTSTRAP_ADMIN_USERNAME": "ragaccept",
        "BOOTSTRAP_ADMIN_PASSWORD": "RagAccept123",
        "REDIS_ENABLED": "false",
        "PRIVACY_AUTO_MAINTENANCE_ENABLED": "false",
        "BILLING_MCP_ENABLED": "false",
    }
)
from app.accounting.embedding_usage import capture_embedding_usage
from app.knowledge.embedding import embedding_service
from app.main import app
import uvicorn

original = embedding_service.embed
stats = {"calls": 0, "submittedUtf8Bytes": 0, "providerTokens": 0, "budgetUtf8Bytes": 5000, "maxCalls": 12}


async def bounded(texts):
    upper = sum(len(t.encode()) for t in texts)
    if stats["calls"] >= stats["maxCalls"] or stats["submittedUtf8Bytes"] + upper > stats["budgetUtf8Bytes"]:
        raise RuntimeError("Acceptance provider budget exceeded")
    stats["calls"] += 1
    stats["submittedUtf8Bytes"] += upper
    try:
        with capture_embedding_usage() as meter:
            result = await original(texts)
        stats["providerTokens"] += meter.total_tokens
        return result
    finally:
        (ROOT / "data/checkpoints/e2e-usage.json").write_text(json.dumps(stats), encoding="utf-8")


embedding_service.embed = bounded
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=18016, log_level="info")
