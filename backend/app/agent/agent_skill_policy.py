from __future__ import annotations

"""Target-architecture Agent/Skill bindings.

The runtime has exactly three specialist Agents.  This module is the single
source of truth for their Skill contracts and permissions.
"""

from typing import Protocol

from app.agent.types import AgentPlan, RoutingDecision


class _Skill(Protocol):
    allowed_tools: tuple[str, ...]
    references: tuple[str, ...]
    scripts: tuple[str, ...]
    quality_gate: str | None


class _SkillRegistry(Protocol):
    def get(self, name: str) -> _Skill | None: ...


TARGET_AGENT_SKILLS = {
    "api_diagnostic": "api-diagnostic",
    "billing": "billing",
    "knowledge": "knowledge",
}

TARGET_AGENT_TOOLS = {
    "api_diagnostic": (
        "query_call_log",
        "query_api_key_status",
        "query_recent_call_stats",
        "query_error_code",
        "search_knowledge",
    ),
    # Billing's local fallback contract intentionally excludes direct handoff
    # and knowledge access. When Billing MCP is enabled, this tuple is replaced
    # at dispatch time by the validated ``list_tools`` catalog.
    "billing": ("query_plan", "query_usage", "query_bill"),
    "knowledge": ("search_knowledge", "list_documents", "get_document"),
}

TARGET_AGENT_OBJECTIVES = {
    "api_diagnostic": "Collect verified API diagnostic evidence without changing customer data.",
    "billing": "Collect verified, read-only billing facts without executing financial or contract changes.",
    "knowledge": "Retrieve cited enterprise knowledge without inferring customer-specific business facts.",
}

SHARED_NODE_SKILLS = {
    "handoff_decision": "escalation",
    "create_support_handoff": "escalation",
    "generate_customer_response": "customer-support",
}

def build_target_agent_plans(decision: RoutingDecision, registry: _SkillRegistry) -> list[AgentPlan]:
    """Build bounded plans and fail fast when a Skill contract has drifted."""
    plans: list[AgentPlan] = []
    for agent in decision.selected_agents:
        skill_name = TARGET_AGENT_SKILLS.get(agent)
        allowed_tools = TARGET_AGENT_TOOLS.get(agent)
        objective = TARGET_AGENT_OBJECTIVES.get(agent)
        if not skill_name or not allowed_tools or not objective:
            raise ValueError(f"Unknown target specialist agent: {agent}")
        skill = registry.get(skill_name)
        if not skill:
            raise RuntimeError(f"Target Agent {agent} requires Skill {skill_name}")
        undeclared = set(allowed_tools).difference(skill.allowed_tools)
        if undeclared:
            raise RuntimeError(
                f"Target Agent {agent} Tool contract exceeds Skill {skill_name}: {sorted(undeclared)}"
            )
        plans.append(AgentPlan(agent=agent, skill=skill_name, allowed_tools=allowed_tools, objective=objective))
    return plans


def validate_target_skill_contracts(registry: _SkillRegistry) -> None:
    """Validate all target and shared Skill bindings before serving traffic."""
    for agent, skill_name in TARGET_AGENT_SKILLS.items():
        decision = RoutingDecision(selected_agents=(agent,))
        build_target_agent_plans(decision, registry)
        skill = registry.get(skill_name)
        if not skill or not skill.references or not skill.scripts or not skill.quality_gate:
            raise RuntimeError(f"Target Agent {agent} requires references, scripts, and a quality gate")
    for node, skill_name in SHARED_NODE_SKILLS.items():
        skill = registry.get(skill_name)
        if not skill:
            raise RuntimeError(f"Target node {node} requires Skill {skill_name}")
