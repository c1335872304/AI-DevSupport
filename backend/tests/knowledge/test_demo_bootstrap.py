"""An upgrade must not turn startup into a knowledge import or re-encoding job."""

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, FileUpload, SupportApplication, User


@pytest.mark.asyncio
async def test_existing_demo_knowledge_and_business_are_not_seeded(tmp_path, monkeypatch):
    from app.db import init_db, session
    from app.core.config import get_settings
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path/'existing.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        user = User(username=get_settings().bootstrap_admin_username, password="unused")
        db.add(user); await db.flush()
        db.add(FileUpload(file_md5="a"*32, file_name="existing.md", user_id=str(user.id), storage_key="existing"))
        db.add(SupportApplication(id="existing", name="Existing app", user_id=str(user.id)))
        await db.commit()
    async def no_init():
        pass
    def forbidden(*_, **__):
        raise AssertionError("Existing knowledge must not invoke an importer")
    monkeypatch.setattr(init_db, "init_db", no_init)
    monkeypatch.setattr(session, "SessionLocal", sessions)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setitem(sys.modules, "seed_support_demo", SimpleNamespace(seed=forbidden))
    script = Path(__file__).resolve().parents[2]/"scripts/bootstrap_demo.py"
    spec = importlib.util.spec_from_file_location("test_bootstrap", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.main()
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(FileUpload)) == 1
    await engine.dispose()
