from __future__ import annotations
import argparse, asyncio, json
from datetime import timedelta
from sqlalchemy import delete, select
from app.db.models import (
    User,
    SupportApplication,
    SupportApiKey,
    SupportApiCallLog,
    SupportErrorCode,
    SupportPlan,
    SupportSubscription,
    SupportUsageRecord,
    SupportInvoice,
    SupportRequestObservation,
)
from app.diagnosis.rules import RULE_VERSION
from app.db.session import SessionLocal, engine
from app.core.time import utcnow


async def seed(username: str, reset: bool = False):
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            raise SystemExit(f"user not found: {username}")
        uid = str(user.id)
        # Request and application identifiers are global primary keys. Keep the
        # administrator's documented names for backwards compatibility, while
        # giving every non-admin demo user an isolated API-support fixture.
        suffix = "" if username == "admin" else f"_u{uid}"
        app_id = f"app_demo{suffix}"
        api_key_id = f"key_demo{suffix}"
        request_401 = f"req_demo_401{suffix}"
        request_429 = f"req_demo_429{suffix}"
        if reset:
            for model in (
                SupportInvoice,
                SupportUsageRecord,
                SupportSubscription,
                SupportRequestObservation,
                SupportApiCallLog,
                SupportApiKey,
                SupportApplication,
            ):
                await db.execute(delete(model).where(model.user_id == uid))
        for row in [
            SupportErrorCode(
                code="AUTH_KEY_EXPIRED",
                name="API Key expired",
                http_status=401,
                cause="The API Key has expired.",
                fix_steps="Create/rotate a valid API Key and retry the request.",
            ),
            SupportErrorCode(
                code="AUTH_KEY_INVALID",
                name="Invalid API Key",
                http_status=401,
                cause="The API Key is invalid or disabled.",
                fix_steps="Verify the masked key identity and use an active key.",
            ),
            SupportErrorCode(
                code="RATE_LIMIT_EXCEEDED",
                name="Rate limit exceeded",
                http_status=429,
                cause="Request rate exceeded the plan QPS limit.",
                fix_steps="Reduce burst rate, add backoff, or request a higher plan limit.",
            ),
        ]:
            if not await db.get(SupportErrorCode, row.code):
                db.add(row)
        if not await db.get(SupportPlan, "pro"):
            db.add(
                SupportPlan(
                    id="pro",
                    name="Professional",
                    qps_limit=50,
                    monthly_quota=1000000,
                    base_price=299.0,
                    overage_price_per_call=0.0005,
                )
            )
        if not await db.get(SupportSubscription, uid):
            db.add(SupportSubscription(user_id=uid, plan_id="pro", status="ACTIVE"))
        if not await db.get(SupportApplication, app_id):
            db.add(SupportApplication(id=app_id, user_id=uid, name="Demo API App", product="OpenAPI"))
        if not await db.get(SupportApiKey, api_key_id):
            db.add(
                SupportApiKey(
                    id=api_key_id,
                    app_id=app_id,
                    user_id=uid,
                    key_masked="ak_****8a2f",
                    status="EXPIRED",
                    expire_at=utcnow() - timedelta(days=1),
                )
            )
        # Observations belong to a newly constructed simulated event. Never infer
        # or backfill historical observations from an old status/current Key.
        for request_id, status, code, observations in (
            (
                request_401,
                401,
                "AUTH_KEY_EXPIRED",
                {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "EXPIRED"},
            ),
            (
                request_429,
                429,
                "RATE_LIMIT_EXCEEDED",
                {"limiterKind": "RATE", "rateObserved": 51, "rateLimit": 50},
            ),
        ):
            if not await db.get(SupportApiCallLog, request_id):
                db.add(
                    SupportApiCallLog(
                        request_id=request_id,
                        user_id=uid,
                        app_id=app_id,
                        api_key_id=api_key_id,
                        endpoint="/v1/chat",
                        http_status=status,
                        error_code=code,
                        latency_ms=44,
                        created_at=utcnow(),
                    )
                )
                db.add(
                    SupportRequestObservation(
                        request_id=request_id,
                        user_id=uid,
                        service_id="demo-api",
                        rule_version=RULE_VERSION,
                        observations_json=json.dumps(observations),
                    )
                )
        if not await db.scalar(
            select(SupportUsageRecord).where(
                SupportUsageRecord.user_id == uid, SupportUsageRecord.month == "2026-08"
            )
        ):
            db.add(SupportUsageRecord(user_id=uid, month="2026-08", call_count=1250000, overage_count=250000))
        if not await db.scalar(
            select(SupportInvoice).where(SupportInvoice.user_id == uid, SupportInvoice.month == "2026-08")
        ):
            db.add(
                SupportInvoice(
                    id=f"inv_{uid}_202608",
                    user_id=uid,
                    month="2026-08",
                    amount=424.0,
                    status="ISSUED",
                    items_json=json.dumps({"baseFee": 299.0, "overageFee": 125.0}),
                )
            )
        await db.commit()
    await engine.dispose()
    print(f"Seeded support demo data for {username}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default="admin")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    asyncio.run(seed(args.username, args.reset))
