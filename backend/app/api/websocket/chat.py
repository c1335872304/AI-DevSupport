from __future__ import annotations

import asyncio
import json
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import websocket_user
from app.db.models import GenerationState
from app.db.session import SessionLocal
from app.agent.chat import stream_chat
from app.agent.generation import generation_runtime

router = APIRouter()
settings = get_settings()


async def _authenticate_socket(websocket: WebSocket):
    timeout = max(1.0, settings.websocket_auth_timeout_seconds)
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=remaining)
        except (asyncio.TimeoutError, WebSocketDisconnect):
            return None
        if raw == "__chat_ping__":
            await websocket.send_text("__chat_pong__")
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict) or payload.get("type") != "auth":
            return None
        token = str(payload.get("token") or "").strip()
        if not token:
            return None
        async with SessionLocal() as auth_db:
            return await websocket_user(websocket, token, auth_db)


@router.websocket("/chat")
async def chat_socket(websocket: WebSocket):
    await websocket.accept()
    user = await _authenticate_socket(websocket)
    if not user:
        await websocket.close(code=1008, reason="unauthorized")
        return

    send_lock = asyncio.Lock()
    subscription_generation: str | None = None
    subscription_queue: asyncio.Queue | None = None
    pump_task: asyncio.Task | None = None

    async def socket_send(payload: dict) -> bool:
        try:
            async with send_lock:
                await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def detach() -> None:
        nonlocal subscription_generation, subscription_queue, pump_task
        if subscription_generation:
            generation_runtime.unsubscribe(subscription_generation, subscription_queue)
        if pump_task and not pump_task.done():
            pump_task.cancel()
            try:
                await pump_task
            except asyncio.CancelledError:
                pass
        subscription_generation = None
        subscription_queue = None
        pump_task = None

    async def attach(generation_id: str) -> None:
        nonlocal subscription_generation, subscription_queue, pump_task
        await detach()
        subscription_generation = generation_id
        subscription_queue = generation_runtime.subscribe(generation_id)

        async def pump() -> None:
            assert subscription_queue is not None
            while True:
                payload = await subscription_queue.get()
                if not await socket_send(payload):
                    return

        pump_task = asyncio.create_task(pump(), name=f"ws-pump:{generation_id}")

    await socket_send({"type": "connection", "sessionId": uuid.uuid4().hex})

    # Reattach to a generation that survived a previous socket disconnect. The DB
    # snapshot contains past content; this subscription delivers only future events.
    async with SessionLocal() as db:
        active = await db.scalar(
            select(GenerationState)
            .where(GenerationState.user_id == str(user.id), GenerationState.status.in_(["PENDING", "STREAMING"]))
            .order_by(GenerationState.updated_at.desc())
        )
    if active:
        await attach(active.generation_id)
        await socket_send({
            "type": "resume", "generationId": active.generation_id,
            "conversationId": active.conversation_id, "content": active.content,
            "status": active.status,
        })

    try:
        while True:
            text = await websocket.receive_text()
            if text == "__chat_ping__":
                async with send_lock:
                    await websocket.send_text("__chat_pong__")
                continue

            payload = None
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                pass

            if isinstance(payload, dict) and payload.get("type") == "stop":
                generation_id = str(payload.get("generationId") or subscription_generation or "").strip()
                if generation_id:
                    await generation_runtime.cancel(generation_id)
                    async with SessionLocal() as db:
                        state = await db.get(GenerationState, generation_id)
                        if state and state.user_id == str(user.id) and state.status in {"PENDING", "STREAMING"}:
                            state.status = "CANCELLED"
                            await db.commit()
                await socket_send({"type": "stop", "generationId": generation_id or None})
                continue

            question = text.strip()
            if not question:
                continue

            if subscription_generation and generation_runtime.is_running(subscription_generation):
                await socket_send({"code": 409, "error": "上一轮回答仍在生成中", "generationId": subscription_generation})
                continue

            async with SessionLocal() as db:
                existing = await db.scalar(
                    select(GenerationState)
                    .where(GenerationState.user_id == str(user.id), GenerationState.status.in_(["PENDING", "STREAMING"]))
                    .order_by(GenerationState.updated_at.desc())
                )
            if existing:
                await socket_send({"code": 409, "error": "上一轮回答仍在生成中", "generationId": existing.generation_id})
                continue

            generation_id = uuid.uuid4().hex
            await attach(generation_id)

            async def run_generation(gid: str = generation_id, q: str = question) -> None:
                async with SessionLocal() as db:
                    await stream_chat(
                        db, user, q,
                        lambda event: generation_runtime.publish(gid, event),
                        generation_id=gid,
                    )

            await generation_runtime.start(generation_id, run_generation)
    except WebSocketDisconnect:
        # Only the subscription disappears. The generation task remains owned by the
        # GenerationRuntime and keeps checkpointing into GenerationState.
        pass
    finally:
        await detach()
