"""Durable approval-only refund graph. The checkpoint stores identifiers."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefundApprovalPreview


class RefundState(TypedDict, total=False):
    request_id: str
    decision_id: str
    outcome: str


def await_approval(state: RefundState) -> RefundState:
    return interrupt({"request_id": state["request_id"]})


async def advance(db: AsyncSession, request_id: str, checkpoint_path: Path) -> str:
    """Serialize graph advancement per business row and repair missing delivery."""
    await db.execute(
        update(RefundApprovalPreview)
        .where(RefundApprovalPreview.request_id == request_id)
        .values(updated_at=RefundApprovalPreview.updated_at)
    )
    row = await db.get(RefundApprovalPreview, request_id, populate_existing=True)
    if row is None:
        raise LookupError(request_id)

    async def resolve(state: RefundState) -> RefundState:
        if state["request_id"] != row.request_id or state.get("decision_id") != row.decision_id or not row.decision_id:
            raise ValueError("Invalid durable approval reference")
        return {"outcome": "APPROVED_PREVIEW" if row.decision == "approve" else "REJECTED"}

    graph = StateGraph(RefundState)
    graph.add_node("await_approval", await_approval)
    graph.add_node("resolve", resolve)
    graph.add_edge(START, "await_approval")
    graph.add_edge("await_approval", "resolve")
    graph.add_edge("resolve", END)
    config = {"configurable": {"thread_id": f"refund-preview:{request_id}"}}
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    # The persisted values are plain strings and mappings.
    serializer = JsonPlusSerializer(allowed_msgpack_modules=[])
    async with aiosqlite.connect(checkpoint_path) as connection:
        saver = AsyncSqliteSaver(connection, serde=serializer)
        workflow = graph.compile(checkpointer=saver)
        state = await workflow.aget_state(config)
        if not state.values:
            await workflow.ainvoke({"request_id": request_id}, config, durability="sync")
        elif state.next and not any(task.interrupts for task in state.tasks):
            await workflow.ainvoke(None, config, durability="sync")
        state = await workflow.aget_state(config)
        if row.decision_id and any(task.interrupts for task in state.tasks):
            await workflow.ainvoke(Command(resume={"decision_id": row.decision_id}), config, durability="sync")
            state = await workflow.aget_state(config)
        outcome = state.values.get("outcome", "PENDING_APPROVAL")
    await db.commit()
    return outcome
