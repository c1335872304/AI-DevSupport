from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent.query_optimizer import QueryOptimizer


class _FakeLLM:
    def __init__(self, value: str = "围绕 req_demo_401 的 401 鉴权失败原因与处理方式") -> None:
        self.value = value
        self.calls = 0

    async def rewrite_retrieval_query(self, **_kwargs) -> str:
        self.calls += 1
        return self.value


def _settings(**overrides):
    return SimpleNamespace(
        rag_query_rewrite_enabled=True,
        rag_query_rewrite_cache_seconds=300,
        **overrides,
    )


@pytest.mark.asyncio
async def test_query_optimizer_does_not_call_model_for_non_follow_up_or_missing_entities():
    llm = _FakeLLM()
    optimizer = QueryOptimizer(llm=llm, settings=_settings())

    result = await optimizer.optimize(
        user_id="11",
        conversation_id="conv-1",
        question="退款政策是什么？",
        history=[{"role": "user", "content": "之前的问题"}],
        entity_memory={},
        is_follow_up=False,
    )

    assert result.query == "退款政策是什么？"
    assert result.mode == "raw"
    assert not result.applied
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_query_optimizer_rewrites_once_and_caches_per_conversation_and_entity_state():
    llm = _FakeLLM()
    optimizer = QueryOptimizer(llm=llm, settings=_settings())
    kwargs = {
        "user_id": "11",
        "conversation_id": "conv-1",
        "question": "那为什么会这样？",
        "history": [{"role": "user", "content": "请求 req_demo_401 返回 401，帮我定位。"}],
        "entity_memory": {"request_id": "req_demo_401"},
        "is_follow_up": True,
    }

    first = await optimizer.optimize(**kwargs)
    second = await optimizer.optimize(**kwargs)

    assert first.mode == "llm_rewrite"
    assert first.applied and not first.cache_hit
    assert "原始问题：那为什么会这样？" in first.query
    assert "req_demo_401" in first.query
    assert second.cache_hit
    assert second.query == first.query
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_query_optimizer_falls_back_to_local_context_without_retrying():
    llm = _FakeLLM("")
    optimizer = QueryOptimizer(llm=llm, settings=_settings())

    result = await optimizer.optimize(
        user_id="11",
        conversation_id="conv-1",
        question="上面那个怎么办？",
        history=[{"role": "user", "content": "接口 /v1/chat 使用 key_demo 返回 401。"}],
        entity_memory={"endpoint": "/v1/chat", "api_key_id": "key_demo"},
        is_follow_up=True,
    )

    assert result.mode == "contextual_fallback"
    assert "当前追问：上面那个怎么办？" in result.query
    assert "api_key_id=key_demo" in result.query
    assert llm.calls == 1
