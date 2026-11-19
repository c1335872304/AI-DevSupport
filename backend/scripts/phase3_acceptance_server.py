"""Isolated P3 UI fixture. Never loads application data or calls a model."""

import asyncio
import json
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite:///" + (ROOT / "data/phase3-ui.sqlite").as_posix(),
        "DATABASE_AUTO_CREATE_DEV": "true",
        "DATABASE_AUTO_MIGRATE": "false",
        "SEARCH_BACKEND": "database",
        "STORAGE_BACKEND": "local",
        "TASK_MODE": "background",
        "LOCAL_STORAGE_DIR": str(ROOT / "data/phase3-ui-storage"),
        "BOOTSTRAP_ADMIN_USERNAME": "loopaccept",
        "BOOTSTRAP_ADMIN_PASSWORD": "LoopAccept123",
        "REDIS_ENABLED": "false",
        "BILLING_MCP_ENABLED": "false",
        "PRIVACY_AUTO_MAINTENANCE_ENABLED": "false",
        "DIAGNOSIS_RECOVERY_ENABLED": "true",
        "LLM_API_KEY": "",
        "EMBEDDING_API_KEY": "",
        "SKILLS_SEMANTIC_ROUTING_ENABLED": "false",
    }
)


async def prepare():
    from sqlalchemy import select

    from app.core.time import utcnow
    from app.db.init_db import init_db
    from app.db.models import (
        ConversationMessage,
        ConversationSession,
        GenerationState,
        SupportApiCallLog,
        SupportRequestObservation,
        User,
    )
    from app.db.session import SessionLocal
    from app.diagnosis.execution import run_turn
    from app.diagnosis.rules import RULE_VERSION
    from app.diagnosis.service import begin_turn
    from app.tools.registry import tool_registry

    await init_db()
    tag = uuid.uuid4().hex[:10]
    cases = []
    for purpose in ("http", "ui"):
        conversation, generation = f"p3-{tag}-{purpose}", f"p3-{tag}-{purpose}-g1"
        old, new = f"req_{tag}_{purpose}_old", f"req_{tag}_{purpose}_new"
        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.username == "loopaccept"))
            db.add(
                ConversationSession(
                    conversation_id=conversation, user_id=str(user.id), title=f"第三阶段闭环验收 {purpose}"
                )
            )
            db.add(
                SupportApiCallLog(
                    request_id=old,
                    user_id=str(user.id),
                    app_id="app_p3",
                    endpoint="/v1/chat",
                    http_status=429,
                    created_at=utcnow() - timedelta(minutes=10),
                )
            )
            db.add(
                SupportRequestObservation(
                    request_id=old,
                    user_id=str(user.id),
                    service_id="demo-api",
                    rule_version=RULE_VERSION,
                    observations_json=json.dumps(
                        {"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}
                    ),
                )
            )
            await db.commit()
        question = f"请求 {old} 返回429，请核查。"
        case = await begin_turn(
            user_id=str(user.id),
            conversation_id=conversation,
            generation_id=generation,
            question=question,
            entities={"request_id": old},
            sources={"request_id": "current"},
            diagnostic=True,
        )
        await run_turn(generation, user, tool_registry, finalize=True)
        answer = "请求时的脱敏观测支持频率限制。请降低请求频率，再提供新请求号复查。"
        async with SessionLocal() as db:
            db.add(
                SupportApiCallLog(
                    request_id=new,
                    user_id=str(user.id),
                    app_id="app_p3",
                    endpoint="/v1/chat",
                    http_status=200,
                    created_at=utcnow(),
                )
            )
            db.add_all(
                [
                    ConversationMessage(
                        conversation_id=conversation,
                        user_id=str(user.id),
                        generation_id=generation,
                        role="user",
                        content=question,
                    ),
                    ConversationMessage(
                        conversation_id=conversation,
                        user_id=str(user.id),
                        generation_id=generation,
                        role="assistant",
                        content=answer,
                    ),
                    GenerationState(
                        generation_id=generation,
                        conversation_id=conversation,
                        user_id=str(user.id),
                        question=question,
                        content=answer,
                        status="COMPLETED",
                    ),
                ]
            )
            await db.commit()
        cases.append(
            {
                "purpose": purpose,
                "diagnosisId": case,
                "conversationId": conversation,
                "generationId": generation,
                "requestId": new,
            }
        )
    (ROOT / "data/checkpoints/phase3-ui-fixture.json").write_text(
        json.dumps({"fixtureOnly": True, "providerCalls": 0, "cases": cases}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(prepare())
    import uvicorn

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=18036)
