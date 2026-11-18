from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
import pytest_asyncio

from app.agent.llm import llm_service
from app.agent.runtime import AgentRuntime
from app.agent.target_agents import TargetSpecialistAgents
from app.agent.types import AgentToolCall
from app.db.models import User
from app.db.session import engine
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry


class _FixtureTool(BaseTool):
    description = "target workflow E2E fixture"
    input_schema = {"type": "object", "properties": {}, "additionalProperties": True}

    def __init__(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        *,
        read_only: bool = True,
        delay_seconds: float = 0.0,
        timeout_seconds: float | None = None,
    ) -> None:
        self.name = name
        self.payload = dict(payload or {})
        self.read_only = read_only
        self.parallel_safe = read_only
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.calls: list[dict[str, Any]] = []

    async def execute(self, context: ToolExecutionContext, arguments: dict) -> dict[str, Any]:
        self.calls.append(dict(arguments))
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return dict(self.payload)


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_connections():
    await engine.dispose()
    yield
    await engine.dispose()


def _user(user_id: int = 701) -> User:
    return User(id=user_id, username=f"target-e2e-{user_id}", password="x", role="USER")


async def _run(
    runtime: AgentRuntime,
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    *,
    generation_id: str,
    planner_state: dict[str, Any] | None = None,
    final_answer: str = "基于已核验结果给出下一步。",
    semantic_hint: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    async def no_semantic_route(*_args, **_kwargs):
        return semantic_hint or {}

    async def final_response(_messages, force_no_tools=False):
        yield final_answer

    async def specialist_plan(messages, tools):
        names = {row["function"]["name"] for row in tools}
        context = str(messages[0].get("content") or "")
        if planner_state is not None:
            planner_state.setdefault("contexts", []).append({"tools": set(names), "content": context})
            planner_state["active"] = int(planner_state.get("active") or 0) + 1
            planner_state["maxActive"] = max(int(planner_state.get("maxActive") or 0), int(planner_state["active"]))
            try:
                await asyncio.sleep(float(planner_state.get("delaySeconds") or 0.0))
            finally:
                planner_state["active"] = int(planner_state.get("active") or 1) - 1
        attempted = context.split('"attemptedTools":', 1)[-1].split("]", 1)[0]
        calls: list[AgentToolCall] = []
        if "query_call_log" in names:
            if '"query_call_log"' not in attempted:
                calls.append(AgentToolCall("api-log", "query_call_log", {"request_id": "req_demo_429"}))
            else:
                for name, arguments in (
                    ("query_api_key_status", {"app_id": "app_demo"}),
                    ("query_error_code", {"code": "RATE_LIMIT_EXCEEDED"}),
                    ("query_recent_call_stats", {"endpoint": "/v1/chat", "minutes": 60}),
                ):
                    if name in names:
                        calls.append(AgentToolCall(f"api-{name}", name, arguments))
        elif "mcp__billing__get_invoice" in names and '"mcp__billing__get_invoice"' not in attempted:
            calls.append(AgentToolCall("billing-mcp-invoice", "mcp__billing__get_invoice", {}))
        elif "query_bill" in names and '"query_bill"' not in attempted:
            calls.append(AgentToolCall("billing-bill", "query_bill", {}))
        elif "search_knowledge" in names:
            if '"search_knowledge"' not in attempted:
                calls.append(AgentToolCall("knowledge-search", "search_knowledge", {"query": str(messages[-1].get("content") or "")}))
            elif "get_document" in names and '"get_document"' not in attempted and '"fileMd5": "aaaaaaaa' in context:
                calls.append(AgentToolCall("knowledge-document", "get_document", {"file_md5": "a" * 32, "chunk_id": 4, "max_chars": 5000}))
        if calls:
            yield {"type": "tool_calls", "tool_calls": calls}

    monkeypatch.setattr(llm_service, "classify_intent", no_semantic_route)
    monkeypatch.setattr(llm_service, "stream_agent_turn", specialist_plan)
    monkeypatch.setattr(llm_service, "stream_messages", final_response)
    events: list[dict[str, Any]] = []
    chunks: list[str] = []

    async def send_json(event: dict[str, Any]) -> None:
        events.append(event)

    async def on_chunk(chunk: str) -> None:
        chunks.append(chunk)

    answer, _references = await runtime.run(
        user=_user(),
        question=question,
        history=[],
        generation_id=generation_id,
        send_json=send_json,
        on_chunk=on_chunk,
    )
    return answer, events, chunks


def _nodes(events: list[dict[str, Any]]) -> list[str]:
    return [str(event["node"]) for event in events if event.get("type") == "workflow_node"]


@pytest.mark.asyncio
async def test_read_only_billing_uses_final_handoff_decision_over_model_hint(monkeypatch):
    bill=_FixtureTool('query_bill',{'found':True,'bills':[{'invoiceId':'INV-12','month':'2026-10','amount':12,'status':'ISSUED'}]})
    handoff=_FixtureTool('create_support_handoff',{'handoffId':'CS-UNWANTED'},read_only=False)
    answer,events,_=await _run(AgentRuntime(ToolRegistry([bill,handoff])),monkeypatch,
        '请核实2026-10的套餐、用量和账单金额。',generation_id='billing-conflicting-model-hint',
        semantic_hint={'intent':'billing','needs_human':True,'entities':{'month':'2026-10'},'confidence':.95},
        final_answer='已查询账单，2026-10金额为12元。')
    assert '12' in answer and not handoff.calls
    assert not next(e for e in events if e.get('type')=='handoff_decision')['decision']['required']
    assert all(e['passed'] for e in events if e.get('type')=='quality_gate')
    assert not any(e.get('type')=='quality_gate_blocked' for e in events)


@pytest.mark.parametrize('question',['我要退款','帮我升套餐','请转人工核查账单','请把这个问题提交人工，我需要确认工单是否建好。'])
async def test_required_handoff_survives_low_risk_model_hint(monkeypatch,question):
    bill=_FixtureTool('query_bill',{'found':True,'bills':[{'invoiceId':'INV-12','month':'2026-10','amount':12,'status':'ISSUED'}]})
    handoff=_FixtureTool('create_support_handoff',{'handoffId':'CS-REQUIRED','status':'OPEN'},read_only=False)
    _,events,_=await _run(AgentRuntime(ToolRegistry([bill,handoff])),monkeypatch,question,
        generation_id='required-handoff-boundary',semantic_hint={'intent':'billing','needs_human':False,'confidence':.99},
        final_answer='已创建人工工单，业务结果需人工核验。')
    assert len(handoff.calls)==1
    assert _nodes(events).index('target_evidence_join') < _nodes(events).index('target_create_handoff')
    assert next(e for e in events if e.get('type')=='handoff_decision')['decision']['required']
    assert all(e['passed'] for e in events if e.get('type')=='quality_gate')


@pytest.mark.asyncio
async def test_handoff_success_without_id_does_not_confirm_this_request(monkeypatch):
    handoff = _FixtureTool("create_support_handoff", {"status": "OPEN"}, read_only=False)
    answer, events, chunks = await _run(
        AgentRuntime(ToolRegistry([handoff])), monkeypatch, "请提交人工处理",
        generation_id="handoff-without-id",
        final_answer="已创建人工工单，等待人工处理。",
    )
    assert len(handoff.calls) == 1
    trace = next(event["trace"] for event in events if event.get("type") == "skill_trace")
    assert trace["handoffResult"]["attempted"] is True
    assert trace["handoffResult"]["success"] is False
    assert "已创建人工工单" not in answer + "".join(chunks)


@pytest.mark.asyncio
async def test_billing_tool_uses_request_month_and_rejects_wrong_period(monkeypatch):
    bill = _FixtureTool("query_bill", {"found": True, "bills": [
        {"invoiceId": "FIXTURE-OTHER", "month": "2026-02", "amount": 12, "status": "PAID"},
    ]})
    answer, events, _ = await _run(
        AgentRuntime(ToolRegistry([bill])), monkeypatch, "帮我查 2026-11 的账单金额。",
        generation_id="billing-period-boundary", final_answer="暂时未核实该账期金额。",
    )
    assert bill.calls == [{"month": "2026-11"}]
    failure = next(event for event in events if event.get("resultStatus") == "ERROR")
    assert failure["error"] == "Billing period mismatch"
    assert "12" not in answer


def test_api_diagnostic_tool_parameters_require_customer_or_log_provenance():
    assert not TargetSpecialistAgents._api_call_has_diagnostic_anchor(
        "query_error_code", {"code": "RATE_LIMIT_EXCEEDED"}, {}, [],
    )
    assert TargetSpecialistAgents._api_call_has_diagnostic_anchor(
        "query_error_code", {"code": "RATE_LIMIT_EXCEEDED"}, {"error_code": "RATE_LIMIT_EXCEEDED"}, [],
    )
    prior_log = (
        AgentToolCall("api-log", "query_call_log", {"request_id": "req-1"}, source_agent="api_diagnostic"),
        type("Result", (), {"status": "SUCCESS", "data": {"found": True, "errorCode": "RATE_LIMIT_EXCEEDED"}})(),
    )
    assert TargetSpecialistAgents._api_call_has_diagnostic_anchor(
        "query_error_code", {"code": "RATE_LIMIT_EXCEEDED"}, {}, [prior_log],
    )


@pytest.mark.asyncio
async def test_api_request_id_e2e_runs_dependency_batch_then_parent_context(monkeypatch):
    call_log = _FixtureTool("query_call_log", {
        "found": True, "requestId": "req_demo_429", "appId": "app_demo",
        "endpoint": "/v1/chat", "httpStatus": 429, "errorCode": "RATE_LIMIT_EXCEEDED",
    })
    api_key = _FixtureTool("query_api_key_status", {"found": True, "keys": []})
    error_code = _FixtureTool("query_error_code", {"found": True, "code": "RATE_LIMIT_EXCEEDED", "cause": "rate limit"})
    stats = _FixtureTool("query_recent_call_stats", {"endpoint": "/v1/chat", "windowMinutes": 60, "total": 10, "byStatus": {"429": 3}, "rateLimitedCount": 3, "rateLimitedRatio": 0.3})
    search = _FixtureTool("search_knowledge", {"results": [{"fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4, "pageNumber": 1}]})
    document = _FixtureTool("get_document", {"fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4, "pageNumber": 1, "textContent": "429 限流说明"})
    runtime = AgentRuntime(ToolRegistry([call_log, api_key, error_code, stats, search, document]))

    answer, events, _chunks = await _run(runtime, monkeypatch, "request_id req_demo_429 接口返回 429", generation_id="target-e2e-api")

    assert answer
    assert call_log.calls == [{"request_id": "req_demo_429"}]
    assert api_key.calls == [{"app_id": "app_demo"}]
    assert error_code.calls == [{"code": "RATE_LIMIT_EXCEEDED"}]
    assert stats.calls == [{"endpoint": "/v1/chat", "minutes": 60}]
    assert document.calls == [{"file_md5": "a" * 32, "chunk_id": 4, "max_chars": 5000}]
    nodes = _nodes(events)
    assert nodes.count("target_execute_tools") == 2
    assert nodes.index("target_evidence_join") < nodes.index("target_handoff_decision")
    assert "target_create_handoff" not in nodes


@pytest.mark.asyncio
async def test_confirmed_429_evidence_keeps_a_grounded_model_diagnostic_without_gate_rewrite(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "llm_api_key", "test-only")
    call_log = _FixtureTool("query_call_log", {
        "found": True, "requestId": "req_demo_429", "appId": "app_demo",
        "endpoint": "/v1/chat", "httpStatus": 429, "errorCode": "RATE_LIMIT_EXCEEDED",
    })
    api_key = _FixtureTool("query_api_key_status", {"found": True, "keys": []})
    error_code = _FixtureTool("query_error_code", {"found": True, "code": "RATE_LIMIT_EXCEEDED", "cause": "rate limit"})
    stats = _FixtureTool("query_recent_call_stats", {"endpoint": "/v1/chat", "windowMinutes": 60, "total": 10, "byStatus": {"429": 3}, "rateLimitedCount": 3, "rateLimitedRatio": 0.3})
    search = _FixtureTool("search_knowledge", {"results": [{"fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4, "pageNumber": 1}]})
    document = _FixtureTool("get_document", {"fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4, "pageNumber": 1, "textContent": "429 限流说明"})
    runtime = AgentRuntime(ToolRegistry([call_log, api_key, error_code, stats, search, document]))

    answer, events, _chunks = await _run(
        runtime,
        monkeypatch,
        "request_id req_demo_429 接口返回 429，是不是月额度用完了？",
        generation_id="target-e2e-confirmed-429",
        final_answer=(
            "请求 req_demo_429 在 /v1/chat 返回 HTTP 429（RATE_LIMIT_EXCEEDED）。"
            "最近 60 分钟共 10 次调用，其中 3 次为 429。"
            "不能仅凭 429 推断月额度已经用尽。\n\n来源#1: rate-limit.md"
        ),
    )

    assert "req_demo_429" in answer
    assert "HTTP 429" in answer
    assert "10 次调用，其中 3 次为 429" in answer
    assert "不能仅凭 429 推断月额度已经用尽" in answer
    assert "来源#1: rate-limit.md" in answer
    api_gate = next(event for event in events if event.get("type") == "quality_gate" and event.get("skill") == "api-diagnostic")
    assert api_gate["passed"] is True
    assert not any(event.get("type") == "quality_gate_repaired" for event in events)
    assert not any(event.get("type") == "quality_gate_blocked" for event in events)
    assert "target_create_handoff" not in _nodes(events)


@pytest.mark.asyncio
async def test_first_time_rate_limit_question_filters_unsupported_personal_claims(monkeypatch, langfuse_receiver):
    search = _FixtureTool("search_knowledge", {
        "results": [{"fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4, "pageNumber": 1}],
    })
    document = _FixtureTool("get_document", {
        "fileMd5": "a" * 32, "fileName": "rate-limit.md", "chunkId": 4,
        "pageNumber": 1, "textContent": "限流时应降低并发并使用指数退避。",
    })
    runtime = AgentRuntime(ToolRegistry([search, document]))

    answer, events, _chunks = await _run(
        runtime,
        monkeypatch,
        "我被限流了，怎么回事",
        generation_id="target-e2e-first-rate-limit",
        final_answer=(
            "已核验：\n- 已核验错误码为 RATE_LIMIT_EXCEEDED，表示请求触发了限流。\n\n"
            "这能确认本次或近期调用触发了限流。\n\n"
            "建议降低并发并采用带抖动的指数退避。\n\n来源#1: rate-limit.md"
        ),
    )

    assert "已核验" not in answer
    assert "本次或近期调用触发了限流" not in answer
    assert "建议降低并发" in answer
    assert "来源#1: rate-limit.md" in answer
    api_gate = next(event for event in events if event.get("type") == "quality_gate" and event.get("skill") == "api-diagnostic")
    assert api_gate["passed"] is False
    assert "unsupported_personal_rate_limit_claim" in api_gate["warnings"]
    filtered = next(event for event in events if event.get("type") == "quality_gate_filtered")
    assert filtered["action"] == "filtered_unsupported_claims"
    assert not any(event.get("type") == "quality_gate_repaired" for event in events)
    assert not any(event.get("type") == "quality_gate_blocked" for event in events)
    spans = langfuse_receiver("我被限流了，怎么回事", "本次或近期调用触发了限流", "rate-limit.md")
    root, = [span for span in spans if not span.parent_span_id]
    exported = next(item.value.string_value for item in root.attributes if item.key == "langfuse.observation.output")
    output = json.loads(exported)
    assert output["qualityGateAction"] == "filtered_unsupported_claims"
    assert any(gate["filtered"] for gate in output["qualityGates"].values())
    assert "unsupported_personal_rate_limit_claim" in (
        output["qualityGates"]["api-diagnostic:audit_api_diagnostic"]["ruleCodes"]
    )
    assert {"search_knowledge", "safety"} <= {span.name for span in spans if span.trace_id == root.trace_id}


@pytest.mark.asyncio
async def test_three_selected_agents_run_concurrently_with_independent_tool_contexts(monkeypatch):
    api_log = _FixtureTool("query_call_log", {"found": True, "requestId": "req_demo_429"})
    bill = _FixtureTool("query_bill", {"found": True, "bills": [{"invoiceId": "INV-1"}]})
    search = _FixtureTool("search_knowledge", {"results": []})
    runtime = AgentRuntime(ToolRegistry([api_log, bill, search]))
    planner_state: dict[str, Any] = {"delaySeconds": 0.02}

    _answer, events, _chunks = await _run(
        runtime,
        monkeypatch,
        "request_id req_demo_429 的账单和退款政策是什么？",
        generation_id="target-e2e-three-agents",
        planner_state=planner_state,
    )

    dispatch = next(event for event in events if event.get("type") == "target_specialists_dispatched")
    assert dispatch["planningMode"] == "concurrent_llm"
    assert set(dispatch["agents"]) == {"api_diagnostic", "billing", "knowledge"}
    assert len(planner_state["contexts"]) >= 3
    assert planner_state["maxActive"] == 3

    context_tools = [row["tools"] for row in planner_state["contexts"][:3]]
    assert any("query_call_log" in names and "query_bill" not in names for names in context_tools)
    assert any("query_bill" in names and "query_call_log" not in names for names in context_tools)
    assert any("search_knowledge" in names and "query_call_log" not in names and "query_bill" not in names for names in context_tools)
    assert api_log.calls == [{"request_id": "req_demo_429"}]
    assert bill.calls == [{}]
    assert search.calls == [{"query": "request_id req_demo_429 的账单和退款政策是什么？"}]
    assert "target_evidence_join" in _nodes(events)


@pytest.mark.asyncio
async def test_high_risk_billing_e2e_collects_evidence_before_creating_handoff(monkeypatch):
    bill = _FixtureTool("query_bill", {"found": True, "bills": [{"invoiceId": "INV-1", "month": "2026-08", "amount": 99, "status": "PAID"}]})
    handoff = _FixtureTool("create_support_handoff", {"handoffId": "CS-701", "status": "OPEN"}, read_only=False)
    runtime = AgentRuntime(ToolRegistry([bill, handoff]))

    _answer, events, _chunks = await _run(runtime, monkeypatch, "我想申请退款，账单有重复扣费", generation_id="target-e2e-billing")

    assert len(bill.calls) == 1
    assert len(handoff.calls) == 1
    nodes = _nodes(events)
    assert nodes.index("target_evidence_join") < nodes.index("target_handoff_decision") < nodes.index("target_create_handoff")
    handoff_event = next(event for event in events if event.get("type") == "handoff_decision")
    assert handoff_event["decision"]["required"] is True
    assert any(event.get("type") == "tool_call" and event.get("tool") == "create_support_handoff" and event.get("status") == "success" for event in events)


@pytest.mark.asyncio
@pytest.mark.parametrize("remote_fails", [False, True], ids=["success", "failure"])
async def test_high_risk_billing_mcp_e2e_discovers_tools_before_fact_collection(
    monkeypatch, langfuse_receiver, remote_fails,
):
    """The Billing Agent must use the MCP catalog, never the local billing Tool."""
    from types import SimpleNamespace

    import app.tools.mcp.billing as billing_module
    from app.tools.mcp.billing import billing_mcp_adapter

    monkeypatch.setattr(billing_mcp_adapter.settings, "billing_mcp_enabled", True)
    monkeypatch.setattr(billing_mcp_adapter.settings, "billing_mcp_url", "http://billing-mcp:8011/mcp")
    discovered = SimpleNamespace(
        name="get_invoice",
        description="Read the authenticated customer's invoices.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "month": {"type": "string"},
            },
            "required": ["customer_id"],
        },
        annotations=SimpleNamespace(read_only_hint=True),
    )
    remote_calls: list[dict[str, Any]] = []

    async def fake_list_tools(self):
        return [discovered]

    async def fake_call_tool(self, name, arguments):
        remote_calls.append({"name": name, "arguments": dict(arguments)})
        await asyncio.sleep(0.08)
        if remote_fails:
            raise RuntimeError("private-mcp-error-detail")
        return {
            "structuredContent": {
                "found": True,
                "bills": [{
                    "invoiceId": "INV-1",
                    "month": "2026-08",
                    "amount": 99,
                    "status": "PAID",
                    "items": {},
                }],
            }
        }

    monkeypatch.setattr(billing_module.MCPRemoteClient, "list_tools", fake_list_tools)
    monkeypatch.setattr(billing_module.MCPRemoteClient, "call_tool", fake_call_tool)
    handoff = _FixtureTool("create_support_handoff", {"handoffId": "CS-703", "status": "OPEN"}, read_only=False)
    runtime = AgentRuntime(ToolRegistry([handoff]))

    _answer, events, _chunks = await _run(
        runtime,
        monkeypatch,
        "我想申请退款，账单有重复扣费",
        generation_id="target-e2e-billing-mcp",
    )

    discovery_event = next(event for event in events if event.get("type") == "billing_mcp_tools_discovered")
    assert [tool["name"] for tool in discovery_event["tools"]] == ["mcp__billing__get_invoice"]
    assert "customer_id" not in discovery_event["tools"][0]["inputSchema"]["properties"]
    assert remote_calls == [{"name": "get_invoice", "arguments": {"customer_id": "701"}}]
    exported = langfuse_receiver("private-mcp-error-detail", "customer_id", "INV-1")
    tool_span, = [span for span in exported if span.name == "mcp__billing__get_invoice"]
    output = next(item.value.string_value for item in tool_span.attributes if item.key == "langfuse.observation.output")
    telemetry = json.loads(output)
    assert telemetry["status"] == ("ERROR" if remote_fails else "SUCCESS")
    assert telemetry["durationMs"] >= 30
    assert tool_span.end_time_unix_nano > tool_span.start_time_unix_nano
    if remote_fails:
        assert tool_span.status.code == 2
        assert tool_span.status.message == "ERROR"

    assert len(handoff.calls) == 1
    nodes = _nodes(events)
    assert nodes.index("target_evidence_join") < nodes.index("target_handoff_decision") < nodes.index("target_create_handoff")


@pytest.mark.asyncio
async def test_tool_timeout_e2e_records_failure_and_never_claims_handoff_success(monkeypatch):
    search = _FixtureTool("search_knowledge", delay_seconds=0.03, timeout_seconds=0.001)
    handoff = _FixtureTool("create_support_handoff", {"handoffId": "CS-702", "status": "OPEN"}, read_only=False)
    runtime = AgentRuntime(ToolRegistry([search, handoff]))

    answer, events, _chunks = await _run(runtime, monkeypatch, "请说明退款政策", generation_id="target-e2e-timeout")

    failed = [event for event in events if event.get("type") == "tool_call" and event.get("tool") == "search_knowledge" and event.get("status") == "failed"]
    assert failed and failed[-1]["resultStatus"] == "TIMEOUT"
    evidence_event = next(event for event in events if event.get("type") == "evidence_summary")
    assert "search_knowledge:TIMEOUT" in evidence_event["summary"]["unresolvedItems"]
    assert "target_create_handoff" not in _nodes(events)
    assert handoff.calls == []
    assert "查询超时" in answer
    assert "已创建人工工单" not in answer
