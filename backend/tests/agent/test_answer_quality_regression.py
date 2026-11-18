import pytest

from app.agent.evidence import evidence_composer, evidence_joiner
from app.agent.graph.answer_content import ensure_reference_citations
from app.agent.graph.workflow import _diagnostic_clarification
from app.agent.question_scope import vendor_clarification
from app.agent.routing_policy import routing_policy
from app.agent.target_agents import _scope_knowledge_call
from app.agent.types import AgentToolCall, RoutingDecision
from app.tools.base import ToolResult


@pytest.mark.parametrize(
    "question",
    [
        "Qwen北京Key能用于新加坡Base URL吗？",
        "Qwen embedding每行8192 Token，256维支持吗？",
        "OpenAI后台响应queued如何轮询？",
        "DeepSeek官方规则能保证我的账号未来永不限流吗？",
        "按公开说明，AUTH_FAILED 有什么含义？",
        "认证配置是什么？",
        "509 是否总等于月配额耗尽？",
        "API 的单批提交上限是多少？",
    ],
)
def test_document_rules_override_noisy_diagnostic_classifier_and_numeric_entities(question):
    decision = routing_policy.decide(question, {"http_status": "256"}, {"intent": "api_diagnostic"})
    assert decision.selected_agents == ("knowledge",)
    assert not decision.requires_handoff_after_summary


def test_real_incident_and_financial_operation_keep_original_protection():
    assert (
        "api_diagnostic"
        in routing_policy.decide("Qwen请求返回401，请排查", {"request_id": "req_123"}).selected_agents
    )
    assert routing_policy.decide(
        "Qwen请求退款转人工", {}, {"intent": "refund_request"}
    ).requires_handoff_after_summary
    assert routing_policy.decide("请直接退款").requires_handoff_after_summary
    assert not routing_policy.decide("请说明退款流程").requires_handoff_after_summary


def test_unknown_vendor_needs_clarification_but_named_vendor_does_not():
    assert vendor_clarification("启用strict后枚举就一定正确吗？请给API配置参数")
    assert not vendor_clarification("Qwen JSON Schema如何设置参数？")


def test_diagnostic_clarification_asks_for_the_next_missing_detail():
    assert "操作" in _diagnostic_clarification({"diagnostic_scope": "unspecified"}, {}, diagnostic=False)
    incident = {"diagnostic_scope": "incident", "intent": "api_diagnostic"}
    assert "报错" in _diagnostic_clarification(incident, {"endpoint": "/v1/chat"}, diagnostic=True)
    assert "request_id" in _diagnostic_clarification(incident, {"http_status": "429"}, diagnostic=True)
    assert "报错" in _diagnostic_clarification(
        {"diagnostic_scope": "unspecified"}, {}, diagnostic=True,
        question="更正，是同步通讯录时报错，不是登录。",
    )
    assert "报错" in _diagnostic_clarification(
        {"diagnostic_scope": "unspecified"}, {}, diagnostic=True,
        question="同步通讯录时总是失败。",
    )
    assert not _diagnostic_clarification(incident, {"request_id": "req_context_001"}, diagnostic=True)
    assert not _diagnostic_clarification(
        {"diagnostic_scope": "aggregate", "intent": "api_diagnostic"},
        {"endpoint": "/v1/chat"}, diagnostic=True,
    )


async def test_real_langgraph_carries_clarification_to_conditional_edge():
    from app.agent.graph.engine import END, START, StateGraph
    from app.agent.graph.state import CustomerServiceState
    from app.agent.graph.workflow import _route_after_intent

    graph = StateGraph(CustomerServiceState)
    graph.add_node("route", lambda state: {"clarification_question": "请选择厂商"})
    graph.add_node("clarify", lambda state: {"final_answer": state["clarification_question"]})
    graph.add_node("wrong", lambda state: {"final_answer": "incorrectly searched"})
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route", _route_after_intent, {"clarify": "clarify", "target_specialist_dispatch": "wrong"}
    )
    graph.add_edge("clarify", END)
    graph.add_edge("wrong", END)
    assert (await graph.compile().ainvoke({"question": "strict配置"}))["final_answer"] == "请选择厂商"


def test_top_level_metadata_aliases_are_normalized_without_losing_version_constraints():
    call = _scope_knowledge_call(
        AgentToolCall(
            "x",
            "search_knowledge",
            {
                "query": "OpenAI认证",
                "product": "OpenAI API",
                "category": "api",
                "effective_at": "2026-01-01",
                "filters": {"version": "v2"},
            },
            "knowledge",
        ),
        "Qwen认证",
    )
    assert call.arguments == {
        "query": "Qwen认证",
        "filters": {"product": "Qwen API", "category": "api", "effective_at": "2026-01-01", "version": "v2"},
    }


