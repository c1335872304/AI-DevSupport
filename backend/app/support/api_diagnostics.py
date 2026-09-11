from __future__ import annotations

from datetime import timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SupportApiCallLog, SupportApiKey, SupportErrorCode
from app.core.time import utcnow


async def query_call_log(db: AsyncSession, user_id: str, request_id: str) -> dict:
    row = await db.get(SupportApiCallLog, request_id)
    if not row or row.user_id != user_id:
        return {"found": False, "requestId": request_id}
    key_masked = None
    if row.api_key_id:
        key = await db.get(SupportApiKey, row.api_key_id)
        if key and key.user_id == user_id:
            key_masked = key.key_masked
    return {"found": True, "requestId": row.request_id, "appId": row.app_id, "endpoint": row.endpoint, "httpStatus": row.http_status, "errorCode": row.error_code, "latencyMs": row.latency_ms, "apiKeyMasked": key_masked, "calledAt": row.created_at.isoformat()}


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
        return {"found": False, "reason": "API Key not found for current customer"}
    now = utcnow()
    return {"found": True, "keys": [{"apiKeyId": r.id, "appId": r.app_id, "apiKeyMasked": r.key_masked, "status": r.status, "expireAt": r.expire_at.isoformat() if r.expire_at else None, "expired": bool(r.expire_at and r.expire_at < now)} for r in rows]}


async def query_recent_call_stats(db: AsyncSession, user_id: str, *, endpoint: str | None = None, minutes: int = 60) -> dict:
    minutes=max(1,min(1440,int(minutes)))
    base=[SupportApiCallLog.user_id == user_id]
    if endpoint:
        base.append(SupportApiCallLog.endpoint == endpoint)
    anchor=(await db.execute(select(func.max(SupportApiCallLog.created_at)).where(*base, SupportApiCallLog.http_status == 429))).scalar()
    if anchor is None:
        anchor=(await db.execute(select(func.max(SupportApiCallLog.created_at)).where(*base))).scalar()
    if anchor is None:
        return {"endpoint": endpoint, "windowMinutes": minutes, "total": 0, "byStatus": {}, "rateLimitedCount": 0, "rateLimitedRatio": 0.0}
    conds=[*base, SupportApiCallLog.created_at >= anchor - timedelta(minutes=minutes)]
    rows=(await db.execute(select(SupportApiCallLog.http_status, func.count()).where(*conds).group_by(SupportApiCallLog.http_status))).all()
    by={int(status): int(count) for status,count in rows}
    total=sum(by.values()); n429=by.get(429,0)
    return {"endpoint": endpoint, "windowMinutes": minutes, "anchorAt": anchor.isoformat(), "total": total, "byStatus": by, "rateLimitedCount": n429, "rateLimitedRatio": round(n429/total,4) if total else 0.0}


async def query_error_code(db: AsyncSession, code: str) -> dict:
    row = await db.get(SupportErrorCode, code.upper())
    if not row:
        return {"found": False, "code": code}
    return {"found": True, "code": row.code, "name": row.name, "httpStatus": row.http_status, "cause": row.cause, "fixSteps": row.fix_steps}
