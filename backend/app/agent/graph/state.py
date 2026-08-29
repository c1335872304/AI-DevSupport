from __future__ import annotations

from typing import Any, TypedDict

from app.agent.types import AgentToolCall
from app.skill_runtime.trace import SkillTrace


class CustomerServiceState(TypedDict, total=False):
    """Shared state carried across the LangGraph customer-service workflow."""

    # Request/context
    question: str
    history: list[dict]
    generation_id: str

    # Prompt / skills
    messages: list[dict]
    active_skills: list[str]
    skill_catalog: str
    skill_trace: SkillTrace

    # Agent turn
    step: int
    max_steps: int
    tool_calls: list[AgentToolCall]
    turn_chunks: list[str]
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

    # Observability
    graph_path: list[str]
    workflow_engine: str
    trace_summary: dict[str, Any]
