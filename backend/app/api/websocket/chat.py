from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import get_settings
from app.core.redaction import redact_text
from app.core.deps import websocket_user
from app.accounting.rate_limit import rate_limit_service
from app.db.models import GenerationState
from app.db.session import SessionLocal
from app.agent.chat import stream_chat
from app.agent.generation import generation_runtime

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

_connection_counts: dict[str, int] = {}
_connection_lock = asyncio.Lock()


async def _acquire_connection(user_id: str) -> tuple[str, bool] | None:
    connection_id = uuid.uuid4().hex
    if settings.redis_enabled:
        try:
            redis = await rate_limit_service.redis_client()
            key = f"paismart:ws:connections:{user_id}"
            now = time.time()
            ttl = max(60, settings.chat_connection_ttl_seconds)
            async with redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, now - ttl)
                pipe.zadd(key, {connection_id: now})
                pipe.zcard(key)
                pipe.expire(key, ttl)
                results = await pipe.execute()
            if int(results[2]) > max(1, settings.chat_max_connections_per_user):
                await redis.zrem(key, connection_id)
                return None
            return connection_id, True
        except Exception as exc:
            logger.warning("[WS] distributed connection limit unavailable: %s", exc)
            if settings.app_env.lower() in {"prod", "production"}:
                # Do not silently exceed a per-user limit when a production
                # worker cannot reach the shared counter.
                return None

    async with _connection_lock:
        current = _connection_counts.get(user_id, 0)
        if current >= max(1, settings.chat_max_connections_per_user):
            return None
        _connection_counts[user_id] = current + 1
        return connection_id, False


async def _touch_connection(user_id: str, connection: tuple[str, bool]) -> None:
    connection_id, distributed = connection
    if not distributed:
        return
    try:
        redis = await rate_limit_service.redis_client()
        key = f"paismart:ws:connections:{user_id}"
        ttl = max(60, settings.chat_connection_ttl_seconds)
        await redis.zadd(key, {connection_id: time.time()})
        await redis.expire(key, ttl)
    except Exception as exc:
        logger.warning("[WS] distributed connection heartbeat failed: %s", exc)


async def _release_connection(user_id: str, connection: tuple[str, bool]) -> None:
    connection_id, distributed = connection
    if distributed:
        try:
            redis = await rate_limit_service.redis_client()
            await redis.zrem(f"paismart:ws:connections:{user_id}", connection_id)
        except Exception as exc:
            logger.warning("[WS] distributed connection release failed: %s", exc)
        return
    async with _connection_lock:
        current = _connection_counts.get(user_id, 0) - 1
        if current > 0:
            _connection_counts[user_id] = current
        else:
            _connection_counts.pop(user_id, None)


def _gid(generation_id: str | None) -> str:
    return (generation_id or "-")[:8]


def _console(message: str) -> None:
    print(message, flush=True)


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
    logger.info("[WS] accepted client=%s", websocket.client)
    _console(f"[WS] accepted client={websocket.client}")
    user = await _authenticate_socket(websocket)
    if not user:
        logger.warning("[WS] authentication failed client=%s", websocket.client)
        _console(f"[WS] authentication failed client={websocket.client}")
        await websocket.close(code=1008, reason="unauthorized")
        return
    logger.info("[WS] authenticated user=%s role=%s", user.id, user.role)
    _console(f"[WS] authenticated user={user.id} role={user.role}")
    connection_state = await _acquire_connection(str(user.id))
    if connection_state is None:
        logger.warning("[WS] connection limit reached user=%s", user.id)
        await websocket.close(code=1013, reason="too many chat connections")
        return
    connection_acquired = True

    send_lock = asyncio.Lock()
    subscription_generation: str | None = None
    subscription_queue: asyncio.Queue | None = None
    pump_task: asyncio.Task | None = None

    async def socket_send(payload: dict) -> bool:
        try:
            async with send_lock:
                await websocket.send_json(payload)
            return True
        except Exception as exc:
            logger.warning("[WS] send failed type=%s error=%s", payload.get("type", "error"), exc)
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
        logger.info("[WS] subscribed generation=%s", _gid(generation_id))

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
            await _touch_connection(str(user.id), connection_state)
            _console(f"[WS] raw message received chars={len(text)}")
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
                logger.info("[WS] stop requested generation=%s", _gid(generation_id))
                if generation_id:
                    async with SessionLocal() as db:
                        state = await db.get(GenerationState, generation_id)
                        owned = state is not None and state.user_id == str(user.id)
                    if not owned:
                        await socket_send({"code": 404, "error": "未找到此生成任务"})
                        continue
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
            if len(question) > max(1, settings.chat_max_input_chars):
                await socket_send(
                    {
                        "code": 413,
                        "error": f"消息过长，最多支持 {settings.chat_max_input_chars} 个字符",
                    }
                )
                continue

            try:
                async with SessionLocal() as rate_limit_db:
                    await rate_limit_service.check(rate_limit_db, "chat", str(user.id))
            except HTTPException as exc:
                await socket_send({"code": exc.status_code, "error": str(exc.detail)})
                continue

            preview = redact_text(question[:80].replace("\n", " "))
            logger.info("[WS] question received chars=%d preview=%s", len(question), preview)
            _console(f"[WS] question received chars={len(question)} preview={preview}")

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
            logger.info("[WS] generation scheduled generation=%s", _gid(generation_id))
            _console(f"[WS] generation scheduled generation={_gid(generation_id)}")

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
        logger.info("[WS] disconnected user=%s generation=%s", user.id, _gid(subscription_generation))
    finally:
        await detach()
        if connection_acquired:
            await _release_connection(str(user.id), connection_state)
        logger.info("[WS] closed user=%s", user.id)
