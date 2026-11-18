"""Actual independent-process claim test on the dedicated MySQL schema."""

import asyncio
import os
import subprocess
import sys
import time
import uuid
import pytest

CHILD = r"""
import asyncio,json,sys,time
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.documents.coordination import claim_document,IndexBusy
async def main():
    engine=create_async_engine(sys.argv[1]);sessions=async_sessionmaker(engine,expire_on_commit=False)
    Path(sys.argv[3]).write_text('ready')
    deadline=time.monotonic()+15
    while not Path(sys.argv[4]).exists():
        if time.monotonic()>deadline: raise RuntimeError('Barrier timeout')
        await asyncio.sleep(.01)
    try:
        lease=await claim_document(sessions,int(sys.argv[2]));print(json.dumps({'claimed':bool(lease)}))
    except IndexBusy:
        print(json.dumps({'claimed':False}))
    finally: await engine.dispose()
asyncio.run(main())
"""


@pytest.mark.asyncio
async def test_independent_processes_share_document_fence(tmp_path):
    url = os.environ.get("RAG_TEST_MYSQL_URL")
    if not url:
        pytest.skip("Requires isolated real MySQL")
    assert url.endswith("/rag_acceptance")
    import json
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.db.models import User, FileUpload

    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        user = User(username="process-" + uuid.uuid4().hex[:10], password="unused")
        db.add(user)
        await db.flush()
        file = FileUpload(
            file_name="process.md", file_md5=uuid.uuid4().hex, user_id=str(user.id), storage_key="unused"
        )
        db.add(file)
        await db.commit()
        file_id = file.id
    go = tmp_path / "go"
    processes = []
    try:
        for i in range(2):
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-c", CHILD, url, str(file_id), str(tmp_path / f"ready{i}"), str(go)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            )
        deadline = time.monotonic() + 15
        while not all((tmp_path / f"ready{i}").exists() for i in range(2)):
            if time.monotonic() > deadline:
                raise RuntimeError("Child process readiness timeout")
            await asyncio.sleep(0.01)
        go.write_text("start")
        output = []
        for p in processes:
            stdout, stderr = await asyncio.to_thread(p.communicate, timeout=20)
            assert p.returncode == 0, stderr.decode(errors="replace")
            output.append(json.loads(stdout)["claimed"])
        assert sorted(output) == [False, True]
    finally:
        for p in processes:
            if p.poll() is None:
                p.kill()
                p.wait()
        await engine.dispose()
