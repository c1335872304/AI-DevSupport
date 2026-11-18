from __future__ import annotations

import asyncio
import logging
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import timedelta

from app.core.time import utcnow

logger = logging.getLogger(__name__)
HEARTBEAT_INTERVAL_SECONDS = 10
GENERATION_LEASE_SECONDS = 120


class GenerationRuntime:
    """Owner of detached tasks, with shared Redis streams and SQL snapshot fallback.

    Durable recovery still comes from GenerationState checkpoints in the database. This
    local task lifetime is independent of the socket. Redis carries checked events and
    cross-replica cancellation; bounded streams expire after two hours.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._listeners: dict[asyncio.Queue, asyncio.Task] = {}
        self._content: dict[str, str] = {}
        self._watchers: set[asyncio.Task] = set()

    @staticmethod
    async def _redis():
        from app.accounting.rate_limit import rate_limit_service
        return await rate_limit_service.redis_client()

    @staticmethod
    def _distributed():
        from app.core.config import get_settings
        return get_settings().redis_enabled

    async def subscribe_shared(self, generation_id: str):
        if not self._distributed():
            return self.subscribe(generation_id), None
        redis = await self._redis()
        key = f'paismart:generation:events:{generation_id}'
        try:
            latest = await redis.xrevrange(key, count=1)
        except Exception:
            logger.exception('Shared subscription unavailable; using SQL snapshot fallback')
            return self.subscribe(generation_id), None
        cursor = latest[0][0] if latest else '0-0'
        snapshot = json.loads(latest[0][1]['payload']) if latest else None
        queue = asyncio.Queue(maxsize=256)

        async def listen():
            nonlocal cursor
            while True:
                try:
                    streams = await redis.xread({key: cursor}, count=128, block=1000)
                    for _, events in streams:
                        for event_id, fields in events:
                            payload = json.loads(fields['payload'])
                            payload['eventId'] = event_id
                            if queue.full():
                                queue.get_nowait()
                            queue.put_nowait(payload)
                            cursor = event_id
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception('Shared generation stream temporarily unavailable')
                    await asyncio.sleep(1)
        self._listeners[queue] = asyncio.create_task(listen(), name=f'generation-events:{generation_id}')
        return queue, snapshot

    async def start(self, generation_id: str, factory: Callable[[], Awaitable[None]]) -> asyncio.Task:
        async with self._lock:
            existing = self._tasks.get(generation_id)
            if existing and not existing.done():
                return existing
            task = asyncio.create_task(factory(), name=f"generation:{generation_id}")
            self._tasks[generation_id] = task
            task.add_done_callback(lambda _: asyncio.create_task(self._forget_task(generation_id)))
            if self._distributed():
                async def watch_cancel():
                    while not task.done():
                        try:
                            redis = await self._redis()
                            if await redis.get(f'paismart:generation:cancel:{generation_id}'):
                                task.cancel()
                                return
                        except Exception:
                            logger.exception('Shared cancellation channel unavailable')
                            try:
                                from app.db.models import GenerationState
                                from app.db.session import SessionLocal
                                async with SessionLocal() as db:
                                    state = await db.get(GenerationState, generation_id)
                                if state and state.status == 'CANCELLED':
                                    task.cancel()
                                    return
                            except Exception:
                                logger.exception('SQL cancellation fallback unavailable')
                        await asyncio.sleep(.25)
                watcher = asyncio.create_task(watch_cancel())
                self._watchers.add(watcher)
                watcher.add_done_callback(self._watchers.discard)
                task.add_done_callback(lambda _: watcher.cancel())
            return task

    async def _forget_task(self, generation_id: str) -> None:
        async with self._lock:
            task = self._tasks.get(generation_id)
            if task and task.done():
                self._tasks.pop(generation_id, None)
                self._content.pop(generation_id, None)
                if not task.cancelled():
                    try:
                        task.exception()
                    except Exception:
                        pass

    async def cancel(self, generation_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(generation_id)
        if not task or task.done():
            if self._distributed():
                try:
                    redis = await self._redis()
                    await redis.set(f'paismart:generation:cancel:{generation_id}', '1', ex=300)
                except Exception:
                    logger.exception('Shared cancellation unavailable; caller persists SQL cancellation')
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    async def publish(self, generation_id: str, payload: dict) -> None:
        if self._distributed():
            # Absolute checked text makes replay, trimmed streams and a dropped
            # subscriber queue idempotent; legacy local chunks remain supported.
            payload = dict(payload)
            if payload.get('type') == 'chunk':
                self._content[generation_id] = self._content.get(generation_id, '') + payload.get('chunk', '')
                payload['content'] = self._content[generation_id]
            elif payload.get('type') in {'answer_replace', 'completion'} and isinstance(payload.get('content'), str):
                self._content[generation_id] = payload['content']
            payload['streamContent'] = self._content.get(generation_id, '')
            try:
                redis = await self._redis()
                async with redis.pipeline(transaction=True) as pipe:
                    key = f'paismart:generation:events:{generation_id}'
                    pipe.xadd(key, {'payload': json.dumps(payload, ensure_ascii=False)}, maxlen=1024)
                    pipe.expire(key, 7200)
                    await pipe.execute()
            except Exception:
                # Generation still commits its SQL authority; sockets poll it
                # below while Redis reconnects. Never retry the paid generation.
                logger.exception('Generation event publish failed; SQL snapshot remains authoritative')
        # Never block generation on a slow/disconnected UI. Each subscriber queue is
        # bounded; if it falls behind, snapshot recovery is the authoritative fallback.
        for queue in list(self._subscribers.get(generation_id, ())):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

    def subscribe(self, generation_id: str, max_events: int = 256) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=max(8, max_events))
        self._subscribers[generation_id].add(queue)
        return queue

    def unsubscribe(self, generation_id: str, queue: asyncio.Queue | None) -> None:
        if queue is None:
            return
        listener = self._listeners.pop(queue, None)
        if listener:
            listener.cancel()
        subscribers = self._subscribers.get(generation_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(generation_id, None)

    async def heartbeat(self, generation_id: str) -> None:
        from sqlalchemy import update
        from app.db.models import GenerationState
        from app.db.session import SessionLocal

        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            try:
                async with SessionLocal() as db:
                    result = await db.execute(update(GenerationState).where(
                        GenerationState.generation_id == generation_id,
                        GenerationState.status.in_(("PENDING", "STREAMING")),
                    ).values(updated_at=utcnow()))
                    await db.commit()
                    if not result.rowcount:
                        return
            except Exception:
                logger.exception("Generation heartbeat failed for %s", generation_id)

    async def recovery_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await self.recover_orphaned_states()
            except Exception:
                logger.exception("Generation recovery failed")

    async def recover_orphaned_states(self) -> int:
        from sqlalchemy import select, update
        from app.accounting.usage import usage_service
        from app.db.models import GenerationState, LLMTokenReservation
        from app.db.session import SessionLocal
        async with SessionLocal() as db:
            result = await db.execute(
                update(GenerationState)
                .where(GenerationState.status.in_(["PENDING", "STREAMING"]),
                       GenerationState.updated_at < utcnow() - timedelta(seconds=GENERATION_LEASE_SECONDS))
                .values(status="INTERRUPTED", error="Generation heartbeat expired")
            )
            unsettled_ids = (await db.scalars(
                select(LLMTokenReservation.generation_id)
                .join(GenerationState, GenerationState.generation_id == LLMTokenReservation.generation_id)
                .where(LLMTokenReservation.status == "RESERVED",
                       GenerationState.status.in_(["INTERRUPTED", "FAILED", "CANCELLED"]))
            )).all()
            for generation_id in unsettled_ids:
                await usage_service.release_llm(db, generation_id, "server_restart_recovery", commit=False)
            await db.commit()
            return int(result.rowcount or 0)

    def is_running(self, generation_id: str) -> bool:
        task = self._tasks.get(generation_id)
        return bool(task and not task.done())

    async def close(self):
        tasks = [*self._listeners.values(), *self._tasks.values(), *self._watchers]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._listeners.clear()
        self._watchers.clear()


generation_runtime = GenerationRuntime()
