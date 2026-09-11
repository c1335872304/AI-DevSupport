from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AgentToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    source_agent: str | None = None
    source_skill: str | None = None


def tool_call_fingerprint(call: AgentToolCall) -> str:
    """Return a stable request-level identity for an idempotent read call.

    Provider-generated call IDs and specialist ownership are deliberately not
    included: two agents asking the same read question with the same normalized
    arguments should share the one verified result.
    """
    import json

    arguments = json.dumps(call.arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return f"{call.name}:{arguments}"


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Auditable routing contract for the target specialist architecture.

    Every customer-service request is resolved through this contract before
    specialist Tool work begins.
    """

    selected_agents: tuple[str, ...] = ()
    forced_agents: tuple[str, ...] = ()
    blocked_agents: tuple[str, ...] = ()
    matched_rules: tuple[str, ...] = ()
    risk_level: str = "LOW"
    requires_handoff_after_summary: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "selectedAgents": list(self.selected_agents),
            "forcedAgents": list(self.forced_agents),
            "blockedAgents": list(self.blocked_agents),
            "matchedRules": list(self.matched_rules),
            "riskLevel": self.risk_level,
            "requiresHandoffAfterSummary": self.requires_handoff_after_summary,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AgentPlan:
    """A bounded specialist task; agents may only request declared tools."""

    agent: str
    skill: str
    allowed_tools: tuple[str, ...]
    objective: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "skill": self.skill,
            "allowedTools": list(self.allowed_tools),
            "objective": self.objective,
        }


@dataclass(frozen=True, slots=True)
class ToolBatch:
    """One dependency-safe batch submitted to the shared Tool Runtime."""

    batch_id: str
    agent: str
    tool_call_ids: tuple[str, ...]
    depends_on: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batchId": self.batch_id,
            "agent": self.agent,
            "toolCallIds": list(self.tool_call_ids),
            "dependsOn": list(self.depends_on),
        }


@dataclass(frozen=True, slots=True)
class AgentEvidence:
    """Structured specialist output used by the evidence join, never final text."""

    agent: str
    status: str
    verified_facts: tuple[dict[str, Any], ...] = ()
    # Bounded, authorised document excerpts are kept separate from business facts.
    # They are answer-only context and must never be used as instructions or copied
    # into a handoff summary.
    knowledge_excerpts: tuple[dict[str, Any], ...] = ()
    citations: tuple[dict[str, Any], ...] = ()
    attempted_tools: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    recommended_handoff: bool = False
    tool_failures: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "verifiedFacts": list(self.verified_facts),
            "knowledgeExcerpts": list(self.knowledge_excerpts),
            "citations": list(self.citations),
            "attemptedTools": list(self.attempted_tools),
            "unresolvedItems": list(self.unresolved_items),
            "recommendedHandoff": self.recommended_handoff,
            "toolFailures": list(self.tool_failures),
        }


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    """Verified cross-agent evidence for answer composition and handoff context."""

    verified_facts: tuple[dict[str, Any], ...] = ()
    knowledge_excerpts: tuple[dict[str, Any], ...] = ()
    citations: tuple[dict[str, Any], ...] = ()
    attempted_steps: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifiedFacts": list(self.verified_facts),
            "knowledgeExcerpts": list(self.knowledge_excerpts),
            "citations": list(self.citations),
            "attemptedSteps": list(self.attempted_steps),
            "unresolvedItems": list(self.unresolved_items),
        }


@dataclass(frozen=True, slots=True)
class HandoffResult:
    """The only contract answer generation may use to claim handoff status."""

    attempted: bool = False
    success: bool = False
    handoff_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "success": self.success,
            "handoffId": self.handoff_id,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class HandoffDecision:
    """Internal decision produced only after the evidence summary is complete."""

    required: bool = False
    reasons: tuple[str, ...] = ()
    category: str = "GENERAL"
    priority: str = "NORMAL"
    ticket_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "reasons": list(self.reasons),
            "category": self.category,
            "priority": self.priority,
            "ticketSummary": self.ticket_summary,
        }
