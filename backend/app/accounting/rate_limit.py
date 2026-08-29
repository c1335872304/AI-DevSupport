from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import RateLimitPolicy


class RateLimitService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis = None

    async def _policy(self, db: AsyncSession, scope: str) -> tuple[int, int, bool]:
        row = await db.get(RateLimitPolicy, scope)
        if row:
            return int(row.max_requests), int(row.window_seconds), bool(row.enabled)
        if scope == "register":
            return self.settings.rate_limit_register_max, self.settings.rate_limit_register_window_seconds, True
        if scope == "login":
            return self.settings.rate_limit_login_max, self.settings.rate_limit_login_window_seconds, True
        return 60, 60, True

    async def check(self, db: AsyncSession, scope: str, key: str) -> None:
        maximum, window, enabled = await self._policy(db, scope)
        if not enabled:
            return
        identity = f"paismart:rl:{scope}:{key}"
        if self.settings.redis_enabled:
            try:
                if self._redis is None:
                    from redis.asyncio import from_url
                    self._redis = from_url(self.settings.redis_url, decode_responses=True)
                count = await self._redis.incr(identity)
                if count == 1:
                    await self._redis.expire(identity, window)
                if int(count) > maximum:
                    ttl = await self._redis.ttl(identity)
                    raise HTTPException(status_code=429, detail=f"Rate limit exceeded; retry in {max(1, int(ttl))}s")
                return
            except HTTPException:
                raise
            except Exception:
                # Redis outage must not disable authentication; fall back to local limits.
                pass

        now = time.monotonic()
        async with self._lock:
            q = self._events[identity]
            cutoff = now - window
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= maximum:
                retry = max(1, int(window - (now - q[0])))
                raise HTTPException(status_code=429, detail=f"Rate limit exceeded; retry in {retry}s")
            q.append(now)

    async def get_policies(self, db: AsyncSession) -> dict:
        output = {}
        for scope in ("register", "login"):
            maximum, window, enabled = await self._policy(db, scope)
            output[scope] = {"max": maximum, "windowSeconds": window, "enabled": enabled}
        return output

    async def set_policies(self, db: AsyncSession, payload: dict) -> dict:
        for scope in ("register", "login"):
            raw = payload.get(scope)
            if not isinstance(raw, dict):
                continue
            maximum = int(raw.get("max", 0))
            window = int(raw.get("windowSeconds", 0))
            if maximum < 1 or window < 1:
                raise HTTPException(status_code=422, detail=f"Invalid rate-limit policy: {scope}")
            row = await db.get(RateLimitPolicy, scope)
            if not row:
                row = RateLimitPolicy(scope=scope, max_requests=maximum, window_seconds=window, enabled=bool(raw.get("enabled", True)))
                db.add(row)
            else:
                row.max_requests = maximum
                row.window_seconds = window
                row.enabled = bool(raw.get("enabled", True))
        await db.commit()
        return await self.get_policies(db)


rate_limit_service = RateLimitService()
