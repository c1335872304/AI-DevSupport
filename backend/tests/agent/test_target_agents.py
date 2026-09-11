from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.agent.llm import llm_service
from app.agent.target_agents import target_specialist_agents
from app.agent.types import AgentPlan, AgentToolCall


class _Skill:
    def __init__(self, allowed_tools: tuple[str, ...]) -> None:
        self.allowed_tools = allowed_tools


class _Registry:
    _tools = {
        "api-diagnostic": (
            "query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code", "search_knowledge",
        ),
        "billing": ("query_plan", "query_usage", "query_bill"),
        "knowledge": ("search_knowledge", "list_documents", "get_document"),
    }

    def get(self, name: str):
        tools = self._tools.get(name)
        return _Skill(tools) if tools else None


class _ToolRegistry:
    def llm_tools(self, names):
        return [{"type": "function", "function": {"name": name}} for name in names]


@pytest.mark.asyncio
async def test_target_agents_propose_only_their_own_allowlisted_tools(monkeypatch):
    async def fake_stream(_messages, tools):
        name = tools[0]["function"]["name"]
        arguments = {"request_id": "req_demo_401"} if name == "query_call_log" else {}
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("planner", name, arguments)]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_stream)
    plans = [
        AgentPlan("api_diagnostic", "api-diagnostic", ("query_call_log",), "diagnose API"),
        AgentPlan("billing", "billing", ("query_bill",), "verify billing"),
        AgentPlan("knowledge", "knowledge", ("search_knowledge",), "retrieve knowledge"),
    ]
    work = await target_specialist_agents.plan_work(
        plans=plans,
        question="request_id req_demo_401 返回 401，2026-08 的账单费用太高",
        entities={"request_id": "req_demo_401", "http_status": "401", "month": "2026-08"},
        registry=_Registry(),
        tool_registry=_ToolRegistry(),
    )

    by_agent = {item.plan.agent: item for item in work}
    assert [call.name for call in by_agent["api_diagnostic"].proposed_calls] == ["query_call_log"]
    assert [call.name for call in by_agent["billing"].proposed_calls] == ["query_bill"]
    assert [call.name for call in by_agent["knowledge"].proposed_calls] == ["search_knowledge"]
    for item in work:
        assert all(call.name in item.plan.allowed_tools for call in item.proposed_calls)


@pytest.mark.asyncio
async def test_knowledge_search_uses_graph_supplied_retrieval_query_without_changing_other_tools(monkeypatch):
    async def fake_stream(_messages, tools):
        name = tools[0]["function"]["name"]
        arguments = {"request_id": "req_demo_401"} if name == "query_call_log" else {"query": "raw"}
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("planner", name, arguments)]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_stream)
    plans = [
        AgentPlan("api_diagnostic", "api-diagnostic", ("query_call_log",), "diagnose"),
        AgentPlan("knowledge", "knowledge", ("search_knowledge",), "retrieve"),
    ]
    work = await target_specialist_agents.plan_work(
        plans=plans,
        question="那为什么会这样？",
        retrieval_query="原始问题：那为什么会这样？\n检索改写：req_demo_401 的 401 鉴权失败原因",
        entities={"request_id": "req_demo_401"},
        registry=_Registry(),
        tool_registry=_ToolRegistry(),
    )

    calls = {item.plan.agent: item.proposed_calls[0] for item in work}
    assert calls["knowledge"].arguments["query"].startswith("原始问题：")
    assert calls["api_diagnostic"].arguments == {"request_id": "req_demo_401"}


def test_agent_evidence_contains_status_only_until_domain_extractors_are_introduced():
    agent = target_specialist_agents.get("billing")
    assert agent is not None
    plan = AgentPlan("billing", "billing", ("query_plan", "query_usage", "query_bill"), "verify billing")
    calls = agent.initial_calls(plan, "查询套餐和用量", {"month": "2026-08"})
    outcomes = [(calls[0], SimpleNamespace(status="SUCCESS", data={"secret": "not copied"}))]

    evidence = agent.evidence_from_results(outcomes)
    assert evidence.status == "completed"
    assert evidence.verified_facts == ({"source": calls[0].name, "verified": True},)
    assert "secret" not in str(evidence.to_dict())


