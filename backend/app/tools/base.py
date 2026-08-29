from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.db.models import User


@dataclass(slots=True)
class ToolExecutionContext:
    user: User
    generation_id: str | None = None
    active_skills: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=lambda: frozenset({"*"}))
    source: str = "agent"


@dataclass(slots=True)
class ToolResult:
    status: str
    data: Any = None
    error: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "data": self.data,
        }
        if self.error:
            payload["error"] = self.error
        if self.duration_ms is not None:
            payload["durationMs"] = self.duration_ms
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


class BaseTool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any]
    timeout_seconds: float | None = None
    parallel_safe: bool = True
    read_only: bool = True
    idempotent: bool = True
    resource_group: str | None = None
    allowed_roles: frozenset[str] = frozenset()
    required_scopes: frozenset[str] = frozenset()
    risk_level: str = "low"

    def as_llm_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    @abstractmethod
    async def execute(self, context: ToolExecutionContext, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError
