from __future__ import annotations

"""Structured evidence joining for the target customer-service architecture.

Only known, customer-safe Tool fields cross this boundary.  In particular, raw
MCP payloads, API key material, and retrieved document content never become
facts available to response composition or the later handoff node.
"""

import json
from dataclasses import dataclass
from typing import Any, Iterable

from app.agent.types import AgentEvidence, AgentToolCall, EvidenceSummary, HandoffDecision, RoutingDecision
from app.core.redaction import redact_text
from app.tools.base import ToolResult


_TOOL_AGENT = {
    "query_call_log": "api_diagnostic",
    "query_api_key_status": "api_diagnostic",
    "query_recent_call_stats": "api_diagnostic",
    "query_error_code": "api_diagnostic",
    "query_plan": "billing",
    "query_usage": "billing",
    "query_bill": "billing",
    "search_knowledge": "knowledge",
    "list_documents": "knowledge",
    "get_document": "knowledge",
}

_KNOWLEDGE_EXCERPT_MAX_CHARS = 1600
_KNOWLEDGE_EXCERPT_LIMIT = 3


def _bounded_text(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def _knowledge_excerpts_for(tool_name: str, data: Any) -> list[dict[str, Any]]:
    """Keep small, authorised document excerpts for answer composition only.

    Search and document Tool payloads are intentionally not copied wholesale into
    ``verifiedFacts``: they may contain untrusted document text.  The bounded
    excerpts below retain the supporting content required for a grounded answer,
    while preserving source metadata and an explicit trust marker for the final
    response prompt.
    """
    if not isinstance(data, dict):
        return []
    if tool_name == "search_knowledge":
        candidates = data.get("results") if isinstance(data.get("results"), list) else []
    elif tool_name == "get_document":
        candidates = [data]
    else:
        return []

    excerpts: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        text = _bounded_text(item.get("text") or item.get("textContent"), _KNOWLEDGE_EXCERPT_MAX_CHARS)
        if not text:
            continue
        excerpts.append(
            {
                "source": {
                    key: item.get(key)
                    for key in ("referenceNumber", "fileMd5", "fileName", "pageNumber", "chunkId")
                    if item.get(key) is not None
                },
                "text": redact_text(text),
                "trust": "untrusted_retrieved_document",
            }
        )
        if len(excerpts) >= _KNOWLEDGE_EXCERPT_LIMIT:
            break
    return excerpts


def _facts_for(tool_name: str, data: Any) -> list[dict[str, Any]]:
    """Translate a successful result into a deliberately narrow fact contract."""
    if not isinstance(data, dict):
        return []
    billing_aliases = {
        "mcp__billing__get_plan": "query_plan",
        "mcp__billing__get_usage": "query_usage",
        "mcp__billing__get_invoice": "query_bill",
    }
    tool_name = billing_aliases.get(tool_name, tool_name)
    if tool_name == "query_call_log":
        return [{
            "tool": tool_name,
            "found": bool(data.get("found")),
            # Preserve the requested ID even when it was not found. It lets the
            # final diagnostic distinguish a missing record from a confirmed
            # 429 elsewhere in the customer's recent statistics.
            **({key: data[key] for key in ("requestId",) if key in data}),
            **({key: data[key] for key in ("appId", "endpoint", "httpStatus", "errorCode", "latencyMs") if key in data} if data.get("found") else {}),
        }]
    if tool_name == "query_api_key_status":
        keys = data.get("keys") if isinstance(data.get("keys"), list) else []
        return [{
            "tool": tool_name,
            "found": bool(data.get("found")),
            "keys": [
                {key: item[key] for key in ("apiKeyId", "appId", "status", "expireAt", "expired") if key in item}
                for item in keys if isinstance(item, dict)
            ],
        }]
    if tool_name == "query_recent_call_stats":
        return [{
            "tool": tool_name,
            "endpoint": data.get("endpoint"),
            "windowMinutes": data.get("windowMinutes"),
            "total": data.get("total"),
            "byStatus": data.get("byStatus") if isinstance(data.get("byStatus"), dict) else {},
            "rateLimitedCount": data.get("rateLimitedCount"),
            "rateLimitedRatio": data.get("rateLimitedRatio"),
        }]
    if tool_name == "query_error_code":
        fact = {"tool": tool_name, "found": bool(data.get("found")), "code": data.get("code")}
        if data.get("found"):
            fact.update({
                key: _bounded_text(data.get(key)) if key in {"name", "cause", "fixSteps"} else data.get(key)
                for key in ("name", "httpStatus", "cause", "fixSteps") if key in data
            })
        return [fact]
    if tool_name == "query_plan":
        allowed = ("subscriptionStatus", "planId", "planName", "qpsLimit", "monthlyQuota", "basePrice", "overagePricePerCall")
        return [{"tool": tool_name, "found": bool(data.get("found")), **{key: data[key] for key in allowed if key in data}}]
    if tool_name == "query_usage":
        usage = data.get("usage") if isinstance(data.get("usage"), list) else []
        return [{
            "tool": tool_name,
            "found": bool(data.get("found")),
            "usage": [
                {key: item[key] for key in ("month", "callCount", "overageCount") if key in item}
                for item in usage if isinstance(item, dict)
            ],
        }]
    if tool_name == "query_bill":
        bills = data.get("bills") if isinstance(data.get("bills"), list) else []
        # Do not carry free-form line items into the agent context. The fixed
        # invoice identity, amount and status are sufficient for verified facts.
        return [{
            "tool": tool_name,
            "found": bool(data.get("found")),
            "bills": [
                {key: item[key] for key in ("invoiceId", "month", "amount", "status") if key in item}
                for item in bills if isinstance(item, dict)
            ],
        }]
    return []


class EvidenceJoiner:
    """Join per-agent verified facts, citations and failures deterministically."""

    def build_agent_evidence(
        self,
        outcomes: Iterable[tuple[AgentToolCall, ToolResult]],
    ) -> list[AgentEvidence]:
        grouped: dict[str, dict[str, Any]] = {}
        for call, result in outcomes:
            agent = call.source_agent or _TOOL_AGENT.get(call.name)
            if agent not in {"api_diagnostic", "billing", "knowledge"}:
                continue
            bucket = grouped.setdefault(agent, {"facts": [], "tools": [], "failures": []})
            bucket["tools"].append(call.name)
            if result.status == "SUCCESS":
                bucket["facts"].extend(_facts_for(call.name, result.data))
            else:
                bucket["failures"].append({"tool": call.name, "status": result.status})

        evidence: list[AgentEvidence] = []
        for agent in ("api_diagnostic", "billing", "knowledge"):
            bucket = grouped.get(agent)
            if not bucket:
                continue
            failures = tuple(bucket["failures"])
            facts = tuple(bucket["facts"])
            evidence.append(AgentEvidence(
                agent=agent,
                status="failed" if failures and not facts else ("partial" if failures else "completed"),
                verified_facts=facts,
                knowledge_excerpts=tuple(
                    excerpt
                    for call, result in outcomes
                    if call.source_agent == agent and result.status == "SUCCESS"
                    for excerpt in _knowledge_excerpts_for(call.name, result.data)
                ),
                attempted_tools=tuple(dict.fromkeys(bucket["tools"])),
                unresolved_items=tuple(f"{item['tool']}:{item['status']}" for item in failures),
                # A failed read attempt must not create a ticket when other
                # read tools already produced enough verified facts for a safe
                # answer.  Escalate only if this specialist has no usable
                # evidence at all; explicit/high-risk routing remains handled
                # independently by the handoff decision.
                recommended_handoff=bool(failures and not facts),
                tool_failures=failures,
            ))
        return evidence

    def join(self, evidence: Iterable[AgentEvidence], citations: Iterable[dict[str, Any]] = ()) -> EvidenceSummary:
        facts: list[dict[str, Any]] = []
        fact_keys: set[str] = set()
        attempted: list[str] = []
        unresolved: list[str] = []
        knowledge_excerpts: list[dict[str, Any]] = []
        excerpt_keys: set[str] = set()
        for item in evidence:
            for fact in item.verified_facts:
                key = json.dumps(fact, ensure_ascii=False, sort_keys=True, default=str)
                if key not in fact_keys:
                    fact_keys.add(key)
                    facts.append(dict(fact))
            attempted.extend(item.attempted_tools)
            unresolved.extend(item.unresolved_items)
            for excerpt in item.knowledge_excerpts:
                key = json.dumps(excerpt, ensure_ascii=False, sort_keys=True, default=str)
                if key not in excerpt_keys and len(knowledge_excerpts) < _KNOWLEDGE_EXCERPT_LIMIT:
                    excerpt_keys.add(key)
                    knowledge_excerpts.append(dict(excerpt))
        unique_citations: list[dict[str, Any]] = []
        citation_keys: set[str] = set()
        for citation in citations:
            safe = {
                key: citation.get(key)
                for key in ("fileMd5", "fileName", "pageNumber", "chunkId", "referenceNumber")
                if key in citation
            }
            key = json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str)
            if key not in citation_keys:
                citation_keys.add(key)
                unique_citations.append(safe)
        return EvidenceSummary(
            verified_facts=tuple(facts),
            knowledge_excerpts=tuple(knowledge_excerpts),
            citations=tuple(unique_citations),
            attempted_steps=tuple(dict.fromkeys(attempted)),
            unresolved_items=tuple(dict.fromkeys(unresolved)),
        )


