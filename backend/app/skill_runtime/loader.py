from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skill_runtime.models import SkillDefinition


class SkillLoadError(ValueError):
    pass


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            return int(value)
        except ValueError:
            return value.strip('"\'')


def parse_skill_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Parse the deliberately small SKILL.md front-matter subset used by PaiSmart.

    Values may be JSON literals (recommended for arrays) or plain scalar strings.
    Avoiding a YAML dependency keeps skill discovery available in minimal installs.
    """
    if not text.startswith("---\n"):
        raise SkillLoadError("SKILL.md must start with front matter delimited by ---")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SkillLoadError("SKILL.md front matter is not closed")
    header = text[4:end]
    body = text[end + 5 :].strip()
    metadata: dict[str, Any] = {}
    for line in header.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise SkillLoadError(f"Invalid front matter line: {line}")
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = _parse_scalar(value)
    return metadata, body


def _as_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SkillLoadError(f"{field_name} must be a string or string array")
    return tuple(item.strip() for item in value)


def load_skill(skill_dir: Path) -> SkillDefinition:
    file = skill_dir / "SKILL.md"
    if not file.is_file():
        raise SkillLoadError(f"Missing SKILL.md: {skill_dir}")
    metadata, body = parse_skill_markdown(file.read_text(encoding="utf-8"))
    name = str(metadata.get("name") or skill_dir.name).strip()
    description = str(metadata.get("description") or "").strip()
    if not name or not description:
        raise SkillLoadError(f"Skill {skill_dir.name} requires name and description")
    if name != skill_dir.name:
        raise SkillLoadError(f"Skill name must match directory name: {skill_dir.name}")
    if not body:
        raise SkillLoadError(f"Skill {name} has empty instructions")
    return SkillDefinition(
        name=name,
        description=description,
        root=skill_dir.resolve(),
        instructions=body,
        triggers=_as_string_tuple(metadata.get("triggers"), "triggers"),
        negative_triggers=_as_string_tuple(metadata.get("negative_triggers"), "negative_triggers"),
        allowed_tools=_as_string_tuple(metadata.get("allowed_tools"), "allowed_tools"),
        references=_as_string_tuple(metadata.get("references"), "references"),
        scripts=_as_string_tuple(metadata.get("scripts"), "scripts"),
        evals=_as_string_tuple(metadata.get("evals"), "evals"),
        quality_gate=str(metadata.get("quality_gate") or "").strip() or None,
        priority=int(metadata.get("priority") or 0),
        metadata=metadata,
    )
