from __future__ import annotations

from app.agent.graph.state import CustomerServiceState


def route_after_agent(state: CustomerServiceState) -> str:
    """Route an LLM decision to the next customer-service workflow stage."""

    action = str(state.get("next_action") or "safety")
    if action in {"execute_tools", "handoff", "force_finalize", "safety"}:
        return action
    return "safety"
