from __future__ import annotations

"""Structured evidence joining for the target customer-service architecture.

Only known, customer-safe Tool fields cross this boundary.  In particular, raw
MCP payloads, API key material, and retrieved document content never become
facts available to response composition or the later handoff node.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from app.agent.types import AgentEvidence, AgentToolCall, EvidenceSummary, HandoffDecision, RoutingDecision
from app.core.redaction import redact_text
from app.tools.base import ToolResult


_TOOL_AGENT = {
    "query_request_observation": "api_diagnostic",
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
_KNOWLEDGE_EXCERPT_LIMIT = 12


def _bounded_text(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def render_document_excerpts(summary: dict[str, Any], references: list[dict[str, Any]], *, question: str = "") -> str:
    """Publish bounded, attributed excerpts when synthesis is unavailable."""
    from app.core.content_safety import detect_prompt_injection
    from app.agent.question_scope import asks_about_personal_state

    available = {ref.get("referenceNumber") for ref in references}
    excerpts = []
    for item in summary.get("knowledgeExcerpts") or ():
        source = (item.get("source") or {}).get("referenceNumber")
        text = redact_text(_bounded_text(item.get("text"), _KNOWLEDGE_EXCERPT_MAX_CHARS))
        if source in available and text and not detect_prompt_injection(text):
            # Repeat the source on each quoted prose clause. Preserve code
            # blocks intact and never cite an adjoining generated statement.
            clauses = [text] if "```" in text or "~~~" in text else re.split(r"(?<=[。！？；])\s*", text)
            excerpts.extend(f"文档摘录（来源#{source}）：「{clause}」" for clause in clauses if clause)
    answer = "\n\n".join(dict.fromkeys(excerpts))
    if answer and asks_about_personal_state(question):
        answer += "\n\n仅凭这些文档无法确认您的账户状态或本次请求的实际情况。"
    return answer


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
                    for key in ("referenceNumber", "fileMd5", "fileName", "pageNumber", "chunkId", "indexVersion", "citationId", "sourceLocation")
                    if item.get(key) is not None
                },
                "text": redact_text(text),
                "trust": "untrusted_retrieved_document",
            }
        )
        if len(excerpts) >= _KNOWLEDGE_EXCERPT_LIMIT:
            break
    return excerpts


def _raw_facts_for(tool_name: str, data: Any) -> list[dict[str, Any]]:
    """Translate a successful result into a deliberately narrow fact contract."""
    if not isinstance(data, dict):
        return []
    if tool_name == "list_documents":
        documents = [
            {"fileName": redact_text(_bounded_text(item.get("fileName"), 240))}
            for item in (data.get("documents") or ())[:30]
            if isinstance(item, dict) and item.get("fileName")
        ]
        return [{"tool": tool_name, "found": bool(documents), "documents": documents}]
    if tool_name == "query_request_observation":
        from app.diagnosis.rules import SAFE_OBSERVATIONS
        return [{"tool": tool_name, "found": bool(data.get("found")),
                 **{k: data[k] for k in ["requestId", "appId", "endpoint", "serviceId", "ruleVersion"] if k in data},
                 "observations": {k: v for k, v in (data.get("observations") or {}).items() if k in SAFE_OBSERVATIONS}}]
    from app.support.billing import BILLING_TOOL_ALIASES

    tool_name = BILLING_TOOL_ALIASES.get(tool_name, tool_name)
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


def _facts_for(tool_name: str, data: Any) -> list[dict[str, Any]]:
    facts = _raw_facts_for(tool_name, data)
    if not isinstance(data, dict):
        return facts
    context = {key: data[key] for key in ["ownerUserId", "sourceSystem", "queriedAt", "calledAt",
        "windowType", "windowStart", "windowEnd", "scope", "appId", "requestId"] if key in data}
    context["sourceType"] = "DOCUMENT_RULE" if tool_name == "query_error_code" else "BUSINESS_QUERY"
    context["supportsPersonalIncident"] = tool_name == "query_call_log" and bool(data.get("found"))
    context["scope"] = ("general_rule" if tool_name == "query_error_code" else
                        "historical_event" if tool_name in {"query_call_log", "query_request_observation"} else
                        "historical_window" if data.get("windowType") in {"incident", "explicit"} else "current_snapshot")
    # A slow turn may outlive a snapshot. Do not forward it as a current fact.
    if context["scope"] == "current_snapshot" and data.get("queriedAt"):
        from datetime import timedelta
        from app.core.time import utcnow
        from app.support.api_diagnostics import parse_time, timestamp

        ttl = 30 if tool_name == "query_api_key_status" else 300 if tool_name in {"query_plan", "mcp__billing__get_plan"} else 60
        try:
            expires = parse_time(data["queriedAt"]) + timedelta(seconds=ttl)
            if expires < utcnow():
                return []
            context["validUntil"] = timestamp(expires)
        except (ValueError, TypeError, AttributeError):
            return []
    for fact in facts:
        fact["evidenceContext"] = context
    return facts


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
                if key not in excerpt_keys:
                    excerpt_keys.add(key)
                    knowledge_excerpts.append(dict(excerpt))
        # Round-robin documents so repeated chunks from one file cannot evict
        # the second vendor from a comparison. Keep the existing bounded text
        # size and cap the joined context at 12 excerpts (19,200 characters).
        groups: dict[str, list] = {}
        for excerpt in knowledge_excerpts:
            groups.setdefault(str(excerpt.get('source',{}).get('fileMd5') or excerpt.get('source',{}).get('fileName')),[]).append(excerpt)
        knowledge_excerpts=[]
        while any(groups.values()) and len(knowledge_excerpts)<_KNOWLEDGE_EXCERPT_LIMIT:
            for group in groups.values():
                if group and len(knowledge_excerpts)<_KNOWLEDGE_EXCERPT_LIMIT:
                    knowledge_excerpts.append(group.pop(0))
        unique_citations: list[dict[str, Any]] = []
        citation_keys: set[str] = set()
        for citation in citations:
            safe = {
                key: citation.get(key)
                for key in ("fileMd5", "fileName", "pageNumber", "chunkId", "referenceNumber", "indexVersion", "citationId", "sourceLocation")
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
        # Read failures belong to the evidence summary. Durable writes require
        # routing authorization or a separate persisted diagnosis decision.
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