def test_same_document_multiple_chunks_keep_mapping_numbers_and_correct_labels():
    refs = [
        {"referenceNumber": n, "fileName": name}
        for n, name in [(1, "a.md"), (2, "a.md"), (3, "b.md"), (4, "c.md")]
    ]
    answer = ensure_reference_citations("结论（来源#3: wrong.md）。\n来源#1: wrong.md", refs)
    assert "来源#3: b.md" in answer and "wrong.md" not in answer
    assert "来源#2: a.md" in answer and "来源#4: c.md" in answer


@pytest.mark.parametrize('question', [
    'Qwen text-embedding-v4在北京和新加坡价格是否相同？',
    '比较Qwen cn-beijing与ap-southeast-1的免费额度',
    'Qwen跨地域的计费差异是什么？',
])
def test_region_comparison_cannot_be_narrowed_by_planner_or_extracted_entity(question):
    call = _scope_knowledge_call(AgentToolCall('x', 'search_knowledge', {
        'query': 'Qwen北京价格', 'region': 'CN',
        'filters': {'category': 'billing', 'version': 'v2', 'effective_at': '2026-10-19'},
    }, 'knowledge'), question, {'region': 'CN'})
    assert call.arguments['query'] == question
    assert call.arguments['filters'] == {
        'product': 'Qwen API', 'version': 'v2', 'effective_at': '2026-10-19',
    }


def test_single_region_and_explicit_comparison_category_remain_constrained():
    call = AgentToolCall('x', 'search_knowledge', {'query': 'Qwen配置',
        'filters': {'region': 'APAC', 'category': 'billing'}}, 'knowledge')
    result = _scope_knowledge_call(call, 'Qwen新加坡配置', {'region': 'APAC'})
    assert result.arguments['filters']['region'] == 'APAC'
    result = _scope_knowledge_call(call, '比较Qwen北京和新加坡，仅查billing分类')
    assert result.arguments['filters']['category'] == 'billing'
    assert 'region' not in result.arguments['filters']


def test_comparison_preserves_second_vendor_and_does_not_turn_rules_into_personal_facts():
    results = [
        {"fileMd5": "a", "fileName": "gpt.md", "chunkId": i, "textContent": f"OpenAI rule {i}"}
        for i in range(8)
    ]
    results.append(
        {"fileMd5": "b", "fileName": "deepseek.md", "chunkId": 0, "textContent": "DeepSeek valid JSON only"}
    )
    outcomes = [
        (
            AgentToolCall("good", "search_knowledge", {}, "knowledge"),
            ToolResult(status="SUCCESS", data={"results": results}),
        ),
        (AgentToolCall("bad", "search_knowledge", {}, "knowledge"), ToolResult(status="INVALID_ARGUMENT")),
    ]
    composition = evidence_composer.compose(
        question="比较两家",
        routing=RoutingDecision(selected_agents=("knowledge",)),
        evidence=evidence_joiner.build_agent_evidence(outcomes),
    )
    assert not composition.summary.verified_facts
    assert composition.summary.knowledge_excerpts[1]["source"]["fileName"] == "deepseek.md"
    assert not composition.handoff.required
    assert composition.summary.unresolved_items


async def test_query_derived_filename_recall_keeps_permission_and_product_filters(monkeypatch):
    from app.db.models import User
    from app.knowledge.elasticsearch import ElasticsearchService

    service = ElasticsearchService()
    calls = []

    class Client:
        async def search(self, **kwargs):
            calls.append(kwargs)
            name = "qwen-errors.md" if "knn" in kwargs else "qwen-base-url.md"
            return {
                "hits": {
                    "hits": [
                        {
                            "_id": name,
                            "_score": 1,
                            "_source": {
                                "fileMd5": name,
                                "fileName": name,
                                "chunkId": 0,
                                "textContent": "rule",
                                "userId": "1",
                            },
                        }
                    ]
                }
            }

    async def ready():
        pass

    monkeypatch.setattr(service, "client", Client())
    monkeypatch.setattr(service, "ensure_index", ready)
    result = await service.search(
        User(id=91, username="reader", password="x", role="USER"),
        "千问的Base URL和API Key怎样匹配",
        [1.0, 0.0],
        2,
        metadata_filters={"product": "Qwen API"},
    )
    assert result[0]["fileName"] == "qwen-base-url.md"
    assert "*base-url*" in str(calls[1]["query"])
    for request in calls:
        filters = request["knn"]["filter"] if "knn" in request else request["query"]["bool"]["filter"]
        assert "Qwen API" in str(filters) and "isPublic" in str(filters) and "fixture-" in str(filters)
