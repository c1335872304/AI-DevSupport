from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent.evidence_followup import evidence_followup
from app.agent.llm import llm_service
from app.agent.skill_context import planning_turn
from app.agent.types import AgentToolCall
from app.skill_runtime.models import SkillDefinition
from app.skill_runtime.registry import SkillRegistry
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_skill_reference_is_lazy_bounded_and_reused(monkeypatch, tmp_path):
    (tmp_path / "detail.md").write_text("SPECIAL_WORKFLOW_DETAIL" * 500, encoding="utf-8")
    registry = SkillRegistry(
        [SkillDefinition("knowledge", "docs", tmp_path, "short instructions", references=("detail.md",))]
    )
    seen = []

    async def model(messages, tools):
        seen.append((messages, tools))
        if len(seen) == 1:
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    AgentToolCall(
                        "read", "read_skill_reference", {"skill": "knowledge", "reference": "detail.md"}
                    )
                ],
            }
        else:
            yield {
                "type": "tool_calls",
                "tool_calls": [AgentToolCall("search", "search_knowledge", {"query": "policy"})],
            }

    monkeypatch.setattr(llm_service, "stream_agent_turn", model)
    context = {}
    options = dict(skill_name="knowledge", registry=registry, context=context)
    events = [event async for event in planning_turn([{"role": "user", "content": "policy"}], [], **options)]
    assert "SPECIAL_WORKFLOW_DETAIL" not in str(seen[0][0])
    assert "SPECIAL_WORKFLOW_DETAIL" in str(seen[1][0])
    assert len(context["knowledge"]["messages"][1]["content"]) < 4300
    assert events[0]["tool_calls"][0].name == "search_knowledge"
    assert len(seen) == 2
    [event async for event in planning_turn([], [], **options)]
    assert len(seen) == 3
    assert not seen[-1][1]
    assert "SPECIAL_WORKFLOW_DETAIL" in str(seen[-1][0])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {"skill": "billing", "reference": "private.md"},
        {"skill": "knowledge", "reference": "../private.md"},
        {"skill": "knowledge", "reference": "allowed.md", "execute": True},
    ],
)
async def test_reference_cannot_expand_permissions_or_paths(monkeypatch, tmp_path, arguments):
    registry = SkillRegistry(
        [SkillDefinition("knowledge", "docs", tmp_path, "body", references=("allowed.md",))]
    )
    reads = []
    monkeypatch.setattr(registry, "read_reference", lambda *args: reads.append(args))
    invocations = []

    async def model(messages, tools):
        invocations.append(messages)
        # A persistent request for a forbidden reference cannot create a loop.
        yield {"type": "tool_calls", "tool_calls": [AgentToolCall("read", "read_skill_reference", arguments)]}

    monkeypatch.setattr(llm_service, "stream_agent_turn", model)
    context = {}
    [
        event
        async for event in planning_turn([], [], skill_name="knowledge", registry=registry, context=context)
    ]
    assert not reads
    assert len(invocations) == 2
    assert context["knowledge"]["attempts"] == 1


def _state():
    return {
        "question": "核查请求 req_a 的错误原因",
        "step": 1,
        "agent_plans": [
            {
                "agent": "api_diagnostic",
                "skill": "api-diagnostic",
                "allowedTools": ["query_call_log", "query_error_code", "query_api_key_status"],
            }
        ],
        "executed_tool_call_count": 1,
        "target_tool_outcomes": [
            (
                AgentToolCall(
                    "log", "query_call_log", {"request_id": "req_a"}, "api_diagnostic", "api-diagnostic"
                ),
                ToolResult(
                    "SUCCESS",
                    {"found": True, "requestId": "req_a", "errorCode": "ERR_AUTH", "appId": "app_a"},
                ),
            )
        ],
    }


class _Tools:
    def get(self, name):
        return SimpleNamespace(read_only=name != "create_support_handoff")


