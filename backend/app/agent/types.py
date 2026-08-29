from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AgentToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
