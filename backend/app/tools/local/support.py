from __future__ import annotations

from app.support.handoff import create_handoff, get_user_handoff, serialize_handoff
from app.support.handoff_contract import HANDOFF_CREATE, HANDOFF_INPUT_SCHEMA
from app.tools.base import BaseTool, ToolExecutionContext


class CreateSupportHandoffTool(BaseTool):
    name = HANDOFF_CREATE
    description = (
        "Create a real human-support handoff ticket for the current authenticated customer. "
        "Use only when the customer requests human support or the AI cannot safely continue."
    )
    input_schema = HANDOFF_INPUT_SCHEMA
    parallel_safe = False
    read_only = False
    idempotent = False
    resource_group = "support-handoff"
    risk_level = "medium"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        from app.db.session import SessionLocal
        async with SessionLocal() as db:
            row = await create_handoff(
                db,
                context.user,
                generation_id=context.generation_id,
                diagnosis_lease=context.diagnosis_lease,
                authorization=context.handoff_authorization,
                reason=str(arguments.get("reason") or ""),
                summary=str(arguments.get("summary") or ""),
                category=str(arguments.get("category") or "GENERAL"),
                priority=str(arguments.get("priority") or "NORMAL"),
            )
        return serialize_handoff(row)


class GetSupportHandoffTool(BaseTool):
    name = "get_support_handoff"
    description = "Get the current customer's latest human-support handoff, or a specific handoff by id."
    input_schema = {
        "type": "object",
        "properties": {
            "handoff_id": {"type": "string", "minLength": 3, "maxLength": 64},
        },
        "additionalProperties": False,
    }
    resource_group = "support-handoff-read"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        from app.db.session import SessionLocal
        handoff_id = str(arguments.get("handoff_id") or "").strip() or None
        async with SessionLocal() as db:
            row = await get_user_handoff(db, context.user, handoff_id)
        if not row:
            return {"found": False, "handoff": None}
        return {"found": True, "handoff": serialize_handoff(row)}