def test_supplement_uses_verified_dependency_and_stays_in_domain():
    state = _state()
    calls = evidence_followup(state, _Tools(), max_tools=8, max_steps=6)
    assert len(calls) == 2
    assert {call.name for call in calls} == {"query_error_code", "query_api_key_status"}
    assert next(call for call in calls if call.name == "query_error_code").arguments == {"code": "ERR_AUTH"}
    state["evidence_followup_count"] = 1
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


@pytest.mark.parametrize(
    "change",
    [
        {"step": 6},
        {"executed_tool_call_count": 8},
        {"diagnosis_lease": True},
        {"evidence_followup_count": 1},
    ],
)
def test_supplement_respects_existing_budgets_and_diagnosis_owner(change):
    state = {**_state(), **change}
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


@pytest.mark.parametrize("status", ["DENIED", "TIMEOUT", "ERROR"])
def test_supplement_does_not_retry_failed_or_denied_reads(status):
    state = _state()
    state["target_tool_outcomes"][0][1].status = status
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


def test_supplement_never_repeats_an_executed_call_or_expands_tools():
    state = _state()
    state["agent_plans"][0]["allowedTools"] = ["query_error_code"]
    assert len(evidence_followup(state, _Tools(), max_tools=2, max_steps=6)) == 1
    state["target_tool_outcomes"].append(
        (
            AgentToolCall("error", "query_error_code", {"code": "ERR_AUTH"}, "api_diagnostic"),
            ToolResult("DENIED"),
        )
    )
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


def test_healthy_request_and_complete_evidence_do_not_trigger_extra_queries():
    state = _state()
    state["target_tool_outcomes"][0][1].data = {"found": True, "httpStatus": 200, "appId": "app_a"}
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


@pytest.mark.parametrize(
    "prefix,bill,usage",
    [
        ("", "query_bill", "query_usage"),
        ("mcp__billing__", "get_invoice", "get_usage"),
    ],
)
def test_missing_billing_usage_retains_requested_month(prefix, bill, usage):
    state = {
        "question": "核对2026-08账单和用量",
        "entities": {"month": "2026-08"},
        "agent_plans": [
            {"agent": "billing", "skill": "billing", "allowedTools": [prefix + bill, prefix + usage]}
        ],
        "target_tool_outcomes": [
            (
                AgentToolCall("bill", prefix + bill, {"month": "2026-08"}, "billing", "billing"),
                ToolResult("SUCCESS", {"found": True, "bills": []}),
            )
        ],
    }
    calls = evidence_followup(state, _Tools(), max_tools=8, max_steps=6)
    assert len(calls) == 1
    assert calls[0].name == prefix + usage
    assert calls[0].arguments == {"month": "2026-08"}


def test_document_expansion_uses_existing_anchor_and_does_not_relax_scope():
    state = {
        "question": "比较北京和新加坡的规则",
        "agent_plans": [
            {"agent": "knowledge", "skill": "knowledge", "allowedTools": ["search_knowledge", "get_document"]}
        ],
        "target_tool_outcomes": [
            (
                AgentToolCall(
                    "search", "search_knowledge", {"query": "北京 新加坡"}, "knowledge", "knowledge"
                ),
                ToolResult("SUCCESS", {"status": "OK", "results": [{"fileMd5": "a" * 32, "chunkId": 4}]}),
            )
        ],
    }
    calls = evidence_followup(state, _Tools(), max_tools=8, max_steps=6)
    assert len(calls) == 1
    assert calls[0].name == "get_document"
    assert calls[0].arguments == {"file_md5": "a" * 32, "chunk_id": 4, "max_chars": 5000}
    state["target_tool_outcomes"][0][1].data["warnings"] = ["region conflict"]
    assert not evidence_followup(state, _Tools(), max_tools=8, max_steps=6)


