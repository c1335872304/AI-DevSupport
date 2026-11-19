from __future__ import annotations

from datetime import timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SupportApiCallLog, SupportApiKey, SupportErrorCode
from app.core.time import utcnow


async def query_request_observation(db, user_id, request_id):
    import json
    from app.db.models import SupportRequestObservation
    from app.diagnosis.rules import SAFE_OBSERVATIONS

    log = await db.get(SupportApiCallLog, request_id)
    row = await db.get(SupportRequestObservation, request_id)
    base = {"requestId": request_id, "ownerUserId": user_id,
            "queriedAt": timestamp(utcnow()), "sourceSystem": "demo_business"}
    if not log or not row or log.user_id != user_id or row.user_id != user_id:
        return {**base, "found": False}
    values = json.loads(row.observations_json)
    if not isinstance(values, dict):
        values = {}
    return {**base, "found": True, "serviceId": row.service_id, "ruleVersion": row.rule_version,
            "appId": log.app_id, "endpoint": log.endpoint, "calledAt": timestamp(log.created_at),
            "observations": {k: v for k, v in values.items() if k in SAFE_OBSERVATIONS}}


async def query_call_log(db: AsyncSession, user_id: str, request_id: str) -> dict:
    row = await db.get(SupportApiCallLog, request_id)
    if not row or row.user_id != user_id:
        return {"found": False, "requestId": request_id, "queriedAt": timestamp(utcnow()), "ownerUserId": user_id}
    key_masked = None
    if row.api_key_id:
        key = await db.get(SupportApiKey, row.api_key_id)
        if key and key.user_id == user_id:
            key_masked = key.key_masked
    return {"found": True, "requestId": row.request_id, "appId": row.app_id, "endpoint": row.endpoint, "httpStatus": row.http_status, "errorCode": row.error_code, "latencyMs": row.latency_ms, "apiKeyMasked": key_masked, "calledAt": timestamp(row.created_at), "queriedAt": timestamp(utcnow()), "ownerUserId": user_id, "sourceSystem": "demo_business"}


async def query_api_key_status(db: AsyncSession, user_id: str, *, app_id: str | None = None, api_key_id: str | None = None) -> dict:
    stmt = select(SupportApiKey).where(SupportApiKey.user_id == user_id)
    if api_key_id:
        stmt = stmt.where(SupportApiKey.id == api_key_id)
    elif app_id:
        stmt = stmt.where(SupportApiKey.app_id == app_id)
    else:
        raise ValueError("app_id or api_key_id is required")
    rows = list((await db.scalars(stmt)).all())
    if not rows:
        return {"found": False, "queriedAt": timestamp(utcnow()), "ownerUserId": user_id, "reason": "API Key not found for current customer"}
    now = utcnow()
    return {"found": True, "ownerUserId": user_id, "queriedAt": timestamp(now), "sourceSystem": "demo_business", "keys": [{"apiKeyId": r.id, "appId": r.app_id, "apiKeyMasked": r.key_masked, "status": r.status, "expireAt": r.expire_at.isoformat() if r.expire_at else None, "expired": bool(r.expire_at and r.expire_at < now)} for r in rows]}


def parse_time(value):
    from datetime import datetime, timezone
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def timestamp(value):
    return value.isoformat() + "Z" if value else None


async def query_recent_call_stats(
    db: AsyncSession, user_id: str, *, endpoint: str | None = None,
    app_id: str | None = None, minutes: int = 60, window: str = "current",
    request_id: str | None = None, start_at: str | None = None, end_at: str | None = None,
) -> dict:
    minutes = max(1, min(1440, int(minutes)))
    now = utcnow()
    base = [SupportApiCallLog.user_id == user_id]
    if window == "incident":
        if not request_id:
            raise ValueError("incident window requires request_id")
        log = await db.get(SupportApiCallLog, request_id)
        if not log or log.user_id != user_id:
            return {"found": False, "requestId": request_id, "windowType": window,
                    "queriedAt": timestamp(now), "ownerUserId": user_id}
        if (app_id and app_id != log.app_id) or (endpoint and endpoint != log.endpoint):
            raise ValueError("incident scope does not match the request")
        app_id, endpoint, end = log.app_id, log.endpoint, log.created_at
        start = end - timedelta(minutes=minutes)
        if start_at or end_at:
            raise ValueError("incident window cannot also specify timestamps")
    elif window == "explicit":
        if not start_at or not end_at or request_id:
            raise ValueError("explicit window requires start_at and end_at only")
        start, end = parse_time(start_at), parse_time(end_at)
        if end <= start or end - start > timedelta(days=1) or end > now:
            raise ValueError("invalid explicit window; maximum 24 hours, no future end")
    elif window == "current":
        if request_id or start_at or end_at:
            raise ValueError("current window does not accept historical anchors")
        end, start = now, now - timedelta(minutes=minutes)
    else:
        raise ValueError("unknown statistics window")
    if app_id:
        base.append(SupportApiCallLog.app_id == app_id)
    if endpoint:
        base.append(SupportApiCallLog.endpoint == endpoint)
    rows = (await db.execute(select(SupportApiCallLog.http_status, func.count()).where(
        *base, SupportApiCallLog.created_at >= start, SupportApiCallLog.created_at <= end,
    ).group_by(SupportApiCallLog.http_status))).all()
    by = {int(status): int(count) for status, count in rows}
    total, n429 = sum(by.values()), by.get(429, 0)
    return {"found": True, "ownerUserId": user_id, "sourceSystem": "demo_business",
            "appId": app_id, "endpoint": endpoint, "windowType": window,
            "windowMinutes": (end-start).total_seconds()/60, "windowStart": timestamp(start),
            "windowEnd": timestamp(end), "queriedAt": timestamp(now),
            "requestId": request_id, "scope": "application" if app_id else "customer",
            "total": total, "byStatus": by, "rateLimitedCount": n429,
            "rateLimitedRatio": round(n429/total, 4) if total else 0.0}


async def query_error_code(db: AsyncSession, code: str) -> dict:
    row = await db.get(SupportErrorCode, code.upper())
    if not row:
        return {"found": False, "code": code}
    return {"found": True, "code": row.code, "name": row.name, "httpStatus": row.http_status, "cause": row.cause, "fixSteps": row.fix_steps}
