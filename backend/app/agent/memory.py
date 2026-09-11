from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.agent.entities import normalize_entities

logger = logging.getLogger(__name__)

HISTORY_MAX = 20
ENTITY_TTL_SECONDS = 60 * 60 * 6


class ConversationMemory:
    """Redis-first conversation memory with a clean unavailable fallback.

    SQL history remains the durable source used by the current application. Redis
    provides the legacy sliding window and short-lived entity memory when enabled;
    a Redis outage never prevents a chat request from being served.
    """

    def __init__(self) -> None:
        self._client = None

    def _enabled(self) -> bool:
        return bool(get_settings().redis_enabled)

    async def _redis(self):
        if not self._enabled():
            return None
        if self._client is None:
            from redis.asyncio import from_url

            self._client = from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    @staticmethod
    def _history_key(conversation_id: str) -> str:
        return f"mem:hist:{conversation_id}"

    @staticmethod
    def _entity_key(conversation_id: str) -> str:
        return f"mem:ent:{conversation_id}"

    async def get_history(self, conversation_id: str) -> list[dict] | None:
        client = await self._redis()
        if client is None:
            return None
        try:
            rows = await client.lrange(self._history_key(conversation_id), 0, -1)
            return [json.loads(row) for row in rows]
        except Exception as exc:
            logger.warning("[MEMORY] Redis history unavailable; use database fallback: %s", exc)
            return None

    async def append_message(self, conversation_id: str, role: str, content: str) -> bool:
        client = await self._redis()
        if client is None:
            return False
        try:
            key = self._history_key(conversation_id)
            await client.rpush(key, json.dumps({"role": role, "content": content}, ensure_ascii=False))
            settings = get_settings()
            await client.ltrim(key, -max(1, settings.memory_history_max), -1)
            await client.expire(key, max(60, settings.memory_entity_ttl_seconds))
            return True
        except Exception as exc:
            logger.warning("[MEMORY] Redis history write skipped: %s", exc)
            return False

    async def replace_history(self, conversation_id: str, history: list[dict]) -> bool:
        """Replace the Redis window from durable SQL history.

        SQL is the source of truth.  This method is used when a Redis window is
        stale or incomplete, so a cache restart or partial write cannot silently
        change the context sent to the model.
        """
        client = await self._redis()
        if client is None:
            return False
        try:
            key = self._history_key(conversation_id)
            values = [
                json.dumps(
                    {"role": str(item.get("role") or ""), "content": str(item.get("content") or "")},
                    ensure_ascii=False,
                )
                for item in history
            ]
            settings = get_settings()
            async with client.pipeline(transaction=True) as pipe:
                pipe.delete(key)
                if values:
                    pipe.rpush(key, *values)
                pipe.ltrim(key, -max(1, settings.memory_history_max), -1)
                pipe.expire(key, max(60, settings.memory_entity_ttl_seconds))
                await pipe.execute()
            return True
        except Exception as exc:
            logger.warning("[MEMORY] Redis history reconciliation skipped: %s", exc)
            return False

    async def get_entities(self, conversation_id: str) -> dict[str, str] | None:
        client = await self._redis()
        if client is None:
            return None
        try:
            raw = await client.get(self._entity_key(conversation_id))
            return normalize_entities(json.loads(raw)) if raw else {}
        except Exception as exc:
            logger.warning("[MEMORY] Redis entity memory unavailable; use database fallback: %s", exc)
            return None

    async def update_entities(self, conversation_id: str, new_entities: dict[str, Any]) -> dict[str, str] | None:
        client = await self._redis()
        if client is None:
            return None
        try:
            current = await self.get_entities(conversation_id) or {}
            current.update(normalize_entities(new_entities))
            await client.set(self._entity_key(conversation_id), json.dumps(current, ensure_ascii=False), ex=max(60, get_settings().memory_entity_ttl_seconds))
            return current
        except Exception as exc:
            logger.warning("[MEMORY] Redis entity write skipped: %s", exc)
            return None


conversation_memory = ConversationMemory()
