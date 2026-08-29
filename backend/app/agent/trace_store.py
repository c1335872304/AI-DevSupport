from __future__ import annotations

import json
from datetime import datetime

from app.core.config import get_settings


class TraceStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def begin(self, generation_id: str, user_id: str, question: str, active_skills: list[str]) -> None:
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import AgentRun
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                row = await db.get(AgentRun, generation_id)
                if not row:
                    db.add(AgentRun(
                        run_id=generation_id, generation_id=generation_id, user_id=user_id,
                        question=question, status="RUNNING",
                        active_skills_json=json.dumps(active_skills, ensure_ascii=False),
                    ))
                await db.commit()
        except Exception:
            # Observability must never become an availability dependency.
            return

    async def tool(self, generation_id: str, call_id: str, name: str, step: int, arguments: dict, result) -> None:
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import ToolExecution
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                db.add(ToolExecution(
                    run_id=generation_id, generation_id=generation_id, tool_call_id=call_id,
                    tool_name=name, step=step, status=result.status, duration_ms=result.duration_ms,
                    arguments_json=json.dumps(arguments, ensure_ascii=False, default=str)[:12000],
                    error=(result.error or "")[:2000] or None,
                ))
                await db.commit()
        except Exception:
            return

    async def complete(self, generation_id: str, active_skills: list[str], trace: dict) -> None:
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import AgentRun
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                row = await db.get(AgentRun, generation_id)
                if row:
                    row.status = "COMPLETED"
                    row.active_skills_json = json.dumps(active_skills, ensure_ascii=False)
                    row.trace_json = json.dumps(trace, ensure_ascii=False, default=str)
                    row.completed_at = datetime.utcnow()
                    await db.commit()
        except Exception:
            return

    async def cancel(self, generation_id: str, reason: str = "Generation cancelled") -> None:
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import AgentRun
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                row = await db.get(AgentRun, generation_id)
                if row:
                    row.status = "CANCELLED"
                    row.error = reason[:2000]
                    row.completed_at = datetime.utcnow()
                    await db.commit()
        except Exception:
            return

    async def fail(self, generation_id: str, error: str) -> None:
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import AgentRun
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                row = await db.get(AgentRun, generation_id)
                if row:
                    row.status = "FAILED"
                    row.error = error[:2000]
                    row.completed_at = datetime.utcnow()
                    await db.commit()
        except Exception:
            return


trace_store = TraceStore()
