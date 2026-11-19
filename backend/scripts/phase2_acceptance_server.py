"""Isolated SQLite UI fixture. No real models, knowledge imports or production data."""

import asyncio
import json
import os
from pathlib import Path
import sys
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite:///" + (ROOT / "data/phase2-ui.sqlite").as_posix(),
        "DATABASE_AUTO_CREATE_DEV": "true",
        "DATABASE_AUTO_MIGRATE": "false",
        "SEARCH_BACKEND": "database",
        "STORAGE_BACKEND": "local",
        "TASK_MODE": "background",
        "LOCAL_STORAGE_DIR": str(ROOT / "data/phase2-ui-storage"),
        "BOOTSTRAP_ADMIN_USERNAME": "diagnosisaccept",
        "BOOTSTRAP_ADMIN_PASSWORD": "DiagnosisAccept123",
        "REDIS_ENABLED": "false",
        "BILLING_MCP_ENABLED": "false",
        "PRIVACY_AUTO_MAINTENANCE_ENABLED": "false",
        "LLM_API_KEY": "",
        "EMBEDDING_API_KEY": "",
        "SKILLS_SEMANTIC_ROUTING_ENABLED": "false",
    }
)


async def prepare():
    from sqlalchemy import select
    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.db.models import (
        ConversationMessage,
        ConversationSession,
        GenerationState,
        SupportApiCallLog,
        User,
    )
    from app.core.time import utcnow
    from app.diagnosis.service import begin_turn, finish_turn
    from app.support.api_diagnostics import query_call_log, query_recent_call_stats
    from app.agent.types import AgentToolCall
    from app.tools.base import ToolResult

    await init_db()
    conversation_id, generation_id = "phase2-ui-conversation", "phase2-ui-generation"
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == "diagnosisaccept"))
        if await db.get(ConversationSession, conversation_id):
            return
        db.add(
            ConversationSession(
                conversation_id=conversation_id, user_id=str(user.id), title="429 诊断状态验收"
            )
        )
        db.add(
            SupportApiCallLog(
                request_id="req_phase2_429",
                user_id=str(user.id),
                app_id="app_phase2",
                endpoint="/v1/chat",
                http_status=429,
                created_at=utcnow() - timedelta(hours=2),
            )
        )
        await db.commit()
        log = await query_call_log(db, str(user.id), "req_phase2_429")
        stats = await query_recent_call_stats(
            db, str(user.id), window="incident", request_id="req_phase2_429"
        )
    question = "请求 req_phase2_429 返回429，请帮我核查。"
    case_id = await begin_turn(
        user_id=str(user.id),
        conversation_id=conversation_id,
        generation_id=generation_id,
        question=question,
        entities={"request_id": "req_phase2_429", "http_status": "429"},
        sources={"request_id": "current", "http_status": "current"},
        diagnostic=True,
    )
    await finish_turn(
        user_id=str(user.id),
        conversation_id=conversation_id,
        generation_id=generation_id,
        question=question,
        references=[],
        outcomes=[
            (
                AgentToolCall("log", "query_call_log", {"request_id": "req_phase2_429"}),
                ToolResult("SUCCESS", log),
            ),
            (
                AgentToolCall(
                    "stats", "query_recent_call_stats", {"window": "incident", "request_id": "req_phase2_429"}
                ),
                ToolResult("SUCCESS", stats),
            ),
        ],
    )
    answer = "记录显示该请求历史返回 HTTP 429；统计只代表故障时间窗口，当前是否恢复仍需复查。"
    async with SessionLocal() as db:
        db.add_all(
            [
                ConversationMessage(
                    conversation_id=conversation_id,
                    user_id=str(user.id),
                    generation_id=generation_id,
                    role="user",
                    content=question,
                ),
                ConversationMessage(
                    conversation_id=conversation_id,
                    user_id=str(user.id),
                    generation_id=generation_id,
                    role="assistant",
                    content=answer,
                ),
                GenerationState(
                    generation_id=generation_id,
                    conversation_id=conversation_id,
                    user_id=str(user.id),
                    question=question,
                    content=answer,
                    status="COMPLETED",
                ),
            ]
        )
        await db.commit()
    (ROOT / "data/checkpoints/phase2-ui-fixture.json").write_text(
        json.dumps(
            {
                "diagnosisId": case_id,
                "conversationId": conversation_id,
                "generationId": generation_id,
                "fixtureOnly": True,
                "providerCalls": 0,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(prepare())
    from app.main import app
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=18026)
