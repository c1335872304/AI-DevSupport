"""Initialize an empty Demo; existing knowledge is never seeded/reencoded on upgrade."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def bootstrap():
    from sqlalchemy import func, select
    from app.core.config import get_settings
    from app.db.init_db import init_db
    from app.db.models import FileUpload, SupportApplication, User
    from app.db.session import SessionLocal
    await init_db()
    username = get_settings().bootstrap_admin_username
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        knowledge_count = await db.scalar(select(func.count()).select_from(FileUpload))
        application_count = await db.scalar(select(func.count()).select_from(SupportApplication))
    if not user:
        raise RuntimeError("Demo bootstrap user is unavailable")
    if not application_count:
        from seed_support_demo import seed
        await seed(username)
    if not knowledge_count:
        # Use the same explicit importer CLI; it owns validation and usage accounting.
        import subprocess
        subprocess.run([sys.executable, str(ROOT/"scripts/seed_demo_knowledge.py"), "--username", username], check=True)
    else:
        print(f"Preserving {knowledge_count} existing knowledge documents; import and encoding skipped")


async def main():
    from app.db.session import engine
    try:
        await bootstrap()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
