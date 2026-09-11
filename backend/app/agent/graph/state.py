from __future__ import annotations

from typing import Any, TypedDict

from app.agent.types import AgentToolCall
from app.skill_runtime.trace import SkillTrace


class CustomerServiceState(TypedDict, total=False):
    """Shared state carried across the LangGraph customer-service workflow."""

    # Request/context
    question: str
    history: list[dict]
    conversation_id: str
    generation_id: str

    # Prompt / skills
    active_skills: list[str]
    skill_trace: SkillTrace
    intent_classification: dict[str, Any]
    entity_memory: dict[str, str]
    entities: dict[str, str]
    entity_sources: dict[str, str]
    retrieval_query: str
    query_optimization: dict[str, Any]

    # Agent turn
    step: int
    max_steps: int
    tool_calls: list[AgentToolCall]
    next_action: str

    # Results
    references: dict[str, dict]
    content_parts: list[str]
    draft_answer: str
    final_answer: str
    final_chunks: list[str]

    # Customer-service control
    handoff_attempted: bool
    handoff_success: bool
    handoff_id: str | None
    quality_gate_results: dict[str, dict[str, Any]]
    quality_gate_blocked: bool
    quality_gate_action: str

    # Target-architecture contracts carried across the authoritative workflow.
    routing_decision: dict[str, Any]
    agent_plans: list[dict[str, Any]]
    tool_batches: list[dict[str, Any]]
    agent_evidence: list[dict[str, Any]]
    evidence_summary: dict[str, Any]
    handoff_result: dict[str, Any]
    billing_mcp_catalog: list[dict[str, Any]]
    target_tool_outcomes: list[tuple[AgentToolCall, Any]]
    target_scheduled_batches: list[dict[str, Any]]
    executed_tool_fingerprints: list[str]
    executed_tool_call_count: int

    # Observability
    graph_path: list[str]
    workflow_engine: str
    trace_summary: dict[str, Any]
