from __future__ import annotations

import json
from app.core.config import get_settings
from app.core.redaction import redact_data, redact_text
from app.core.time import utcnow


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
                        question=redact_text(question), status="RUNNING",
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
                    arguments_json=json.dumps(redact_data(arguments), ensure_ascii=False, default=str)[:12000],
                    error=redact_text(result.error or "")[:2000] or None,
                ))
                await db.commit()
        except Exception:
            return

    async def checkpoint(self, generation_id: str, active_skills: list[str], trace: dict) -> None:
        """Persist the latest trace while a generation is still running.

        ToolExecution rows remain the durable low-level audit. This snapshot makes
        routing, specialist decisions and dependency state available when a later
        provider/tool failure prevents the normal completion path.
        """
        if not self.settings.agent_trace_persist_enabled:
            return
        try:
            from app.db.models import AgentRun
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                row = await db.get(AgentRun, generation_id)
                if row:
                    row.active_skills_json = json.dumps(active_skills, ensure_ascii=False)
                    row.trace_json = json.dumps(redact_data(trace), ensure_ascii=False, default=str)
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
                    row.trace_json = json.dumps(redact_data(trace), ensure_ascii=False, default=str)
                    row.completed_at = utcnow()
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
                    row.error = redact_text(reason)[:2000]
                    if row.trace_json:
                        try:
                            snapshot = json.loads(row.trace_json)
                        except (TypeError, json.JSONDecodeError):
                            snapshot = {}
                        snapshot["terminalStatus"] = "CANCELLED"
                        snapshot["terminalError"] = redact_text(reason)[:2000]
                        row.trace_json = json.dumps(snapshot, ensure_ascii=False, default=str)
                    row.completed_at = utcnow()
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
                    row.error = redact_text(error)[:2000]
                    if row.trace_json:
                        try:
                            snapshot = json.loads(row.trace_json)
                        except (TypeError, json.JSONDecodeError):
                            snapshot = {}
                        snapshot["terminalStatus"] = "FAILED"
                        snapshot["terminalError"] = redact_text(error)[:2000]
                        row.trace_json = json.dumps(snapshot, ensure_ascii=False, default=str)
                    row.completed_at = utcnow()
                    await db.commit()
        except Exception:
            return


trace_store = TraceStore()
