from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.agent.runtime import AgentRuntime
from app.agent.target_agents import target_specialist_agents
from app.agent.types import AgentPlan, AgentToolCall
from app.core.security import create_access_token, decode_token
from app.db.models import User
from app.accounting.embedding_usage import capture_embedding_usage, record_embedding_usage
from app.agent.generation import GenerationRuntime
from app.agent.llm import llm_service
from app.accounting.llm_usage import capture_llm_usage, record_provider_usage
from app.accounting.rate_limit import RateLimitService
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry
from app.tools.validation import ToolValidationError, validate_json_schema
from app.skill_runtime.registry import skill_registry
from app.tools.registry import tool_registry


class _EchoTool(BaseTool):
    name = "echo"
    description = "echo"
    required_scopes = frozenset({"tools:read"})
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 8},
            "count": {"type": "integer", "minimum": 1, "maximum": 3},
        },
        "required": ["text"],
        "additionalProperties": False,
    }

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        return arguments


def _user() -> User:
    return User(id=7, username="runtime-user", password="x", role="USER")


def test_runtime_json_schema_rejects_extra_fields_and_ranges():
    schema = _EchoTool.input_schema
    with pytest.raises(ToolValidationError, match="Additional properties|unsupported fields"):
        validate_json_schema({"text": "ok", "extra": True}, schema)
    with pytest.raises(ToolValidationError, match="maximum of 3|<= 3"):
        validate_json_schema({"text": "ok", "count": 9}, schema)
    with pytest.raises(ToolValidationError, match="required|required property"):
        validate_json_schema({}, schema)


@pytest.mark.asyncio
async def test_tool_registry_enforces_schema_and_scopes():
    registry = ToolRegistry([_EchoTool()])
    denied = await registry.execute(
        "echo",
        {"text": "hello"},
        ToolExecutionContext(user=_user(), scopes=frozenset(), source="mcp"),
    )
    assert denied.status == "DENIED"

    invalid = await registry.execute(
        "echo",
        {"text": "too-long-value"},
        ToolExecutionContext(user=_user(), scopes=frozenset({"tools:read"}), source="mcp"),
    )
    assert invalid.status == "INVALID_ARGUMENT"

    allowed = await registry.execute(
        "echo",
        {"text": "hello", "count": 2},
        ToolExecutionContext(user=_user(), scopes=frozenset({"tools:read"}), source="mcp"),
    )
    assert allowed.status == "SUCCESS"
    assert allowed.data["count"] == 2


@pytest.mark.asyncio
async def test_agent_buffers_tool_preamble_instead_of_streaming_it(monkeypatch):
    async def fake_turn(messages, tools):
        # Specialist planners may receive provider preamble text, but only Tool
        # calls are allowed into the shared scheduler.
        yield {"type": "content", "content": "I will inspect this..."}
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("c1", "search_knowledge", {"query": "ok"})]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    work = await target_specialist_agents.plan_work(
        plans=[AgentPlan("knowledge", "knowledge", ("search_knowledge",), "find verified documentation")],
        question="plain test question",
        entities={},
        registry=skill_registry,
        tool_registry=tool_registry,
    )

    assert len(work) == 1
    assert [call.name for call in work[0].proposed_calls] == ["search_knowledge"]


@pytest.mark.asyncio
async def test_generation_runtime_disconnect_does_not_cancel_task():
    runtime = GenerationRuntime()
    started = asyncio.Event()
    release = asyncio.Event()

    async def work():
        started.set()
        await release.wait()
        await runtime.publish("g-detached", {"type": "completion"})

    queue = runtime.subscribe("g-detached")
    task = await runtime.start("g-detached", work)
    await asyncio.wait_for(started.wait(), timeout=0.5)
    runtime.unsubscribe("g-detached", queue)  # simulates WebSocket disconnect
    await asyncio.sleep(0)
    assert runtime.is_running("g-detached")
    assert not task.cancelled()
    release.set()
    await asyncio.wait_for(task, timeout=0.5)


@pytest.mark.asyncio
async def test_generation_runtime_subscriber_receives_live_events():
    runtime = GenerationRuntime()
    queue = runtime.subscribe("g-live")
    await runtime.publish("g-live", {"type": "chunk", "chunk": "hello"})
    assert await asyncio.wait_for(queue.get(), timeout=0.2) == {"type": "chunk", "chunk": "hello"}


def test_token_version_is_bound_into_jwt():
    token = create_access_token("alice", 3, "USER", token_version=9)
    claims = decode_token(token, "access")
    assert claims["ver"] == 9


def test_provider_usage_meter_prefers_reported_usage():
    with capture_llm_usage() as meter:
        record_provider_usage({"prompt_tokens": 120, "completion_tokens": 35})
        record_provider_usage({"input_tokens": 10, "output_tokens": 5})
    assert meter.prompt_tokens == 130
    assert meter.completion_tokens == 40
    assert meter.total_tokens == 170


def test_embedding_usage_meter_accumulates_provider_usage():
    with capture_embedding_usage() as meter:
        record_embedding_usage({"total_tokens": 100})
        record_embedding_usage({"prompt_tokens": 23})
    assert meter.total_tokens == 123


@pytest.mark.asyncio
async def test_rate_limit_fallback_blocks_after_limit(monkeypatch):
    service = RateLimitService()
    service.settings.redis_enabled = False

    async def policy(db, scope):
        return 2, 60, True

    monkeypatch.setattr(service, "_policy", policy)
    await service.check(object(), "login", "same-client")  # type: ignore[arg-type]
    await service.check(object(), "login", "same-client")  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as caught:
        await service.check(object(), "login", "same-client")  # type: ignore[arg-type]
    assert caught.value.status_code == 429
