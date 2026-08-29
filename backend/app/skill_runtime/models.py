from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SkillDefinition:
    name: str
    description: str
    root: Path
    instructions: str
    triggers: tuple[str, ...] = ()
    negative_triggers: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    scripts: tuple[str, ...] = ()
    evals: tuple[str, ...] = ()
    quality_gate: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def catalog_item(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "triggers": list(self.triggers),
            "negativeTriggers": list(self.negative_triggers),
            "references": list(self.references),
            "scripts": list(self.scripts),
            "evals": list(self.evals),
            "qualityGate": self.quality_gate,
            "defaultActive": bool(self.metadata.get("default_active", False)),
        }

    def prompt_block(self, max_chars: int) -> str:
        body = self.instructions.strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n...<skill instructions truncated>"
        refs = ", ".join(self.references) if self.references else "无"
        scripts = ", ".join(self.scripts) if self.scripts else "无"
        return (
            f"### Skill: {self.name}\n"
            f"用途：{self.description}\n"
            f"可按需读取 references：{refs}\n"
            f"可按需运行 scripts：{scripts}\n\n"
            f"{body}"
        )
