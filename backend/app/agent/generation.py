from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable


class GenerationRuntime:
    """Process-local owner of detached generation tasks and live event subscribers.

    Durable recovery still comes from GenerationState checkpoints in the database. This
    runtime only owns live tasks/events, so a WebSocket disconnect never cancels generation.
    Multi-instance deployments can replace publish/subscribe with Redis without changing
    stream_chat or AgentRuntime.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def start(self, generation_id: str, factory: Callable[[], Awaitable[None]]) -> asyncio.Task:
        async with self._lock:
            existing = self._tasks.get(generation_id)
            if existing and not existing.done():
                return existing
            task = asyncio.create_task(factory(), name=f"generation:{generation_id}")
            self._tasks[generation_id] = task
            task.add_done_callback(lambda _: asyncio.create_task(self._forget_task(generation_id)))
            return task

    async def _forget_task(self, generation_id: str) -> None:
        async with self._lock:
            task = self._tasks.get(generation_id)
            if task and task.done():
                self._tasks.pop(generation_id, None)
                if not task.cancelled():
                    try:
                        task.exception()
                    except Exception:
                        pass

    async def cancel(self, generation_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(generation_id)
        if not task or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    async def publish(self, generation_id: str, payload: dict) -> None:
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
        subscribers = self._subscribers.get(generation_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(generation_id, None)

    async def recover_orphaned_states(self) -> int:
        from sqlalchemy import select, update
        from app.accounting.usage import usage_service
        from app.db.models import GenerationState
        from app.db.session import SessionLocal
        async with SessionLocal() as db:
            orphaned_ids = list((await db.scalars(
                select(GenerationState.generation_id).where(
                    GenerationState.status.in_(["PENDING", "STREAMING"])
                )
            )).all())
            result = await db.execute(
                update(GenerationState)
                .where(GenerationState.status.in_(["PENDING", "STREAMING"]))
                .values(status="INTERRUPTED", error="Server restarted before generation completed")
            )
            await db.commit()
            for generation_id in orphaned_ids:
                await usage_service.release_llm(db, generation_id, "server_restart_recovery")
            return int(result.rowcount or 0)

    def is_running(self, generation_id: str) -> bool:
        task = self._tasks.get(generation_id)
        return bool(task and not task.done())


generation_runtime = GenerationRuntime()