def test_api_agent_derives_second_batch_only_from_verified_call_log_fields():
    agent = target_specialist_agents.get("api_diagnostic")
    assert agent is not None
    plan = AgentPlan(
        "api_diagnostic", "api-diagnostic",
        ("query_call_log", "query_api_key_status", "query_error_code", "query_recent_call_stats"),
        "diagnose",
    )
    first = agent.initial_calls(plan, "request_id req-1", {"request_id": "req-1"})[0]
    result = SimpleNamespace(status="SUCCESS", data={
        "found": True, "appId": "app-1", "errorCode": "E401", "endpoint": "/v1/chat", "httpStatus": 429,
    })

    calls = agent.follow_up_calls(plan, [(first, result)], {"query_call_log"})

    assert [(call.name, call.arguments) for call in calls] == [
        ("query_api_key_status", {"app_id": "app-1"}),
        ("query_error_code", {"code": "E401"}),
        ("query_recent_call_stats", {"endpoint": "/v1/chat", "minutes": 60}),
    ]


def test_knowledge_agent_reads_one_access_controlled_document_after_search_hit():
    agent = target_specialist_agents.get("knowledge")
    assert agent is not None
    plan = AgentPlan("knowledge", "knowledge", ("search_knowledge", "get_document"), "retrieve")
    first = agent.initial_calls(plan, "退款政策", {})[0]
    result = SimpleNamespace(status="SUCCESS", data={
        "results": [{"fileMd5": "a" * 32, "chunkId": 7, "textContent": "untrusted"}],
    })

    calls = agent.follow_up_calls(plan, [(first, result)], {"search_knowledge"})

    assert len(calls) == 1
    assert calls[0].name == "get_document"
    assert calls[0].arguments == {"file_md5": "a" * 32, "chunk_id": 7, "max_chars": 5000}


@pytest.mark.asyncio
async def test_selected_llm_agents_plan_concurrently_with_only_their_own_tools(monkeypatch):
    active = 0
    peak = 0

    async def fake_stream(messages, tools):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        names = {row["function"]["name"] for row in tools}
        name = next(iter(names))
        arguments = {"request_id": "req_demo_401"} if name == "query_call_log" else {}
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("planner", name, arguments)]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_stream)
    plans = [
        AgentPlan("api_diagnostic", "api-diagnostic", ("query_call_log",), "api"),
        AgentPlan("billing", "billing", ("query_plan",), "billing"),
        AgentPlan("knowledge", "knowledge", ("search_knowledge",), "knowledge"),
    ]
    work = await target_specialist_agents.plan_work(
        plans=plans,
        question="request_id req_demo_401，请处理问题",
        entities={"request_id": "req_demo_401"},
        registry=_Registry(),
        tool_registry=_ToolRegistry(),
        max_agents=3,
    )

    assert peak == 3
    assert {item.plan.agent for item in work} == {"api_diagnostic", "billing", "knowledge"}
    for item in work:
        assert [call.name for call in item.proposed_calls] == list(item.plan.allowed_tools)
        assert all(call.source_agent == item.plan.agent and call.source_skill == item.plan.skill for call in item.proposed_calls)


@pytest.mark.asyncio
async def test_agent_planner_skips_a_call_fingerprint_already_executed(monkeypatch):
    async def fake_stream(_messages, _tools):
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("planner", "search_knowledge", {"query": "退款政策"})]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_stream)
    plan = AgentPlan("knowledge", "knowledge", ("search_knowledge",), "retrieve")
    work = await target_specialist_agents.plan_work(
        plans=[plan],
        question="退款政策是什么？",
        entities={},
        registry=_Registry(),
        tool_registry=_ToolRegistry(),
        attempted_call_fingerprints=['search_knowledge:{"query":"退款政策"}'],
    )

    assert work[0].proposed_calls == ()
