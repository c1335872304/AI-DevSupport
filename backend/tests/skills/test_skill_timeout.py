import asyncio

import pytest

from app.skill_runtime.models import SkillDefinition
from app.skill_runtime.registry import SkillRegistry


@pytest.mark.asyncio
async def test_skill_script_timeout_kills_hanging_process(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "sleep.py"
    script.write_text("import time\ntime.sleep(1)\nprint('{}')\n", encoding="utf-8")
    skill = SkillDefinition(
        name="timeout-test",
        description="timeout test",
        root=tmp_path,
        instructions="timeout test",
        scripts=("sleep",),
    )
    registry = SkillRegistry([skill], root=tmp_path)
    registry.settings.skills_script_timeout_seconds = 0.05

    with pytest.raises(TimeoutError, match="timed out"):
        await asyncio.wait_for(registry.run_script("timeout-test", "sleep", {}), timeout=1)
