from __future__ import annotations

from app.agent.routing_policy import routing_policy


def test_high_risk_refund_is_not_downgraded_by_a_general_semantic_hint():
    decision = routing_policy.decide("我想申请退款", {}, {"intent": "general"})

    assert decision.requires_handoff_after_summary is True
    assert decision.risk_level == "HIGH"
    assert decision.forced_agents == ("billing",)
    assert "high_risk_billing_or_contract_operation" in decision.matched_rules


def test_refund_policy_is_knowledge_not_a_handoff_request():
    decision = routing_policy.decide("退款政策和条件是什么？", {}, {"intent": "refund_policy"})

    assert decision.requires_handoff_after_summary is False
    assert "knowledge" in decision.selected_agents
    assert "high_risk_billing_or_contract_operation" not in decision.matched_rules


def test_api_and_billing_compound_question_selects_both_specialists():
    decision = routing_policy.decide(
        "request_id req_demo_429 返回 429，为什么本月账单费用上涨？",
        {"request_id": "req_demo_429", "http_status": "429", "month": "2026-08"},
        {"intent": "api_diagnostic"},
    )

    assert decision.selected_agents == ("api_diagnostic", "billing", "knowledge")
    assert decision.risk_level == "MEDIUM"
    assert "api_diagnostic_entity" in decision.matched_rules
    assert "billing_keyword" in decision.matched_rules


def test_explicit_handoff_is_recorded_but_does_not_skip_api_evidence_collection():
    decision = routing_policy.decide(
        "接口一直 401，帮我转人工",
        {"http_status": "401"},
        {"intent": "general"},
    )

    assert decision.requires_handoff_after_summary is True
    assert decision.selected_agents == ("api_diagnostic",)
    assert decision.forced_agents == ()


def test_generic_explicit_handoff_does_not_start_an_unrelated_specialist():
    decision = routing_policy.decide("请直接转人工客服处理", {}, {"intent": "general"})

    assert decision.requires_handoff_after_summary is True
    assert decision.selected_agents == ()
    assert "handoff_without_specialist" in decision.matched_rules


def test_explicit_handoff_negation_does_not_force_a_ticket():
    decision = routing_policy.decide("不用人工了，问题已经解决", {}, {"intent": "general"})

    assert decision.requires_handoff_after_summary is False
    assert "handoff_negated" in decision.matched_rules


def test_greeting_does_not_start_a_specialist():
    decision = routing_policy.decide("你好", {}, {"intent": "general"})

    assert decision.selected_agents == ()
    assert decision.matched_rules == ("chitchat",)
