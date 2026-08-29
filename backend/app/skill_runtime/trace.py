from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SkillTrace:
    question: str
    initial_skills: list[str] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    activations: list[str] = field(default_factory=list)
    deactivations: list[dict[str, str]] = field(default_factory=list)
    tool_batches: list[dict[str, Any]] = field(default_factory=list)

    def activate(self, skill: str, *, dynamic: bool = False) -> None:
        if skill not in self.active_skills:
            self.active_skills.append(skill)
        if dynamic and skill not in self.activations:
            self.activations.append(skill)

    def deactivate(self, skill: str, *, reason: str = "") -> None:
        if skill in self.active_skills:
            self.active_skills.remove(skill)
        self.deactivations.append({"skill": skill, "reason": reason})

    def record_batch(self, step: int, calls: list[Any], results: list[Any]) -> None:
        items = []
        for call, result in zip(calls, results, strict=True):
            entry: dict[str, Any] = {
                "tool": call.name,
                "status": result.status,
                "durationMs": result.duration_ms,
            }
            if call.name == "run_skill_script":
                entry["skill"] = call.arguments.get("skill")
                entry["script"] = call.arguments.get("script")
            elif call.name == "read_skill_reference":
                entry["skill"] = call.arguments.get("skill")
                entry["reference"] = call.arguments.get("reference")
            elif call.name == "activate_skill":
                entry["skill"] = call.arguments.get("skill")
            items.append(entry)
        self.tool_batches.append({"step": step + 1, "calls": items})

    def summary(self) -> dict[str, Any]:
        flattened = [item for batch in self.tool_batches for item in batch["calls"]]
        tool_counts: dict[str, int] = {}
        scripts: list[str] = []
        references: list[str] = []
        failures = 0
        for item in flattened:
            tool = str(item.get("tool") or "")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            if item.get("status") != "SUCCESS":
                failures += 1
            script = item.get("script")
            if script and script not in scripts:
                scripts.append(str(script))
            reference = item.get("reference")
            if reference and reference not in references:
                references.append(str(reference))
        return {
            "question": self.question,
            "initialSkills": list(self.initial_skills),
            "activeSkills": list(self.active_skills),
            "dynamicActivations": list(self.activations),
            "dynamicDeactivations": list(self.deactivations),
            "toolBatches": self.tool_batches,
            "toolCounts": tool_counts,
            "scriptsUsed": scripts,
            "referencesRead": references,
            "stepsUsed": len(self.tool_batches),
            "totalToolCalls": len(flattened),
            "maxParallelWidth": max((len(batch["calls"]) for batch in self.tool_batches), default=0),
            "failedToolCalls": failures,
        }
