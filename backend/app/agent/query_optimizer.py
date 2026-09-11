from __future__ import annotations

"""Bounded retrieval-query refinement for entity-backed follow-up questions."""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from app.agent.entities import looks_like_follow_up, normalize_entities
from app.agent.llm import llm_service
from app.core.config import get_settings


_REFERENCE_MARKERS = ("这个", "那个", "它", "刚才", "上面", "前面", "那", "所以", "继续", "呢", "怎么办")


@dataclass(frozen=True, slots=True)
class QueryOptimization:
    """A serializable decision; the raw customer question is never replaced."""

    query: str
    applied: bool
    mode: str
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        # Do not include query text in traces: it can contain customer data.
        return {"applied": self.applied, "mode": self.mode, "cacheHit": self.cache_hit}


class QueryOptimizer:
    """Use a deterministic expansion first and at most one model rewrite.

    Cache keys include user, conversation and normalized entity state.  This
    keeps one user's context from ever changing another user's retrieval query.
    """

    def __init__(
        self,
        *,
        llm: Any = None,
        settings: Any = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.llm = llm or llm_service
        self.settings = settings or get_settings()
        self.clock = clock
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()

    @staticmethod
    def _last_user_question(history: list[dict]) -> str:
        for item in reversed(history):
            if item.get("role") != "user":
                continue
            value = " ".join(str(item.get("content") or "").split())
            if value:
                return value[:600]
        return ""

    @staticmethod
    def _is_referential(question: str) -> bool:
        text = str(question or "").strip()
        return any(marker in text for marker in _REFERENCE_MARKERS)

    @staticmethod
    def _contextual_query(question: str, previous_question: str, entities: dict[str, str]) -> str:
        entity_text = "；".join(f"{key}={value}" for key, value in entities.items())
        parts = [f"当前追问：{question.strip()}"]
        if previous_question:
            parts.append(f"上一轮用户问题：{previous_question}")
        if entity_text:
            parts.append(f"已解析实体：{entity_text}")
        return "\n".join(parts)[:1800]

    def _cache_key(
        self,
        *,
        user_id: str,
        conversation_id: str,
        question: str,
        previous_question: str,
        entities: dict[str, str],
    ) -> str:
        value = json.dumps(
            {
                "user": user_id,
                "conversation": conversation_id,
                "question": question,
                "previous": previous_question,
                "entities": entities,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> str:
        item = self._cache.get(key)
        if not item:
            return ""
        expires_at, value = item
        if expires_at <= self.clock():
            self._cache.pop(key, None)
            return ""
        self._cache.move_to_end(key)
        return value

    def _put_cached(self, key: str, value: str) -> None:
        ttl = max(1, int(getattr(self.settings, "rag_query_rewrite_cache_seconds", 300)))
        self._cache[key] = (self.clock() + ttl, value)
        self._cache.move_to_end(key)
        while len(self._cache) > 256:
            self._cache.popitem(last=False)

    async def optimize(
        self,
        *,
        user_id: str,
        conversation_id: str,
        question: str,
        history: list[dict] | None,
        entity_memory: dict[str, str] | None,
        is_follow_up: bool,
    ) -> QueryOptimization:
        raw = " ".join(str(question or "").split())[:1200]
        rows = list(history or [])
        entities = normalize_entities(entity_memory)
        follows_context = bool(is_follow_up) or (
            bool(rows) and self._is_referential(raw) and looks_like_follow_up(raw, rows)
        )
        if not raw or not getattr(self.settings, "rag_query_rewrite_enabled", True) or not follows_context or not entities:
            return QueryOptimization(query=raw, applied=False, mode="raw")

        previous = self._last_user_question(rows)
        if not previous:
            return QueryOptimization(query=raw, applied=False, mode="raw")
        contextual = self._contextual_query(raw, previous, entities)

        # A full, explicit follow-up benefits from local context but does not
        # need another model call. Short/pointing questions get exactly one.
        needs_model = len(raw) <= 80 or self._is_referential(raw)
        if not needs_model:
            return QueryOptimization(query=contextual, applied=True, mode="contextual")

        key = self._cache_key(
            user_id=user_id,
            conversation_id=conversation_id,
            question=raw,
            previous_question=previous,
            entities=entities,
        )
        rewritten = self._get_cached(key)
        if rewritten:
            return QueryOptimization(query=rewritten, applied=True, mode="llm_rewrite", cache_hit=True)

        candidate = await self.llm.rewrite_retrieval_query(
            question=raw,
            contextual_query=contextual,
            entity_memory=entities,
        )
        candidate = " ".join(str(candidate or "").split())[:420]
        if not candidate:
            return QueryOptimization(query=contextual, applied=True, mode="contextual_fallback")

        # Preserve literal terms from the actual customer question alongside the
        # model's disambiguation, which is more robust for error codes and IDs.
        combined = f"原始问题：{raw}\n检索改写：{candidate}"[:1800]
        self._put_cached(key, combined)
        return QueryOptimization(query=combined, applied=True, mode="llm_rewrite")


query_optimizer = QueryOptimizer()
