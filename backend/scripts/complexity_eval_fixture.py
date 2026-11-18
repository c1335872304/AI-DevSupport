"""Create only owned Demo API request observations for paired live evaluation."""

import asyncio
import json
import re
import sys
from pathlib import Path


async def main(action="prepare", label=None, phase=None):
    from app.core.time import utcnow
    from app.db.models import (
        SupportApiCallLog,
        SupportApiKey,
        SupportApplication,
        SupportRequestObservation,
        User,
    )
    from app.db.session import SessionLocal, engine

    state_path = Path("/evaluation/private/identity.json")
    state = json.loads(state_path.read_text())
    owner = str(state["userId"])
    if action == "recheck":
        assert label in {"fixed", "quota"} and re.fullmatch(r"(baseline|final)(?:_[a-z0-9]+)?", phase or "")
        request_id = state["requests"][label] + "_" + phase
        async with SessionLocal() as db:
            user = await db.get(User, state["userId"])
            assert user.username == state["username"] and user.username.startswith("rag_eval_")
            assert await db.get(SupportApiCallLog, request_id) is None
            status = 200 if label == "fixed" else 429
            observations = (
                {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "ACTIVE"}
                if label == "fixed"
                else {"limiterKind": "QUOTA", "quotaRemaining": 0}
            )
            db.add(
                SupportApiCallLog(
                    request_id=request_id,
                    user_id=owner,
                    app_id=state["appId"],
                    endpoint="/v1/chat",
                    http_status=status,
                    created_at=utcnow(),
                )
            )
            db.add(
                SupportRequestObservation(
                    request_id=request_id,
                    user_id=owner,
                    service_id="demo-api",
                    rule_version="2026-10-v1",
                    observations_json=json.dumps(observations),
                )
            )
            await db.commit()
        await engine.dispose()
        print("Fresh owned recheck request created after preceding diagnostic turn")
        return
    assert action == "prepare" and not state.get("requests")
    app_id = "app_chain_" + owner
    requests = {
        name: "req_chain_" + owner + "_" + name for name in ("expired", "fixed", "rate", "quota", "unknown")
    }
    async with SessionLocal() as db:
        user = await db.get(User, state["userId"])
        assert user.username == state["username"] and user.username.startswith("rag_eval_")
        db.add(SupportApplication(id=app_id, user_id=owner, name="Temporary paired Demo API evaluation"))
        db.add(
            SupportApiKey(
                id="key_chain_" + owner, user_id=owner, app_id=app_id, key_masked="demo-***", status="ACTIVE"
            )
        )
        for name, status, observations in [
            ("expired", 401, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "EXPIRED"}),
            ("fixed", 200, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "ACTIVE"}),
            ("rate", 429, {"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}),
            ("quota", 429, {"limiterKind": "QUOTA", "quotaRemaining": 0}),
        ]:
            db.add(
                SupportApiCallLog(
                    request_id=requests[name],
                    user_id=owner,
                    app_id=app_id,
                    endpoint="/v1/chat",
                    http_status=status,
                    created_at=utcnow(),
                )
            )
            db.add(
                SupportRequestObservation(
                    request_id=requests[name],
                    user_id=owner,
                    service_id="demo-api",
                    rule_version="2026-10-v1",
                    observations_json=json.dumps(observations),
                )
            )
        await db.commit()
    state.update(requests=requests, appId=app_id)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf8")
    await engine.dispose()
    print("Four owned Demo request observations created; unknown ID intentionally has no record")


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
