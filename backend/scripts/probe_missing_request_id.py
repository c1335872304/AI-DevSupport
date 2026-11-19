"""Replay request diagnostics that never receive a request ID."""
import asyncio
from datetime import datetime
import sys

import probe_incremental_intent as probe
from run_phase_b_docker import seed


probe.SCENARIOS = {
    "matching_window": (
        "我的接口一直失败，帮我查原因。",
        "我一直找不到请求号，可以用别的信息查吗？",
        "接口是 /v1/chat，返回 HTTP 429。",
        "发生在 2026-11-18 17:30 UTC+8 左右。",
    ),
    "empty_window": (
        "请求号拿不到，/v1/chat 出了问题。",
        "发生时间是 2026-11-18 17:30 UTC+8。",
        "错误是 HTTP 503。",
    ),
    "corrected_window": (
        "没有请求号，/v1/completions 返回 HTTP 429。",
        "刚才接口说错了，是 /v1/chat。",
        "发生在 2026-11-18 17:30。",
        "北京时间，刚才说的 17:30 是北京时间。",
    ),
}


async def seed_windows():
    from sqlalchemy import select

    from app.db.models import SupportApiCallLog, User
    from app.db.session import SessionLocal

    await seed()
    async with SessionLocal() as db:
        for index, (name, hour, endpoint) in enumerate((
            ("trace-down-1", 9, "/v1/chat"),
            ("trace-down-2", 7, "/v1/chat"),
            ("billing-1", 9, "/v1/chat"),
            ("billing-1", 9, "/v1/completions"),
        )):
            owner = await db.scalar(select(User.id).where(User.username == name))
            db.add(SupportApiCallLog(
                request_id=f"window_fixture_{index}", user_id=str(owner), app_id="app_fixture",
                endpoint=endpoint, http_status=429, created_at=datetime(2026, 11, 18, hour, 30),
            ))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_windows() if sys.argv[1] == "--seed" else probe.run(sys.argv[1]))
