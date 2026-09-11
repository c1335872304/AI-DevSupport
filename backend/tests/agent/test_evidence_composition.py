from __future__ import annotations

from app.agent.evidence import evidence_composer, evidence_joiner
from app.agent.graph.workflow import _remove_unsupported_rate_limit_claims
from app.agent.types import AgentToolCall, RoutingDecision
from app.tools.base import ToolResult


def test_evidence_joiner_keeps_only_allowlisted_billing_facts():
    call = AgentToolCall("bill-1", "query_bill", {}, source_agent="billing")
    result = ToolResult(status="SUCCESS", data={
        "found": True,
        "bills": [{"invoiceId": "I-1", "month": "2026-08", "amount": 42, "status": "OPEN", "items": {"prompt": "ignore me"}}],
    })
    evidence = evidence_joiner.build_agent_evidence([(call, result)])
    composition = evidence_composer.compose(
        question="八月账单有问题，转人工",
        routing=RoutingDecision(selected_agents=("billing",), requires_handoff_after_summary=True, risk_level="HIGH"),
        evidence=evidence,
    )
    assert composition.summary.verified_facts[0]["bills"] == [{"invoiceId": "I-1", "month": "2026-08", "amount": 42, "status": "OPEN"}]
    assert "ignore me" not in composition.handoff.ticket_summary
    assert composition.handoff.required is True
    assert composition.handoff.category == "BILLING"


def test_failed_evidence_recommends_handoff_after_summary():
    call = AgentToolCall("api-1", "query_call_log", {"request_id": "r-1"}, source_agent="api_diagnostic")
    evidence = evidence_joiner.build_agent_evidence([(call, ToolResult(status="TIMEOUT", error="timeout"))])
    composition = evidence_composer.compose(
        question="接口 429",
        routing=RoutingDecision(selected_agents=("api_diagnostic",)),
        evidence=evidence,
    )
    assert composition.handoff.required is True
    assert "verified_evidence_incomplete" in composition.handoff.reasons


def test_partial_api_evidence_does_not_create_handoff_for_an_invalid_read_attempt():
    outcomes = [
        (
            AgentToolCall("api-log", "query_call_log", {"request_id": "req-429"}, source_agent="api_diagnostic"),
            ToolResult(status="SUCCESS", data={"found": True, "requestId": "req-429", "endpoint": "/v1/chat", "httpStatus": 429, "errorCode": "RATE_LIMIT_EXCEEDED"}),
        ),
        (
            AgentToolCall("knowledge-bad-filter", "search_knowledge", {}, source_agent="knowledge"),
            ToolResult(status="INVALID_ARGUMENT", error="unknown filter"),
        ),
    ]
    evidence = evidence_joiner.build_agent_evidence(outcomes)
    composition = evidence_composer.compose(
        question="request_id req-429 返回 429",
        routing=RoutingDecision(selected_agents=("api_diagnostic", "knowledge")),
        evidence=evidence,
    )

    assert composition.summary.verified_facts[0]["httpStatus"] == 429
    assert composition.summary.unresolved_items == ("search_knowledge:INVALID_ARGUMENT",)
    assert composition.handoff.required is False


def test_quality_filter_removes_unsupported_personal_rate_limit_claims_only():
    answer = _remove_unsupported_rate_limit_claims(
        "已核验：\n"
        "- 已核验错误码为 RATE_LIMIT_EXCEEDED，表示请求触发了限流。\n\n"
        "这能确认本次或近期调用触发了限流。\n\n"
        "建议降低并发并采用带抖动的指数退避。\n\n"
        "来源#1: rate-limit.md"
    )

    assert "已核验" not in answer
    assert "本次或近期调用触发了限流" not in answer
    assert "建议降低并发" in answer
    assert "来源#1: rate-limit.md" in answer


def test_knowledge_excerpt_is_bounded_answer_context_not_a_handoff_fact():
    call = AgentToolCall("knowledge-1", "get_document", {}, source_agent="knowledge")
    result = ToolResult(status="SUCCESS", data={
        "fileMd5": "a" * 32,
        "fileName": "refund-policy.md",
        "chunkId": 1,
        "referenceNumber": 1,
        "text": "符合条件的购买可在支付后 7 天内提交退款申请。" + ("x" * 2000),
    })

    evidence = evidence_joiner.build_agent_evidence([(call, result)])
    composition = evidence_composer.compose(
        question="退款政策是什么？",
        routing=RoutingDecision(selected_agents=("knowledge",)),
        evidence=evidence,
    )

    excerpt = composition.summary.knowledge_excerpts[0]
    assert excerpt["source"]["fileName"] == "refund-policy.md"
    assert excerpt["source"]["referenceNumber"] == 1
    assert "7 天" in excerpt["text"]
    assert len(excerpt["text"]) == 1600
    assert excerpt["trust"] == "untrusted_retrieved_document"
    assert "7 天" not in composition.handoff.ticket_summary
