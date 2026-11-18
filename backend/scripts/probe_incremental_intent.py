"""Replay synthetic incremental support conversations through HTTP and WebSocket."""
import asyncio
import json
from pathlib import Path
import sys

from run_phase_b_docker import completed_chat, customer, seed


SCENARIOS = {
    "incremental": (
        "这两天老是失败。",
        "晚上批量跑的时候才有。",
        "就导出接口，返回 HTTP 429。我想知道是跑太快还是额度用完了。",
        "有了，请求号是 req_context_001。",
    ),
    "correction": (
        "上传时总失败，帮我看看。",
        "刚才说错了，是下载失败，不是上传。",
        "准确说是 /v1/chat 请求失败，HTTP 429。",
        "刚翻到那次的请求号 req_context_002，继续查限流原因。",
    ),
    "switch": (
        "接口调用老是失败，帮我查一下。",
        "先不查这个了，换个问题：帮我查 2026 年 11 月账单。",
        "刚才的账单先放一边，回到接口故障。请求号 req_context_003。",
    ),
}


async def run(output):
    with Path(output).open("x", encoding="utf-8") as stream:
        for (scenario, questions), account in zip(
            SCENARIOS.items(), ("trace-down-1", "trace-down-2", "billing-1"), strict=True,
        ):
            async with customer(account) as (client, token):
                for turn, question in enumerate(questions, 1):
                    events = []
                    snapshot = await completed_chat(client, token, question, events)
                    row = {
                        "scenario": scenario, "turn": turn, "question": question,
                        "answer": snapshot["content"], "generationId": snapshot["generationId"],
                        "events": [event for event in events if event.get("type") in {
                            "entities_extracted", "clarification_requested", "routing_decision",
                            "context_assembled", "tool_call", "skill_trace",
                        }],
                    }
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    print(f"{scenario} turn {turn} completed", flush=True)


async def seed_probe():
    from sqlalchemy import select

    from app.core.time import utcnow
    from app.db.models import SupportApiCallLog, SupportRequestObservation, User
    from app.db.session import SessionLocal
    from app.diagnosis.rules import RULE_VERSION

    await seed()
    async with SessionLocal() as db:
        for i, username in enumerate(("trace-down-1", "trace-down-2", "billing-1"), 1):
            owner = await db.scalar(select(User.id).where(User.username == username))
            request_id = f"req_context_{i:03d}"
            db.add(SupportApiCallLog(
                request_id=request_id, user_id=str(owner), app_id="app_context",
                endpoint="/v1/chat", http_status=429, created_at=utcnow(),
            ))
            db.add(SupportRequestObservation(
                request_id=request_id, user_id=str(owner), service_id="demo-api",
                rule_version=RULE_VERSION,
                observations_json=json.dumps({"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}),
            ))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_probe() if sys.argv[1] == "--seed" else run(sys.argv[1]))
