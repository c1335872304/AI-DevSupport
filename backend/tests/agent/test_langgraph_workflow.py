from __future__ import annotations

import pytest

from app.agent.llm import llm_service
from app.agent.runtime import AgentRuntime
from app.db.models import User
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry


class _HandoffTool(BaseTool):
    name = "create_support_handoff"
    description = "test human handoff"
    read_only = False
    parallel_safe = False
    resource_group = "support-handoff"
    input_schema = {
        "type": "object",
        "properties": {"reason": {"type": "string"}, "summary": {"type": "string"}, "category": {"type": "string"}, "priority": {"type": "string"}},
        "required": ["reason", "summary"],
        "additionalProperties": False,
    }

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        return {"handoffId": "H-001", "status": "OPEN"}


def _user() -> User:
    return User(id=91, username="graph-user", password="x", role="USER")


async def _append(target: list, value):
    target.append(value)


@pytest.mark.asyncio
async def test_target_graph_moves_handoff_after_evidence_summary(monkeypatch):
    runtime = AgentRuntime(ToolRegistry([_HandoffTool()]))

    async def fake_final(messages, force_no_tools=False):
        yield "已根据已核验信息处理。"

    monkeypatch.setattr(llm_service, "stream_messages", fake_final)
    events: list[dict] = []
    await runtime.run(
        user=_user(),
        question="不要排查，直接转人工",
        history=[],
        generation_id="graph-target-handoff",
        send_json=lambda payload: _append(events, payload),
        on_chunk=lambda chunk: _append([], chunk),
    )
    nodes = [event["node"] for event in events if event.get("type") == "workflow_node"]
    assert nodes.index("target_evidence_join") < nodes.index("target_handoff_decision") < nodes.index("target_create_handoff")
    trace = next(event["trace"] for event in events if event.get("type") == "skill_trace")
    assert trace["handoffSuccess"] is True
    assert trace["handoffResult"]["handoffId"] == "H-001"
