from __future__ import annotations

from collections.abc import Iterable

from app.agent.types import AgentToolCall


class ToolDependencyAnalyzer:
    """Build deterministic execution batches for specialist tool calls.

    The analyzer never invents calls and never grants permissions. It only separates
    calls that are safe to run now from calls that need a result produced by an earlier
    call. Explicit arguments can satisfy a dependency, e.g. an error-code lookup with
    a code already present in the conversation does not need a call-log lookup first.
    """

    _fallback_dependencies = {
        "query_api_key_status": "query_call_log",
        "query_error_code": "query_call_log",
        "query_recent_call_stats": "query_call_log",
    }

    @classmethod
    def _predecessors(cls, call: AgentToolCall, registry=None) -> list[str]:
        tool = registry.get(call.name) if registry is not None else None
        predecessors = list(getattr(tool, "dependencies", ()) or ())
        if not predecessors and call.name in cls._fallback_dependencies:
            predecessors = [cls._fallback_dependencies[call.name]]
        if call.name == "query_api_key_status" and (
            call.arguments.get("app_id") or call.arguments.get("api_key_id")
        ):
            return []
        if call.name == "query_error_code" and call.arguments.get("code"):
            return []
        if call.name == "query_recent_call_stats" and call.arguments.get("endpoint"):
            return []
        return predecessors

    def next_batch(
        self,
        calls: Iterable[AgentToolCall],
        completed_tools: set[str] | None = None,
        *,
        registry=None,
    ) -> tuple[list[AgentToolCall], list[AgentToolCall], dict]:
        pending = list(calls)
        completed = set(completed_tools or set())
        if not pending:
            return [], [], {"batches": [], "reason": "empty"}

        dependency_edges = [
            {"tool": call.name, "dependsOn": predecessor}
            for call in pending
            for predecessor in self._predecessors(call, registry)
        ]

        # A write-like handoff is a safety barrier: do not run unrelated specialist
        # work in the same batch before the handoff outcome is known.
        handoffs = [call for call in pending if call.name == "create_support_handoff"]
        if handoffs:
            batch = handoffs[:1]
            remaining = [call for call in pending if call not in batch]
            return batch, remaining, {
                "batches": [[call.name for call in batch]],
                "barrier": "handoff",
                "dependencies": dependency_edges,
            }

        pending_names = {call.name for call in pending}
        ready: list[AgentToolCall] = []
        blocked: list[AgentToolCall] = []
        missing: list[dict[str, str]] = []
        for call in pending:
            predecessors = self._predecessors(call, registry)
            absent = [item for item in predecessors if item not in pending_names and item not in completed]
            if absent:
                blocked.append(call)
                missing.extend({"tool": call.name, "dependsOn": item} for item in absent)
                continue
            if any(item in pending_names and item not in completed for item in predecessors):
                blocked.append(call)
            else:
                ready.append(call)
        if not ready:
            if missing:
                return [], pending, {
                    "batches": [],
                    "blocked": [call.name for call in blocked],
                    "missingDependencies": missing,
                    "reason": "missing_dependency",
                    "dependencies": dependency_edges,
                }
            # Defensive cycle breaker. A malformed model plan must not deadlock the
            # conversation; executing one call lets the next turn recover from results.
            ready = pending[:1]
            blocked = pending[1:]
            reason = "cycle_breaker"
        else:
            reason = "dependency_ready"
        return ready, blocked, {
            "batches": [[call.name for call in ready]],
            "blocked": [call.name for call in blocked],
            "reason": reason,
            "dependencies": dependency_edges,
        }


tool_dependency_analyzer = ToolDependencyAnalyzer()
