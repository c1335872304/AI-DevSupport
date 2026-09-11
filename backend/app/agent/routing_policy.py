from __future__ import annotations

"""Deterministic, traceable routing policy for the target Agent architecture.

This module deliberately does not execute Tools or choose Skills.  It produces
the authoritative, auditable Agent selection for the target workflow.
High-risk rules are evaluated before semantic hints, so a request cannot
silently downgrade an explicit handoff-worthy operation.
"""

from typing import Any

from app.agent.types import RoutingDecision


class RoutingPolicy:
    """Map customer intent and normalized entities to bounded specialist Agents."""

    _HANDOFF_REQUESTS = (
        "转人工", "人工客服", "人工处理", "找人工", "投诉", "升级处理", "客服经理", "人工介入",
    )
    _HANDOFF_NEGATIONS = ("不用人工", "不要转人工", "无需人工", "已经解决", "问题已解决")
    _HIGH_RISK_OPERATIONS = (
        "申请退款", "我要退款", "我想退款", "退款申请", "退费", "退订", "重复扣费",
        "支付争议", "chargeback", "改价", "升套餐", "降套餐", "套餐变更", "退差价",
    )
    _POLICY_ONLY = ("政策", "规则", "条件", "标准", "能不能退", "是否可以退", "退款流程")
    _API_TERMS = (
        "api", "接口", "request_id", "request id", "api key", "鉴权", "限流", "qps",
        "webhook", "请求失败", "接口报错",
    )
    _API_KNOWLEDGE_TERMS = (
        "api key", "apikey", "过期", "失效", "有效期", "错误码", "为什么", "原因", "怎么处理",
    )
    _BILLING_TERMS = (
        "账单", "费用", "扣费", "用量", "调用量", "套餐", "配额", "余额", "发票", "invoice", "billing",
    )
    _KNOWLEDGE_TERMS = (
        "知识库", "文档", "说明", "政策", "规则", "条件", "标准", "如何", "怎么", "是什么", "错误码", "产品说明",
    )
    _CHITCHAT = ("你好", "您好", "嗨", "hello", "hi", "谢谢", "感谢")
    _API_ENTITY_KEYS = {"request_id", "error_code", "http_status", "endpoint", "app_id", "api_key_id", "webhook_event_id"}
    _BILLING_ENTITY_KEYS = {"invoice_id", "transaction_id"}
    _SEMANTIC_API = {"api_diagnostic", "authentication_error", "network_error", "upload_error", "payment_error"}
    _SEMANTIC_BILLING = {"billing", "refund_policy", "refund_request", "refund_dispute", "payment_dispute", "subscription_change", "chargeback"}
    _SEMANTIC_KNOWLEDGE = {"product_usage", "refund_policy", "general"}

    def decide(
        self,
        question: str,
        entities: dict[str, str] | None = None,
        semantic_hint: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        text = " ".join(str(question or "").lower().split())
        resolved = dict(entities or {})
        semantic = str((semantic_hint or {}).get("intent") or "").strip().lower()
        matched: list[str] = []
        selected: list[str] = []
        forced: list[str] = []

        def add(agent: str, *, force: bool = False) -> None:
            if agent not in selected:
                selected.append(agent)
            if force and agent not in forced:
                forced.append(agent)

        # Exact greetings and thanks have no customer-service evidence to
        # collect. Handle them before a broad semantic ``general`` hint can
        # route them to the Knowledge Agent.
        if text in self._CHITCHAT:
            return RoutingDecision(matched_rules=("chitchat",), reason="chitchat")

        policy_only = any(token in text for token in self._POLICY_ONLY)
        explicit_handoff = any(token in text for token in self._HANDOFF_REQUESTS)
        handoff_negated = any(token in text for token in self._HANDOFF_NEGATIONS)
        high_risk_operation = any(token in text for token in self._HIGH_RISK_OPERATIONS) and not policy_only
        requires_handoff = high_risk_operation or (explicit_handoff and not handoff_negated)

        if high_risk_operation:
            matched.append("high_risk_billing_or_contract_operation")
        if explicit_handoff and not handoff_negated:
            matched.append("explicit_handoff_request")
        if handoff_negated:
            matched.append("handoff_negated")

        # A financial/contract operation needs billing evidence. A generic
        # request for a human must not accidentally start billing work; it is
        # carried by ``requires_handoff_after_summary`` to the later handoff
        # node after any actually relevant specialist has completed.
        if high_risk_operation:
            add("billing", force=True)

        api_entity_match = bool(self._API_ENTITY_KEYS.intersection(resolved))
        api_lexical_match = any(token in text for token in self._API_TERMS)
        api_semantic_match = semantic in self._SEMANTIC_API
        api_knowledge_match = api_lexical_match and any(token in text for token in self._API_KNOWLEDGE_TERMS)
        if api_entity_match or api_lexical_match or api_semantic_match:
            add("api_diagnostic")
            if api_entity_match:
                matched.append("api_diagnostic_entity")
            elif api_lexical_match:
                matched.append("api_diagnostic_keyword")
            else:
                matched.append("api_diagnostic_semantic_hint")

        billing_entity_match = bool(self._BILLING_ENTITY_KEYS.intersection(resolved))
        billing_lexical_match = any(token in text for token in self._BILLING_TERMS)
        billing_semantic_match = semantic in self._SEMANTIC_BILLING
        if billing_entity_match or billing_lexical_match or billing_semantic_match:
            add("billing")
            if billing_entity_match:
                matched.append("billing_entity")
            elif billing_lexical_match:
                matched.append("billing_keyword")
            else:
                matched.append("billing_semantic_hint")

        knowledge_lexical_match = any(token in text for token in self._KNOWLEDGE_TERMS)
        knowledge_semantic_match = semantic in self._SEMANTIC_KNOWLEDGE
        # Knowledge supports policy explanations and API documentation, but it
        # never substitutes for customer-specific billing/API evidence.
        if (
            knowledge_lexical_match
            or (knowledge_semantic_match and not requires_handoff)
            or (api_entity_match and not requires_handoff)
            or (api_knowledge_match and not requires_handoff)
        ):
            add("knowledge")
            if knowledge_lexical_match:
                matched.append("knowledge_keyword")
            elif knowledge_semantic_match:
                matched.append("knowledge_semantic_hint")
            else:
                matched.append("api_evidence_needs_knowledge_context")

        if not selected and requires_handoff:
            matched.append("handoff_without_specialist")
        elif not selected:
            # The target architecture has no fourth general-purpose specialist.
            # Unknown customer-support questions use knowledge as the safe,
            # evidence-seeking default rather than relying on model memory.
            add("knowledge")
            matched.append("knowledge_safe_default")

        ordered = tuple(agent for agent in ("api_diagnostic", "billing", "knowledge") if agent in selected)
        ordered_forced = tuple(agent for agent in ordered if agent in forced)
        risk = "HIGH" if requires_handoff else "MEDIUM" if len(ordered) > 1 else "LOW"
        reason = "；".join(matched) or "no_specialist_required"
        return RoutingDecision(
            selected_agents=ordered,
            forced_agents=ordered_forced,
            matched_rules=tuple(dict.fromkeys(matched)),
            risk_level=risk,
            requires_handoff_after_summary=requires_handoff,
            reason=reason,
        )


routing_policy = RoutingPolicy()
