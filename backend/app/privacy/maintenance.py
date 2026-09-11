from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.redaction import redact_data, redact_text
from app.db.models import AgentRun, ConversationMessage, GenerationState, SupportHandoff, ToolExecution
from app.db.session import SessionLocal


async def run_once() -> dict[str, dict[str, int]]:
    """Redact retained support data and purge rows beyond configured retention."""
    settings = get_settings()
    redacted = {"conversationMessages": 0, "generationStates": 0, "agentRuns": 0, "toolExecutions": 0, "handoffs": 0}
    purged: dict[str, int] = {}
    async with SessionLocal() as db:
        for row in (await db.scalars(select(ConversationMessage))).all():
            value = redact_text(row.content)
            if value != row.content:
                row.content = value
                redacted["conversationMessages"] += 1
        for row in (await db.scalars(select(GenerationState))).all():
            values = (redact_text(row.question), redact_text(row.content), redact_text(row.error) if row.error else row.error)
            if values != (row.question, row.content, row.error):
                row.question, row.content, row.error = values
                redacted["generationStates"] += 1
        for row in (await db.scalars(select(AgentRun))).all():
            trace = row.trace_json
            if trace:
                try:
                    trace = json.dumps(redact_data(json.loads(trace)), ensure_ascii=False, default=str)
                except (TypeError, json.JSONDecodeError):
                    trace = redact_text(trace)
            values = (redact_text(row.question), redact_text(row.error) if row.error else row.error, trace)
            if values != (row.question, row.error, row.trace_json):
                row.question, row.error, row.trace_json = values
                redacted["agentRuns"] += 1
        for row in (await db.scalars(select(ToolExecution))).all():
            arguments = row.arguments_json
            if arguments:
                try:
                    arguments = json.dumps(redact_data(json.loads(arguments)), ensure_ascii=False, default=str)
                except (TypeError, json.JSONDecodeError):
                    arguments = redact_text(arguments)
            error = redact_text(row.error) if row.error else row.error
            if (arguments, error) != (row.arguments_json, row.error):
                row.arguments_json, row.error = arguments, error
                redacted["toolExecutions"] += 1
        for row in (await db.scalars(select(SupportHandoff))).all():
            reason, summary = redact_text(row.reason), redact_text(row.summary)
            if (reason, summary) != (row.reason, row.summary):
                row.reason, row.summary = reason, summary
                redacted["handoffs"] += 1
        await db.commit()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        history_cutoff = now - timedelta(days=max(1, settings.privacy_history_retention_days))
        trace_cutoff = now - timedelta(days=max(1, settings.privacy_trace_retention_days))
        targets = [
            ("conversationMessages", ConversationMessage, ConversationMessage.created_at < history_cutoff),
            ("generationStates", GenerationState, GenerationState.created_at < history_cutoff),
            ("agentRuns", AgentRun, AgentRun.started_at < trace_cutoff),
            ("toolExecutions", ToolExecution, ToolExecution.created_at < trace_cutoff),
        ]
        for name, model, condition in targets:
            purged[name] = int(await db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
            if purged[name]:
                await db.execute(delete(model).where(condition))
        await db.commit()
    return {"redacted": redacted, "purged": purged}
