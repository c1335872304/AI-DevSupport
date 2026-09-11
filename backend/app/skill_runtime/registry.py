from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Iterable

from app.core.config import get_settings
from app.skill_runtime.loader import SkillLoadError, load_skill
from app.skill_runtime.models import SkillDefinition


class SkillRegistry:
    def __init__(self, skills: Iterable[SkillDefinition] | None = None, root: Path | None = None) -> None:
        self.settings = get_settings()
        self.root = (root or self.settings.skills_path).resolve()
        self._skills: dict[str, SkillDefinition] = {}
        for skill in skills or []:
            self.register(skill)

    @classmethod
    def discover(cls, root: Path | None = None) -> "SkillRegistry":
        registry = cls(root=root)
        if not registry.root.exists():
            return registry
        for child in sorted(registry.root.iterdir()):
            if not child.is_dir() or not (child / "SKILL.md").is_file():
                continue
            try:
                registry.register(load_skill(child))
            except SkillLoadError:
                # One malformed optional skill must not prevent the application from starting.
                continue
        return registry

    def register(self, skill: SkillDefinition) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Duplicate skill: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def names(self) -> list[str]:
        return list(self._skills)

    def definitions(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def catalog(self) -> list[dict]:
        return [skill.catalog_item() for skill in self._skills.values()]

    def catalog_prompt(self) -> str:
        if not self._skills:
            return ""
        lines = ["可用 Skill Catalog（仅名称和用途；需要时调用 activate_skill）："]
        for skill in self._skills.values():
            lines.append(f"- {skill.name}: {skill.description}")
        return "\n".join(lines)

    def build_prompt(self, names: Iterable[str]) -> str:
        blocks: list[str] = []
        remaining = max(1000, self.settings.skills_max_instruction_chars)
        for name in names:
            skill = self.get(name)
            if not skill or remaining <= 0:
                continue
            block = skill.prompt_block(remaining)
            blocks.append(block)
            remaining -= len(block)
        return "\n\n".join(blocks)

    def _safe_declared_path(self, skill_name: str, relative_path: str, *, allowed: tuple[str, ...]) -> Path:
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")
        if relative_path not in allowed:
            raise PermissionError(f"Resource is not declared by active skill: {relative_path}")
        candidate = (skill.root / relative_path).resolve()
        if skill.root != candidate and skill.root not in candidate.parents:
            raise PermissionError("Skill path escapes its directory")
        if not candidate.is_file():
            raise FileNotFoundError(relative_path)
        return candidate

    def read_reference(self, skill_name: str, reference: str) -> str:
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")
        path = self._safe_declared_path(skill_name, reference, allowed=skill.references)
        text = path.read_text(encoding="utf-8")
        limit = max(1000, self.settings.skills_reference_max_chars)
        return text if len(text) <= limit else text[:limit] + "\n...<reference truncated>"

    async def run_script(self, skill_name: str, script: str, arguments: dict) -> dict:
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")
        relative = f"scripts/{script}.py"
        allowed_paths = tuple(f"scripts/{name}.py" for name in skill.scripts)
        path = self._safe_declared_path(skill_name, relative, allowed=allowed_paths)

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(skill.root),
            env={"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "PATH": os.environ.get("PATH", "")},
        )
        payload_text = json.dumps(arguments or {}, ensure_ascii=False)
        if len(payload_text) > self.settings.skills_script_input_max_chars:
            process.kill()
            await process.wait()
            raise ValueError("skill script input exceeds configured limit")
        payload = payload_text.encode("utf-8")
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(payload),
                timeout=max(0.1, self.settings.skills_script_timeout_seconds),
            )
        except asyncio.TimeoutError as exc:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            # Drain stdout/stderr after killing the child. This closes the
            # Proactor pipe transports cleanly on Windows as well as POSIX.
            await process.communicate()
            raise TimeoutError(
                f"skill script timed out after {self.settings.skills_script_timeout_seconds:g}s"
            ) from exc
        except BaseException:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace").strip() or f"script exited {process.returncode}"
            raise RuntimeError(error[:2000])
        raw = stdout.decode("utf-8", errors="replace").strip()
        if len(raw) > self.settings.skills_script_output_max_chars:
            raise RuntimeError("skill script output exceeds configured limit")
        try:
            result = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("skill script must print one JSON value") from exc
        return result if isinstance(result, dict) else {"result": result}


skill_registry = SkillRegistry.discover()
