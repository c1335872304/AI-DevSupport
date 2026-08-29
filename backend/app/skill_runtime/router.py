from __future__ import annotations

import re

from app.core.config import get_settings
from app.skill_runtime.registry import SkillRegistry, skill_registry


class SkillRouter:
    """Deterministic high-precision pre-router.

    The baseline customer-support Skill is activated through ``default_active``.
    Specialist Skills require explicit trigger evidence; description words can only
    break ties. Negative triggers suppress unwanted escalation or troubleshooting,
    for example when a customer says the issue is already resolved.
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or skill_registry
        self.settings = get_settings()

    def score(self, question: str) -> list[dict]:
        if not self.settings.skills_enabled:
            return []
        text = re.sub(r"\s+", " ", question.strip().lower())
        if not text:
            return []
        rows: list[dict] = []
        for skill in self.registry.definitions():
            score = 0
            hits: list[str] = []
            negatives: list[str] = []
            for trigger in skill.triggers:
                token = trigger.strip().lower()
                if token and token in text:
                    score += 8 + min(len(token), 8)
                    hits.append(token)
            if skill.name.replace("-", " ") in text:
                score += 12
                hits.append(skill.name)
            for token in skill.negative_triggers:
                normalized = token.strip().lower()
                if normalized and normalized in text:
                    score -= 16
                    negatives.append(normalized)
            # Description terms can break ties, but cannot activate a skill by themselves.
            weak = 0
            for word in re.findall(r"[a-zA-Z]{4,}|[\u4e00-\u9fff]{2,}", skill.description.lower()):
                if word in text:
                    weak += 1
            if hits and score > 0:
                score += min(weak, 4)
            rows.append({
                "skill": skill.name,
                "score": score,
                "priority": skill.priority,
                "triggerHits": hits,
                "negativeHits": negatives,
            })
        rows.sort(key=lambda row: (row["score"], row["priority"], row["skill"]), reverse=True)
        return rows

    def route(self, question: str) -> list[str]:
        if not self.settings.skills_enabled:
            return []
        limit = max(1, self.settings.skills_max_active)
        defaults = [
            skill.name
            for skill in sorted(self.registry.definitions(), key=lambda item: item.priority, reverse=True)
            if bool(skill.metadata.get("default_active", False))
        ]
        ranked = self.score(question)
        # A single explicit trigger normally scores >=10. Requiring 8 prevents weak
        # description similarity from activating unrelated specialist workflows.
        specialists = [row["skill"] for row in ranked if row["score"] >= 8 and row["skill"] not in defaults]
        selected: list[str] = []
        for name in defaults + specialists:
            if name not in selected:
                selected.append(name)
            if len(selected) >= limit:
                break
        return selected


skill_router = SkillRouter()
