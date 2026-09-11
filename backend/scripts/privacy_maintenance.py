"""Redact or purge old customer-service data.

This script is intentionally explicit: preview is the default, and mutations require
``--apply``. Schedule it outside the web process after reviewing the preview output.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import timedelta

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.redaction import redact_data, redact_text
from app.core.time import utcnow
from app.db.models import (
    AgentRun,
    ConversationMessage,
    GenerationState,
    SupportHandoff,
    ToolExecution,
)
from app.db.session import SessionLocal


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review and maintain retained support data")
    parser.add_argument("--apply", action="store_true", help="apply changes; otherwise only print counts")
    parser.add_argument("--redact-existing", action="store_true", help="redact credential-like content in retained rows")
    parser.add_argument("--purge-expired", action="store_true", help="delete rows older than configured retention windows")
    return parser.parse_args()


async def _redact(db, apply: bool) -> dict[str, int]:
    counts = {"conversationMessages": 0, "generationStates": 0, "agentRuns": 0, "toolExecutions": 0, "handoffs": 0}
    for row in (await db.scalars(select(ConversationMessage))).all():
        value = redact_text(row.content)
        if value != row.content:
            counts["conversationMessages"] += 1
            if apply:
                row.content = value
    for row in (await db.scalars(select(GenerationState))).all():
        question = redact_text(row.question)
        content = redact_text(row.content)
        error = redact_text(row.error) if row.error else row.error
        if (question, content, error) != (row.question, row.content, row.error):
            counts["generationStates"] += 1
            if apply:
                row.question, row.content, row.error = question, content, error
    for row in (await db.scalars(select(AgentRun))).all():
        question = redact_text(row.question)
        error = redact_text(row.error) if row.error else row.error
        trace = row.trace_json
        if trace:
            try:
                trace = json.dumps(redact_data(json.loads(trace)), ensure_ascii=False, default=str)
            except (TypeError, json.JSONDecodeError):
                trace = redact_text(trace)
        if (question, error, trace) != (row.question, row.error, row.trace_json):
            counts["agentRuns"] += 1
            if apply:
                row.question, row.error, row.trace_json = question, error, trace
    for row in (await db.scalars(select(ToolExecution))).all():
        arguments = row.arguments_json
        if arguments:
            try:
                arguments = json.dumps(redact_data(json.loads(arguments)), ensure_ascii=False, default=str)
            except (TypeError, json.JSONDecodeError):
                arguments = redact_text(arguments)
        error = redact_text(row.error) if row.error else row.error
        if (arguments, error) != (row.arguments_json, row.error):
            counts["toolExecutions"] += 1
            if apply:
                row.arguments_json, row.error = arguments, error
    for row in (await db.scalars(select(SupportHandoff))).all():
        reason, summary = redact_text(row.reason), redact_text(row.summary)
        if (reason, summary) != (row.reason, row.summary):
            counts["handoffs"] += 1
            if apply:
                row.reason, row.summary = reason, summary
    if apply:
        await db.commit()
    return counts


async def _purge(db, apply: bool) -> dict[str, int]:
    settings = get_settings()
    now = utcnow()
    history_cutoff = now - timedelta(days=max(1, settings.privacy_history_retention_days))
    trace_cutoff = now - timedelta(days=max(1, settings.privacy_trace_retention_days))
    targets = [
        ("conversationMessages", ConversationMessage, ConversationMessage.created_at < history_cutoff),
        ("generationStates", GenerationState, GenerationState.created_at < history_cutoff),
        ("agentRuns", AgentRun, AgentRun.started_at < trace_cutoff),
        ("toolExecutions", ToolExecution, ToolExecution.created_at < trace_cutoff),
    ]
    counts: dict[str, int] = {}
    for name, model, condition in targets:
        count = int(await db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
        counts[name] = count
        if apply and count:
            await db.execute(delete(model).where(condition))
    if apply:
        await db.commit()
    return counts


async def main() -> None:
    args = _args()
    if not args.redact_existing and not args.purge_expired:
        args.redact_existing = args.purge_expired = True
    async with SessionLocal() as db:
        if args.redact_existing:
            print("redaction:", await _redact(db, args.apply))
        if args.purge_expired:
            print("purge:", await _purge(db, args.apply))
    print("mode:", "APPLIED" if args.apply else "PREVIEW")


if __name__ == "__main__":
    asyncio.run(main())
