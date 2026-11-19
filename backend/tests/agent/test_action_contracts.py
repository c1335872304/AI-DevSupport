import pytest

from app.agent.action_contracts import bind_request_scope, handoff_receipt, render_action_answer
from app.agent.evidence import evidence_joiner
from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.db.models import User
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry, tool_registry


async def execute(call, data):
    events = []

    async def send(event):
        events.append(event)

    async def transport(_tool, _context, _arguments):
        return ToolResult(status="SUCCESS", data=data)

    registry = ToolRegistry([tool_registry.get(call.name)], transport=transport)
    result, = await AgentRuntime(registry)._execute_parallel(
        calls=[call], user=User(id="customer", role="USER"), generation_id="current",
        send_json=send, step=0, active_skills=frozenset({call.source_skill}),
    )
    return result, events


@pytest.mark.asyncio
async def test_only_rows_for_the_bound_period_become_evidence():
    proposed = AgentToolCall("read", "query_bill", {"month": "2026-06"}, "billing", "billing")
    call = bind_request_scope(proposed, "2026-11")
    november = {"month": "2026-11", "amount": 12}
    june = {"month": "2026-06", "amount": 99}

    result, events = await execute(call, {"found": True, "bills": [june, november]})
    verified = evidence_joiner.build_agent_evidence([(call, result)])[0].verified_facts
    assert events[0]["arguments"]["month"] == "2026-11"
    assert verified[0]["bills"] == [november]

    result, _ = await execute(call, {"found": True, "bills": [june]})
    assert result.status == "ERROR"
    assert not evidence_joiner.build_agent_evidence([(call, result)])[0].verified_facts


@pytest.mark.parametrize(("data", "expected_status"), [
    ({"handoffId": "ticket", "generationId": "current", "userId": "customer"}, "SUCCESS"),
    ({"found": True, "handoff": {"handoffId": "old"}}, "ERROR"),
    ({"handoffId": "old", "generationId": "previous"}, "ERROR"),
    ({"handoffId": "other", "userId": "other"}, "DENIED"),
])
@pytest.mark.asyncio
async def test_only_a_valid_creation_receipt_is_successful(data, expected_status):
    call = AgentToolCall(
        "write", "create_support_handoff",
        {"reason": "用户要求转人工", "summary": "用户要求人工支持继续处理当前请求"},
        "handoff_decision", "escalation",
    )
    result, events = await execute(call, data)
    receipt = handoff_receipt(result)
    completed = next(event for event in events if event.get("resultStatus"))
    assert result.status == completed["resultStatus"] == expected_status
    assert receipt.success is (expected_status == "SUCCESS")
    assert receipt.handoff_id == ("ticket" if receipt.success else None)


def test_scoped_answer_preserves_verified_partial_results():
    answer = render_action_answer(
        specialists=("billing",), handoff={}, billing_month="2026-11",
        attempted_tools={"mcp__billing__get_usage", "mcp__billing__get_invoice", "mcp__billing__get_plan"},
        evidence={"verifiedFacts": [{"tool": "query_usage", "found": True, "usage": [
            {"month": "2026-11", "callCount": 120}, {"month": "2026-06", "callCount": 999},
        ]}]},
    )
    assert "120 次" in answer
    assert "999" not in answer
    assert "无法核实所查询账期的账单金额" in answer
    assert "无法核实套餐信息" in answer
