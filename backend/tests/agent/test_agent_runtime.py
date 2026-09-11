from __future__ import annotations

import asyncio

import pytest

from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.db.models import User
from app.agent.llm import llm_service
from app.agent.trace_store import trace_store
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry


class _ParallelProbeTool(BaseTool):
    description = "test"
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, name: str, tracker: dict):
        self.name = name
        self.tracker = tracker

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        self.tracker["active"] += 1
        self.tracker["max_active"] = max(self.tracker["max_active"], self.tracker["active"])
        self.tracker["started"].add(self.name)
        if len(self.tracker["started"]) == 2:
            self.tracker["gate"].set()
        await asyncio.wait_for(self.tracker["gate"].wait(), timeout=0.4)
        await asyncio.sleep(0.01)
        self.tracker["active"] -= 1
        return {"tool": self.name}


class _FailingTool(BaseTool):
    name = "bad"
    description = "test failure isolation"
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_agent_runtime_executes_same_turn_tools_in_parallel(monkeypatch):
    tracker = {"active": 0, "max_active": 0, "started": set(), "gate": asyncio.Event()}
    registry = ToolRegistry([_ParallelProbeTool("tool_a", tracker), _ParallelProbeTool("tool_b", tracker)])
    runtime = AgentRuntime(registry)
    async def no_trace(*_args, **_kwargs):
        return None

    monkeypatch.setattr(trace_store, "tool", no_trace)
    events = []
    user = User(id=1, username="tester", password="x", role="USER")

    results = await runtime._execute_parallel(
        calls=[AgentToolCall("a", "tool_a", {}), AgentToolCall("b", "tool_b", {})],
        user=user,
        generation_id="g1",
        send_json=lambda payload: _append(events, payload),
        step=0,
        active_skills=frozenset(),
    )

    assert [result.status for result in results] == ["SUCCESS", "SUCCESS"]
    assert tracker["max_active"] == 2
    assert [event["status"] for event in events if event.get("type") == "tool_call"].count("executing") == 2
    assert [event["status"] for event in events if event.get("type") == "tool_call"].count("success") == 2


@pytest.mark.asyncio
async def test_parallel_batch_keeps_partial_failure(monkeypatch):
    tracker = {"active": 0, "max_active": 0, "started": set(), "gate": asyncio.Event()}
    good = _ParallelProbeTool("good", tracker)

    async def good_execute(context, arguments):
        return {"ok": True}

    good.execute = good_execute  # type: ignore[method-assign]
    registry = ToolRegistry([good, _FailingTool()])
    runtime = AgentRuntime(registry)
    async def no_trace(*_args, **_kwargs):
        return None

    monkeypatch.setattr(trace_store, "tool", no_trace)
    events = []
    user = User(id=1, username="tester", password="x", role="USER")
    results = await runtime._execute_parallel(
        calls=[AgentToolCall("good-1", "good", {}), AgentToolCall("bad-1", "bad", {})],
        user=user,
        generation_id="g2",
        send_json=lambda payload: _append(events, payload),
        step=0,
        active_skills=frozenset(),
    )
    assert [result.status for result in results] == ["SUCCESS", "ERROR"]
    final = {event["tool"]: event for event in events if event.get("type") == "tool_call" and event.get("status") in {"success", "failed"}}
    assert final["good"]["status"] == "success"
    assert final["bad"]["status"] == "failed"
    assert final["bad"]["resultStatus"] == "ERROR"


def test_registry_exposes_llm_tool_schemas():
    from app.tools.registry import tool_registry

    names = {item["function"]["name"] for item in tool_registry.llm_tools()}
    assert {"search_knowledge", "list_documents", "get_document"} <= names
    search = next(item for item in tool_registry.llm_tools() if item["function"]["name"] == "search_knowledge")
    assert "query" in search["function"]["parameters"]["required"]


async def _append(target: list, value):
    target.append(value)


async def _noop():
    return None
