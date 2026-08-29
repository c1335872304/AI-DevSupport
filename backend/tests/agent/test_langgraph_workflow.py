from __future__ import annotations

import pytest

from app.agent.graph.engine import LANGGRAPH_ENGINE
from app.agent.llm import llm_service
from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.db.models import User
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry


class _ReadTool(BaseTool):
    name = "search_knowledge"
    description = "test read tool"
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        return {"results": [], "query": arguments["query"]}


class _HandoffTool(BaseTool):
    name = "create_support_handoff"
    description = "test human handoff"
    read_only = False
    parallel_safe = False
    resource_group = "support-handoff"
    input_schema = {
        "type": "object",
        "properties": {"reason": {"type": "string"}},
        "required": ["reason"],
        "additionalProperties": False,
    }

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        return {"handoffId": "H-001", "status": "OPEN"}


def _user() -> User:
    return User(id=91, username="graph-user", password="x", role="USER")


async def _append(target: list, value):
    target.append(value)


@pytest.mark.asyncio
async def test_langgraph_main_path_is_real_runtime_path(monkeypatch):
    runtime = AgentRuntime(ToolRegistry([_ReadTool()]))

    async def fake_turn(messages, tools):
        yield {"type": "content", "content": "您好，请问有什么可以帮您？"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    events: list[dict] = []
    chunks: list[str] = []
    content, _ = await runtime.run(
        user=_user(),
        question="你好",
        history=[],
        generation_id="graph-basic",
        send_json=lambda payload: _append(events, payload),
        on_chunk=lambda chunk: _append(chunks, chunk),
    )

    assert content == "您好，请问有什么可以帮您？"
    nodes = [event["node"] for event in events if event.get("type") == "workflow_node"]
    assert nodes == ["load_context", "skill_route", "agent_decide", "safety", "emit_final", "persist_trace"]
    trace = next(event["trace"] for event in events if event.get("type") == "skill_trace")
    assert trace["workflowEngine"] == LANGGRAPH_ENGINE
    assert trace["graphPath"] == nodes


@pytest.mark.asyncio
async def test_langgraph_tool_node_loops_back_to_agent(monkeypatch):
    runtime = AgentRuntime(ToolRegistry([_ReadTool()]))
    turn = 0

    async def fake_turn(messages, tools):
        nonlocal turn
        turn += 1
        if turn == 1:
            yield {
                "type": "tool_calls",
                "tool_calls": [AgentToolCall("kb-1", "search_knowledge", {"query": "退款政策"})],
            }
        else:
            assert any(item.get("role") == "tool" for item in messages)
            yield {"type": "content", "content": "根据当前政策，可以按规则申请退款。"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    events: list[dict] = []
    content, _ = await runtime.run(
        user=_user(),
        question="退款政策是什么？",
        history=[],
        generation_id="graph-tools",
        send_json=lambda payload: _append(events, payload),
        on_chunk=lambda chunk: _append([], chunk),
    )
    assert content.startswith("根据当前政策")
    nodes = [event["node"] for event in events if event.get("type") == "workflow_node"]
    assert nodes[:5] == ["load_context", "skill_route", "agent_decide", "execute_tools", "agent_decide"]
    assert nodes[-3:] == ["safety", "emit_final", "persist_trace"]


@pytest.mark.asyncio
async def test_langgraph_handoff_is_first_class_node(monkeypatch):
    runtime = AgentRuntime(ToolRegistry([_HandoffTool()]))
    turn = 0

    async def fake_turn(messages, tools):
        nonlocal turn
        turn += 1
        if turn == 1:
            visible = {item["function"]["name"] for item in tools}
            assert "create_support_handoff" in visible
            yield {
                "type": "tool_calls",
                "tool_calls": [AgentToolCall("handoff-1", "create_support_handoff", {"reason": "用户要求人工"})],
            }
        else:
            yield {"type": "content", "content": "已创建人工工单 H-001。"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    events: list[dict] = []
    content, _ = await runtime.run(
        user=_user(),
        question="别排查了，直接转人工",
        history=[],
        generation_id="graph-handoff",
        send_json=lambda payload: _append(events, payload),
        on_chunk=lambda chunk: _append([], chunk),
    )
    assert "H-001" in content
    nodes = [event["node"] for event in events if event.get("type") == "workflow_node"]
    assert "handoff" in nodes
    trace = next(event["trace"] for event in events if event.get("type") == "skill_trace")
    assert trace["handoffSuccess"] is True
    assert trace["handoffId"] == "H-001"


@pytest.mark.asyncio
async def test_safety_node_blocks_fake_handoff_success(monkeypatch):
    runtime = AgentRuntime(ToolRegistry([_ReadTool()]))

    async def fake_turn(messages, tools):
        yield {"type": "content", "content": "已成功创建人工工单，请等待处理。"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    content, _ = await runtime.run(
        user=_user(),
        question="帮我看看退款政策",
        history=[],
        generation_id="graph-safety",
        send_json=lambda payload: _append([], payload),
        on_chunk=lambda chunk: _append([], chunk),
    )
    assert "人工工单尚未确认创建成功" in content