@dataclass(frozen=True, slots=True)
class EvidenceComposition:
    summary: EvidenceSummary
    handoff: HandoffDecision

    def to_dict(self) -> dict[str, Any]:
        return {**self.summary.to_dict(), "handoffDecision": self.handoff.to_dict()}


class EvidenceComposer:
    """Create an internal-only ticket summary after all read evidence is joined."""

    def compose(
        self,
        *,
        question: str,
        routing: RoutingDecision,
        evidence: Iterable[AgentEvidence],
        citations: Iterable[dict[str, Any]] = (),
    ) -> EvidenceComposition:
        records = list(evidence)
        summary = EvidenceJoiner().join(records, citations)
        reasons: list[str] = []
        if routing.requires_handoff_after_summary:
            reasons.append("routing_policy_requires_handoff_after_summary")
        if any(item.recommended_handoff for item in records) and not summary.verified_facts:
            reasons.append("specialist_recommends_handoff")
        # Partial read failures are visible in the trace and answer boundary,
        # but do not justify an automatic human ticket once verified evidence
        # exists (for example, a confirmed 429 plus one malformed RAG query).
        if summary.unresolved_items and not summary.verified_facts:
            reasons.append("verified_evidence_incomplete")
        category = "BILLING" if "billing" in routing.selected_agents else "API" if "api_diagnostic" in routing.selected_agents else "GENERAL"
        priority = "HIGH" if routing.risk_level == "HIGH" else "NORMAL"
        ticket_summary = (
            f"客户诉求：{_bounded_text(question, 1200)}\n"
            f"已执行工具：{', '.join(summary.attempted_steps) or '无'}\n"
            f"已确认事实：{json.dumps(list(summary.verified_facts), ensure_ascii=False, default=str)[:3000]}\n"
            f"未解决项：{', '.join(summary.unresolved_items) or '无'}\n"
            f"转人工原因：{', '.join(reasons) or '无'}"
        )[:6000]
        return EvidenceComposition(
            summary=summary,
            handoff=HandoffDecision(
                required=bool(reasons),
                reasons=tuple(reasons),
                category=category,
                priority=priority,
                ticket_summary=ticket_summary,
            ),
        )


evidence_joiner = EvidenceJoiner()
evidence_composer = EvidenceComposer()


def routing_decision_from_dict(value: dict[str, Any] | None) -> RoutingDecision:
    """Restore the trace-safe routing payload without trusting extra fields."""
    raw = value or {}
    return RoutingDecision(
        selected_agents=tuple(str(item) for item in raw.get("selectedAgents") or ()),
        forced_agents=tuple(str(item) for item in raw.get("forcedAgents") or ()),
        blocked_agents=tuple(str(item) for item in raw.get("blockedAgents") or ()),
        matched_rules=tuple(str(item) for item in raw.get("matchedRules") or ()),
        risk_level=str(raw.get("riskLevel") or "LOW"),
        requires_handoff_after_summary=bool(raw.get("requiresHandoffAfterSummary")),
        reason=str(raw.get("reason") or ""),
    )