@pytest.mark.asyncio
async def test_graph_supplements_once_when_specialist_stops_early(monkeypatch):
    from app.agent.graph.workflow import CustomerServiceWorkflow
    from app.skill_runtime.trace import SkillTrace

    events = []
    executions = []

    async def send(payload):
        events.append(payload)

    async def execute(**kwargs):
        executions.extend(kwargs["calls"])
        return [ToolResult("SUCCESS", {"found": True, "code": "ERR_AUTH"}) for _ in kwargs["calls"]]

    runtime = SimpleNamespace(
        settings=SimpleNamespace(agent_max_tool_calls=8, agent_max_steps=6),
        registry=_Tools(),
        _execute_parallel=execute,
        _collect_references=lambda *args: None,
    )
    workflow = CustomerServiceWorkflow(
        runtime=runtime, user=SimpleNamespace(id=1), send_json=send, on_chunk=send
    )
    state = {**_state(), "generation_id": "g-one", "skill_trace": SkillTrace(question="q")}
    state.update(await workflow.target_evidence_join(state))
    assert state["next_action"] == "target_execute_tools"
    state.update(await workflow.target_execute_tools(state))
    assert state["next_action"] == "target_evidence_join"
    state.update(await workflow.target_evidence_join(state))
    assert state["next_action"] == "target_handoff_decision"
    assert len(executions) == 2
    assert state["executed_tool_call_count"] == 3
    assert any(event.get("phase") == "supplementing" for event in events)
    assert all(
        set(event) <= {"type", "generationId", "phase", "timestamp"}
        for event in events
        if event["type"] == "workflow_progress"
    )


@pytest.mark.asyncio
async def test_complete_runtime_recovers_missing_dependency_without_extra_planning(monkeypatch):
    from app.agent.runtime import AgentRuntime
    from app.db.models import User
    from app.db.session import engine
    from app.tools.base import BaseTool
    from app.tools.registry import ToolRegistry

    executed = []

    class Read(BaseTool):
        input_schema = {"type": "object", "properties": {}, "additionalProperties": True}
        description = "isolated read fixture"

        def __init__(self, name, data):
            self.name, self.data = name, data

        async def execute(self, context, arguments):
            executed.append((self.name, arguments))
            return self.data

    planners = []

    async def model(messages, tools):
        planners.append(messages)
        # A repeated proposal is rejected by deduplication; the join must still
        # fill the known error-code dependency exactly once.
        names = {tool["function"]["name"] for tool in tools}
        call = (
            AgentToolCall("log", "query_call_log", {"request_id": "req_a"})
            if "query_call_log" in names
            else AgentToolCall("docs", "search_knowledge", {"query": "鉴权错误"})
        )
        yield {"type": "tool_calls", "tool_calls": [call]}

    async def classify(*args, **kwargs):
        return {}

    async def answer(*args, **kwargs):
        yield "请根据错误码说明核对鉴权配置。"

    monkeypatch.setattr(llm_service, "classify_intent", classify)
    monkeypatch.setattr(llm_service, "stream_agent_turn", model)
    monkeypatch.setattr(llm_service, "stream_messages", answer)
    runtime = AgentRuntime(
        ToolRegistry(
            [
                Read(
                    "query_call_log",
                    {"found": True, "requestId": "req_a", "httpStatus": 401, "errorCode": "ERR_AUTH"},
                ),
                Read("query_error_code", {"found": True, "code": "ERR_AUTH", "meaning": "鉴权失败"}),
                Read(
                    "search_knowledge",
                    {
                        "status": "OK",
                        "results": [
                            {
                                "fileMd5": "a" * 32,
                                "fileName": "authentication.md",
                                "chunkId": 1,
                                "textContent": "鉴权失败时应核对配置。",
                            }
                        ],
                    },
                ),
            ]
        )
    )
    events = []

    async def send(event):
        events.append(event)

    try:
        await runtime.run(
            user=User(id=991, username="isolated", password="x", role="USER"),
            question="request_id req_a 返回401，帮我排查原因",
            history=[],
            generation_id="supplement-runtime",
            send_json=send,
            on_chunk=send,
        )
        assert sorted(name for name, _ in executed) == [
            "query_call_log",
            "query_error_code",
            "search_knowledge",
        ]
        assert len(planners) == 3
        assert any(isinstance(event, dict) and event.get("phase") == "supplementing" for event in events)
    finally:
        await engine.dispose()
