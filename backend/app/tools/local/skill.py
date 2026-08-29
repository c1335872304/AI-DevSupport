from __future__ import annotations

from app.core.config import get_settings
from app.skill_runtime.registry import skill_registry
from app.tools.base import BaseTool, ToolExecutionContext


def _require_active(context: ToolExecutionContext, skill: str) -> None:
    if skill not in context.active_skills:
        raise PermissionError(f"Skill is not active for this request: {skill}")


class ActivateSkillTool(BaseTool):
    name = "activate_skill"
    description = (
        "Activate one PaiSmart Skill from the Skill Catalog when its workflow is useful. "
        "Activation changes guidance only; it never grants additional data permissions."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Skill name exactly as shown in the catalog."},
        },
        "required": ["skill"],
        "additionalProperties": False,
    }
    resource_group = "skill-state"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        skill_name = str(arguments.get("skill") or "").strip()
        skill = skill_registry.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")
        settings = get_settings()
        replace_skill: str | None = None
        if skill_name not in context.active_skills and len(context.active_skills) >= max(1, settings.skills_max_active):
            # Keep the default customer-service baseline and allow a higher-priority
            # specialist (for example escalation) to replace the current specialist.
            replaceable = []
            for active_name in context.active_skills:
                active = skill_registry.get(active_name)
                if active and not bool(active.metadata.get("default_active", False)):
                    replaceable.append(active)
            replaceable.sort(key=lambda item: (item.priority, item.name))
            if not replaceable or skill.priority <= replaceable[0].priority:
                raise PermissionError("maximum active skill count reached")
            replace_skill = replaceable[0].name
        payload = {
            "skill": skill.name,
            "description": skill.description,
            "references": list(skill.references),
            "scripts": list(skill.scripts),
            "allowedTools": list(skill.allowed_tools),
        }
        if replace_skill:
            payload["replaceSkill"] = replace_skill
        return payload


class ReadSkillReferenceTool(BaseTool):
    name = "read_skill_reference"
    description = (
        "Read one reference explicitly declared by an active PaiSmart Skill. "
        "Use only when the active SKILL.md says the detailed reference is needed."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Active skill name."},
            "reference": {"type": "string", "description": "Declared reference path, e.g. references/citation-rules.md."},
        },
        "required": ["skill", "reference"],
        "additionalProperties": False,
    }
    resource_group = "skill-read"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        skill = str(arguments.get("skill") or "").strip()
        reference = str(arguments.get("reference") or "").strip()
        _require_active(context, skill)
        content = skill_registry.read_reference(skill, reference)
        return {"skill": skill, "reference": reference, "content": content}


class RunSkillScriptTool(BaseTool):
    name = "run_skill_script"
    description = (
        "Run one trusted deterministic script declared by an active PaiSmart Skill. "
        "Scripts are repository-owned, execute without a shell, and receive only JSON arguments."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Active skill name."},
            "script": {"type": "string", "description": "Declared script name without .py."},
            "arguments": {"type": "object", "description": "JSON arguments expected by that script."},
        },
        "required": ["skill", "script", "arguments"],
        "additionalProperties": False,
    }
    parallel_safe = True
    read_only = True
    idempotent = True
    resource_group = "skill-script"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        skill = str(arguments.get("skill") or "").strip()
        script = str(arguments.get("script") or "").strip()
        payload = arguments.get("arguments")
        if not isinstance(payload, dict):
            raise ValueError("arguments must be an object")
        _require_active(context, skill)
        return await skill_registry.run_script(skill, script, payload)
