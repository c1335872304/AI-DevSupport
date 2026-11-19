"""Actual Redis streams across runtime instances and independent processes."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from app.agent.generation import GenerationRuntime
from app.core.config import get_settings


@pytest.fixture
async def bus(monkeypatch):
    url = os.environ.get('GENERATION_TEST_REDIS_URL')
    if not url:
        pytest.skip('Requires dedicated Redis event transport')
    from redis.asyncio import from_url
    redis = from_url(url, decode_responses=True)
    await redis.ping()
    monkeypatch.setattr(get_settings(), 'redis_enabled', True)
    async def client():
        return redis
    monkeypatch.setattr(GenerationRuntime, '_redis', staticmethod(client))
    try:
        yield redis, url
    finally:
        await redis.aclose()


async def test_replica_reconnect_gets_cursor_snapshot_and_idempotent_future_text(bus):
    redis, _ = bus
    gid = 'debt-' + uuid4().hex
    owner, first, restarted = GenerationRuntime(), GenerationRuntime(), GenerationRuntime()
    try:
        queue, snapshot = await first.subscribe_shared(gid)
        assert snapshot is None
        await owner.publish(gid, {'type': 'chunk', 'chunk': 'A', 'generationId': gid})
        one = await asyncio.wait_for(queue.get(), 5)
        assert one['content'] == 'A'
        first.unsubscribe(gid, queue)
        await owner.publish(gid, {'type': 'chunk', 'chunk': 'B', 'generationId': gid})
        queue, snapshot = await restarted.subscribe_shared(gid)
        assert snapshot['streamContent'] == 'AB'
        await owner.publish(gid, {'type': 'chunk', 'chunk': 'C', 'generationId': gid})
        event = await asyncio.wait_for(queue.get(), 5)
        assert event['content'] == 'ABC' and event['chunk'] == 'C'
        await owner.publish(gid, {'type': 'completion', 'content': 'Checked final answer', 'generationId': gid})
        assert (await asyncio.wait_for(queue.get(), 5))['content'] == 'Checked final answer'
    finally:
        await asyncio.gather(owner.close(), first.close(), restarted.close())
        await redis.delete(f'paismart:generation:events:{gid}', f'paismart:generation:cancel:{gid}')


CHILD = r'''
import asyncio,json,sys
from pathlib import Path
from app.agent.generation import GenerationRuntime
async def main():
    runtime=GenerationRuntime()
    queue,_=await runtime.subscribe_shared(sys.argv[1])
    Path(sys.argv[2]).write_text('ready')
    events=[]
    async with asyncio.timeout(15):
        while True:
            event=await queue.get()
            events.append(event)
            if event.get('type')=='chunk':
                await runtime.cancel(sys.argv[1])
            if event.get('type')=='completion': break
    print(json.dumps(events))
    await runtime.close()
asyncio.run(main())
'''


async def test_independent_process_receives_and_cancels_owner_generation(bus, tmp_path):
    redis, url = bus
    gid = 'debt-' + uuid4().hex
    ready = tmp_path / 'subscriber-ready'
    env = {**os.environ, 'REDIS_ENABLED': 'true', 'REDIS_URL': url, 'LANGFUSE_ENABLED': 'false'}
    child = subprocess.Popen([sys.executable, '-c', CHILD, gid, str(ready)], env=env,
        cwd=str(Path(__file__).resolve().parents[2]), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    owner = GenerationRuntime()
    try:
        async with asyncio.timeout(15):
            while not ready.exists():
                if child.poll() is not None:
                    raise AssertionError(child.communicate())
                await asyncio.sleep(.05)
        async def generate():
            try:
                await owner.publish(gid, {'type': 'chunk', 'chunk': 'checked', 'generationId': gid})
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                await owner.publish(gid, {'type': 'completion', 'status': 'cancelled',
                                           'content': 'checked', 'generationId': gid})
                raise
        task = await owner.start(gid, generate)
        stdout, stderr = await asyncio.to_thread(child.communicate, timeout=20)
        assert child.returncode == 0, stderr
        events = json.loads(stdout)
        assert events[0]['content'] == 'checked' and events[-1]['status'] == 'cancelled'
        await asyncio.gather(task, return_exceptions=True)
        assert task.cancelled()
    finally:
        if child.poll() is None:
            child.kill()
            await asyncio.to_thread(child.communicate)
        await owner.close()
        await redis.delete(f'paismart:generation:events:{gid}', f'paismart:generation:cancel:{gid}')


async def test_remote_stop_survives_redis_outage_without_cancelling_another_generation(tmp_path, monkeypatch):
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.db.models import Base, GenerationState
    import app.db.session as session_module
    engine = create_async_engine('sqlite+aiosqlite:///' + (tmp_path / 'stop.db').as_posix())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner, remote = GenerationRuntime(), GenerationRuntime()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        monkeypatch.setattr(session_module, 'SessionLocal', sessions)
        monkeypatch.setattr(get_settings(), 'redis_enabled', True)
        async def unavailable():
            raise ConnectionError('synthetic Redis outage')
        monkeypatch.setattr(GenerationRuntime, '_redis', staticmethod(unavailable))
        async with sessions() as db:
            for gid in ['stop-this', 'keep-running']:
                db.add(GenerationState(generation_id=gid, conversation_id=gid, user_id='1',
                                       question='test', status='STREAMING'))
            await db.commit()
        async def generate():
            await asyncio.sleep(30)
        stopped = await owner.start('stop-this', generate)
        healthy = await owner.start('keep-running', generate)
        assert not await remote.cancel('stop-this')  # Redis failure must not prevent the durable stop.
        async with sessions() as db:
            await db.execute(update(GenerationState).where(GenerationState.generation_id == 'stop-this')
                             .values(status='CANCELLED'))
            await db.commit()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(stopped, 5)
        assert not healthy.done()
    finally:
        await owner.close()
        await remote.close()
        await engine.dispose()
