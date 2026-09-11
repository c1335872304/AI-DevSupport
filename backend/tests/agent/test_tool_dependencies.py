from app.agent.dependencies import ToolDependencyAnalyzer
from app.agent.types import AgentToolCall


def _call(name: str, **arguments) -> AgentToolCall:
    return AgentToolCall(id=f"{name}-1", name=name, arguments=arguments)


def test_api_dependency_keeps_downstream_lookup_after_call_log():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, plan = analyzer.next_batch([
        _call("query_call_log", request_id="req_demo_401"),
        _call("query_error_code"),
        _call("query_api_key_status"),
    ])

    assert [call.name for call in ready] == ["query_call_log"]
    assert {call.name for call in remaining} == {"query_error_code", "query_api_key_status"}
    assert plan["reason"] == "dependency_ready"
    assert set(plan["blocked"]) == {"query_error_code", "query_api_key_status"}
    assert {tuple(edge.values()) for edge in plan["dependencies"]} == {
        ("query_error_code", "query_call_log"),
        ("query_api_key_status", "query_call_log"),
    }


def test_explicit_dependency_arguments_allow_parallel_lookup():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, _ = analyzer.next_batch([
        _call("query_error_code", code="AUTH_KEY_EXPIRED"),
        _call("query_api_key_status", app_id="app_demo"),
        _call("query_recent_call_stats", endpoint="/v1/chat"),
    ])

    assert {call.name for call in ready} == {
        "query_error_code", "query_api_key_status", "query_recent_call_stats"
    }
    assert remaining == []


def test_completed_predecessor_unblocks_downstream_lookup():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, _ = analyzer.next_batch(
        [_call("query_error_code")], {"query_call_log"}
    )

    assert [call.name for call in ready] == ["query_error_code"]
    assert remaining == []


def test_missing_predecessor_is_blocked_instead_of_executed():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, plan = analyzer.next_batch([_call("query_error_code")])

    assert ready == []
    assert [call.name for call in remaining] == ["query_error_code"]
    assert plan["reason"] == "missing_dependency"
    assert plan["missingDependencies"] == [{"tool": "query_error_code", "dependsOn": "query_call_log"}]


def test_handoff_is_exclusive_safety_barrier():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, plan = analyzer.next_batch([
        _call("query_plan"),
        _call("create_support_handoff", reason="退款需要人工核验"),
        _call("search_knowledge", query="退款政策"),
    ])

    assert [call.name for call in ready] == ["create_support_handoff"]
    assert {call.name for call in remaining} == {"query_plan", "search_knowledge"}
    assert plan["barrier"] == "handoff"


def test_independent_read_tools_share_one_parallel_batch():
    analyzer = ToolDependencyAnalyzer()
    ready, remaining, plan = analyzer.next_batch([
        _call("query_plan"),
        _call("query_usage", month="2026-08"),
        _call("query_bill", month="2026-08"),
    ])

    assert {call.name for call in ready} == {"query_plan", "query_usage", "query_bill"}
    assert remaining == []
    assert len(plan["batches"]) == 1
