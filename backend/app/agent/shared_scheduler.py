from __future__ import annotations

"""Shared, side-effect-free scheduler for target Agent Tool proposals.

It validates dependency batches before the target workflow executes Tools
through ``AgentRuntime``. Each selected Agent keeps ownership of every Tool
call it proposed; the scheduler never merges work across Agents.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from app.agent.dependencies import ToolDependencyAnalyzer
from app.agent.target_agents import TargetAgentWork
from app.agent.types import AgentToolCall, ToolBatch, tool_call_fingerprint
from app.core.redaction import redact_data


class _Tool(Protocol):
    read_only: bool


class _ToolRegistry(Protocol):
    def get(self, name: str) -> _Tool | None: ...


@dataclass(slots=True)
class ScheduledToolCall:
    call: AgentToolCall

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.call.id,
            "name": self.call.name,
            "arguments": redact_data(self.call.arguments),
            "sourceAgent": self.call.source_agent,
            "sourceSkill": self.call.source_skill,
        }


@dataclass(frozen=True, slots=True)
class ScheduledToolBatch:
    batch: ToolBatch
    calls: tuple[ScheduledToolCall, ...]

    def to_dict(self) -> dict[str, Any]:
        return {**self.batch.to_dict(), "calls": [call.to_dict() for call in self.calls]}


@dataclass(frozen=True, slots=True)
class SharedToolSchedule:
    agent_batches: tuple[tuple[str, ...], ...] = ()
    tool_batches: tuple[ScheduledToolBatch, ...] = ()
    deferred_calls: tuple[dict[str, Any], ...] = ()
    rejected_calls: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentBatches": [list(batch) for batch in self.agent_batches],
            "toolBatches": [batch.to_dict() for batch in self.tool_batches],
            "deferredCalls": list(self.deferred_calls),
            "rejectedCalls": list(self.rejected_calls),
        }


class SharedToolScheduler:
    """Plan the first globally safe Tool batch across specialist Agents."""

    def __init__(
        self,
        *,
        max_agents: int = 3,
        max_tools: int = 6,
        max_total_tools: int | None = None,
        dependency_analyzer: ToolDependencyAnalyzer | None = None,
    ) -> None:
        self.max_agents = max(1, max_agents)
        self.max_tools = max(1, max_tools)
        self.max_total_tools = max_total_tools if max_total_tools is None else max(0, max_total_tools)
        self.dependency_analyzer = dependency_analyzer or ToolDependencyAnalyzer()

    def plan(
        self,
        work: list[TargetAgentWork],
        *,
        registry: _ToolRegistry | None = None,
    ) -> SharedToolSchedule:
        """Create one or more initial read-only batches without executing them.

        Calls remain attributed to their proposing Agent, even when another
        Agent proposed an identical Tool and arguments. Calls depending on prior
        Tool outputs remain deferred until a subsequent scheduling pass receives
        actual results.
        """
        agent_names = [item.plan.agent for item in work]
        agent_batches = tuple(
            tuple(agent_names[index : index + self.max_agents])
            for index in range(0, len(agent_names), self.max_agents)
        )

        scheduled_calls: list[ScheduledToolCall] = []
        rejected: list[dict[str, Any]] = []
        seen_fingerprints: set[str] = set()
        for item in work:
            for call in item.proposed_calls:
                if call.name not in item.plan.allowed_tools:
                    rejected.append({"id": call.id, "tool": call.name, "reason": "agent_tool_contract"})
                    continue
                tool = registry.get(call.name) if registry is not None else None
                if tool is not None and not tool.read_only:
                    # The target architecture deliberately schedules handoff
                    # after evidence summary, never alongside read evidence.
                    rejected.append({"id": call.id, "tool": call.name, "reason": "write_tool_requires_handoff_node"})
                    continue
                fingerprint = tool_call_fingerprint(call)
                if fingerprint in seen_fingerprints:
                    rejected.append({"id": call.id, "tool": call.name, "reason": "duplicate_call_fingerprint"})
                    continue
                if self.max_total_tools is not None and len(scheduled_calls) >= self.max_total_tools:
                    rejected.append({"id": call.id, "tool": call.name, "reason": "tool_budget_exhausted"})
                    continue
                seen_fingerprints.add(fingerprint)
                scheduled_calls.append(ScheduledToolCall(call=call))

        calls = [entry.call for entry in scheduled_calls]
        ready, remaining, dependency_plan = self.dependency_analyzer.next_batch(calls, registry=registry)
        by_id = {entry.call.id: entry for entry in scheduled_calls}
        batches: list[ScheduledToolBatch] = []
        # Tool concurrency applies globally, across all Agent proposals. Split
        # independent calls deterministically; a later executor may run one
        # batch at a time without exceeding the configured budget.
        for index in range(0, len(ready), self.max_tools):
            batch_calls = ready[index : index + self.max_tools]
            batch_id = f"target-batch-{len(batches) + 1}"
            batches.append(
                ScheduledToolBatch(
                    batch=ToolBatch(
                        batch_id=batch_id,
                        agent="shared_tool_runtime",
                        tool_call_ids=tuple(call.id for call in batch_calls),
                    ),
                    calls=tuple(by_id[call.id] for call in batch_calls),
                )
            )

        deferred = [
            {
                "id": call.id,
                "tool": call.name,
                "sourceAgent": call.source_agent,
                "reason": dependency_plan.get("reason", "deferred"),
            }
            for call in remaining
        ]
        return SharedToolSchedule(
            agent_batches=agent_batches,
            tool_batches=tuple(batches),
            deferred_calls=tuple(deferred),
            rejected_calls=tuple(rejected),
        )


def shared_tool_scheduler(*, max_agents: int, max_tools: int, max_total_tools: int | None = None) -> SharedToolScheduler:
    """Create a request-local scheduler from the current runtime limits."""
    return SharedToolScheduler(max_agents=max_agents, max_tools=max_tools, max_total_tools=max_total_tools)
