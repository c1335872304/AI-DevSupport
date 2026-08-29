from __future__ import annotations

import os

try:  # Normal runtime: use the real LangGraph package.
    from langgraph.graph import END, START, StateGraph  # type: ignore

    LANGGRAPH_ENGINE = "langgraph"
    LANGGRAPH_AVAILABLE = True
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only in stripped environments
    if os.getenv("APP_ENV", "development").strip().lower() in {"prod", "production"}:
        raise RuntimeError(
            "LangGraph is required in production. Install backend dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc
    from app.agent.graph.compat import END, START, StateGraph

    LANGGRAPH_ENGINE = "compat-dev"
    LANGGRAPH_AVAILABLE = False

__all__ = ["StateGraph", "START", "END", "LANGGRAPH_ENGINE", "LANGGRAPH_AVAILABLE"]
