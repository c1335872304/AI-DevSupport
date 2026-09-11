from __future__ import annotations

from app.agent.shared_scheduler import SharedToolScheduler
from app.agent.target_agents import TargetAgentWork
from app.agent.types import AgentPlan, AgentToolCall


class _Tool:
    def __init__(self, *, read_only: bool = True) -> None:
        self.read_only = read_only


class _Registry:
    def get(self, name: str):
        return _Tool(read_only=name != "create_support_handoff")


def _work(agent: str, tools: tuple[str, ...], calls: list[AgentToolCall]) -> TargetAgentWork:
    return TargetAgentWork(AgentPlan(agent, agent, tools, "test"), tuple(calls))


def test_scheduler_deduplicates_identical_calls_across_specialists():
    first = AgentToolCall("billing-1", "query_bill", {"month": "2026-08"}, source_agent="billing")
    duplicate = AgentToolCall("knowledge-1", "query_bill", {"month": "2026-08"}, source_agent="knowledge")
    work = [
        _work("billing", ("query_bill",), [first]),
        _work("knowledge", ("query_bill",), [duplicate]),
    ]

    schedule = SharedToolScheduler().plan(work, registry=_Registry())

    assert len(schedule.tool_batches) == 1
    scheduled = schedule.tool_batches[0].calls
    assert [item.call.id for item in scheduled] == ["billing-1"]
    assert schedule.rejected_calls == (
        {"id": "knowledge-1", "tool": "query_bill", "reason": "duplicate_call_fingerprint"},
    )


def test_scheduler_stops_additional_calls_at_request_tool_budget():
    calls = [
        AgentToolCall("billing-1", "query_bill", {"month": "2026-07"}, source_agent="billing"),
        AgentToolCall("billing-2", "query_bill", {"month": "2026-08"}, source_agent="billing"),
    ]

    schedule = SharedToolScheduler(max_total_tools=1).plan(
        [_work("billing", ("query_bill",), calls)], registry=_Registry()
    )

    assert [call.call.id for call in schedule.tool_batches[0].calls] == ["billing-1"]
    assert schedule.rejected_calls == (
        {"id": "billing-2", "tool": "query_bill", "reason": "tool_budget_exhausted"},
    )


def test_scheduler_keeps_dependency_calls_deferred_until_real_predecessor_result_exists():
    log = AgentToolCall("api-log", "query_call_log", {"request_id": "req_1"}, source_agent="api_diagnostic")
    code = AgentToolCall("api-code", "query_error_code", {}, source_agent="api_diagnostic")
    work = [_work("api_diagnostic", ("query_call_log", "query_error_code"), [log, code])]

    schedule = SharedToolScheduler().plan(work, registry=_Registry())

    assert [call.call.name for call in schedule.tool_batches[0].calls] == ["query_call_log"]
    assert schedule.deferred_calls == ({"id": "api-code", "tool": "query_error_code", "sourceAgent": "api_diagnostic", "reason": "dependency_ready"},)


def test_scheduler_limits_agents_and_splits_independent_tool_calls_by_global_budget():
    calls = [AgentToolCall(f"billing-{index}", "query_bill", {"month": f"2026-0{index}"}, source_agent="billing") for index in range(1, 4)]
    work = [
        _work("api_diagnostic", (), []),
        _work("billing", ("query_bill",), calls),
        _work("knowledge", (), []),
    ]

    schedule = SharedToolScheduler(max_agents=2, max_tools=2).plan(work, registry=_Registry())

    assert schedule.agent_batches == (("api_diagnostic", "billing"), ("knowledge",))
    assert [len(batch.calls) for batch in schedule.tool_batches] == [2, 1]


def test_scheduler_rejects_write_tools_before_the_handoff_node():
    handoff = AgentToolCall("handoff-1", "create_support_handoff", {}, source_agent="billing")
    work = [_work("billing", ("create_support_handoff",), [handoff])]

    schedule = SharedToolScheduler().plan(work, registry=_Registry())

    assert schedule.tool_batches == ()
    assert schedule.rejected_calls == ({"id": "handoff-1", "tool": "create_support_handoff", "reason": "write_tool_requires_handoff_node"},)
