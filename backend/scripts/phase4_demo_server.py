"""Three reproducible demos on a separate SQLite DB; no provider or live data."""

import asyncio
from datetime import timedelta
import json
import os
import uuid

from phase3_acceptance_server import ROOT  # Only sets isolated fixture defaults.
from evaluate_phase4_diagnosis import OBS

os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:///" + (ROOT / "data/phase4-demo.sqlite").as_posix(),
    LOCAL_STORAGE_DIR=str(ROOT / "data/phase4-demo-storage"),
)


async def prepare():
    from sqlalchemy import select
    from app.core.time import utcnow
    from app.db.init_db import init_db
    from app.db.models import (
        User,
        ConversationSession,
        ConversationMessage,
        GenerationState,
        SupportApiCallLog,
        SupportRequestObservation,
    )
    from app.db.session import SessionLocal
    from app.diagnosis.service import begin_turn
    from app.diagnosis.execution import run_turn
    from app.tools.registry import tool_registry

    await init_db()
    tag = uuid.uuid4().hex[:8]
    fixtures = []
    for purpose, cause in (
        ("401-recovery", "KEY_EXPIRED"),
        ("429-still-failing", "RATE_LIMIT"),
        ("handoff", "QUOTA_LIMIT"),
    ):
        conversation, generation = f"demo4-{tag}-{purpose}", f"demo4-{tag}-{purpose}-g1"
        request, new = f"req_{tag}_{len(fixtures)}_old", f"req_{tag}_{len(fixtures)}_new"
        code, obs = OBS[cause]
        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.username == "loopaccept"))
            db.add(ConversationSession(conversation_id=conversation, user_id=str(user.id), title=purpose))
            db.add(
                SupportApiCallLog(
                    request_id=request,
                    user_id=str(user.id),
                    app_id="app_demo4",
                    endpoint="/v1/chat",
                    http_status=code,
                    created_at=utcnow() - timedelta(minutes=10),
                )
            )
            db.add(
                SupportRequestObservation(
                    request_id=request,
                    user_id=str(user.id),
                    service_id="demo-api",
                    rule_version="2026-10-v1",
                    observations_json=json.dumps(obs),
                )
            )
            await db.commit()
        question = f"请求 {request} 返回{code}，请核查" + ("并转人工客服" if purpose == "handoff" else "")
        case = await begin_turn(
            user_id=str(user.id),
            conversation_id=conversation,
            generation_id=generation,
            question=question,
            entities={"request_id": request},
            sources={"request_id": "current"},
            diagnostic=True,
        )
        await run_turn(generation, user, tool_registry, finalize=True)
        async with SessionLocal() as db:
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
                        content="模拟业务已核查，完整原因、证据与下一步见诊断面板。",
                    ),
                    GenerationState(
                        generation_id=generation,
                        conversation_id=conversation,
                        user_id=str(user.id),
                        question=question,
                        content="查看诊断面板",
                        status="COMPLETED",
                    ),
                ]
            )
            db.add(
                SupportApiCallLog(
                    request_id=new,
                    user_id=str(user.id),
                    app_id="app_demo4",
                    endpoint="/v1/chat",
                    http_status=429 if purpose == "429-still-failing" else 200,
                    created_at=utcnow(),
                )
            )
            if purpose == "429-still-failing":
                db.add(
                    SupportRequestObservation(
                        request_id=new,
                        user_id=str(user.id),
                        service_id="demo-api",
                        rule_version="2026-10-v1",
                        observations_json=json.dumps(OBS["QUOTA_LIMIT"][1]),
                    )
                )
            await db.commit()
        fixtures.append(
            {
                "purpose": purpose,
                "diagnosisId": case,
                "generationId": generation,
                "conversationId": conversation,
                "requestId": new,
            }
        )
    (ROOT / "data/checkpoints/phase4/demos-fixture.json").write_text(
        json.dumps(fixtures, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    (ROOT / "data/checkpoints/phase4").mkdir(parents=True, exist_ok=True)
    asyncio.run(prepare())
    from app.main import app
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=18046)
