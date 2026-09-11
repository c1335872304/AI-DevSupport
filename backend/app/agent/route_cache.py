from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.agent.entities import normalize_entities

logger = logging.getLogger(__name__)
ROUTE_CACHE_TTL_SECONDS = 60 * 60 * 24


class RouteCache:
    def __init__(self) -> None:
        self._client = None

    async def _redis(self):
        if not get_settings().redis_enabled:
            return None
        if self._client is None:
            from redis.asyncio import from_url

            self._client = from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    @staticmethod
    def _key(question: str) -> str:
        normalized = " ".join((question or "").strip().lower().split())
        return "routecache:" + hashlib.md5(normalized.encode("utf-8")).hexdigest()

    async def get(self, question: str) -> dict | None:
        client = await self._redis()
        if client is None:
            return None
        try:
            raw = await client.get(self._key(question))
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("[ROUTER] route cache read skipped: %s", exc)
            return None

    async def put(self, question: str, result: dict[str, Any]) -> None:
        client = await self._redis()
        if client is None or not result:
            return
        try:
            payload = {
                "intent": result.get("intent"),
                "skills": result.get("skills") or [],
                "needs_human": bool(result.get("needs_human")),
                "confidence": result.get("confidence", 0),
                "is_follow_up": False,
                "entities": normalize_entities(result.get("entities")),
            }
            await client.set(self._key(question), json.dumps(payload, ensure_ascii=False), ex=max(60, get_settings().route_cache_ttl_seconds))
        except Exception as exc:
            logger.warning("[ROUTER] route cache write skipped: %s", exc)


route_cache = RouteCache()
