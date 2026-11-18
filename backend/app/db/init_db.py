from __future__ import annotations

from sqlalchemy import inspect, select, text

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Base, OrganizationTag, RechargePackage, User
from app.db.session import SessionLocal, engine


async def init_db() -> None:
    settings = get_settings()
    if settings.app_env.lower() not in {"prod", "production"} and settings.database_auto_create_dev:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # create_all does not add columns to an existing SQLite/MySQL table.
            # Legacy local compatibility only. Versioned schema upgrades use
            # Alembic; run.py can invoke it through DATABASE_AUTO_MIGRATE.
            def add_missing_columns(sync_conn):
                columns = {item["name"] for item in inspect(sync_conn).get_columns("conversation_sessions")}
                if "collected_entities_json" not in columns:
                    sync_conn.execute(text("ALTER TABLE conversation_sessions ADD COLUMN collected_entities_json TEXT DEFAULT '{}'"))

            await conn.run_sync(add_missing_columns)

    async with SessionLocal() as db:
        default_tag = await db.get(OrganizationTag, "default")
        if not default_tag:
            db.add(OrganizationTag(tag_id="default", name="默认组织", description="默认知识空间", created_by=0))

        existing_package = await db.scalar(select(RechargePackage).limit(1))
        if not existing_package:
            db.add_all(
                [
                    RechargePackage(
                        package_name="体验版",
                        package_price=990,
                        package_desc="适合轻度体验和少量知识库上传",
                        package_benefit="LLM Token：250万\nEmbedding Token：100万",
                        llm_token=2_500_000,
                        embedding_token=1_000_000,
                        sort_order=10,
                    ),
                    RechargePackage(
                        package_name="进阶版",
                        package_price=1990,
                        package_desc="适合持续问答和中等规模知识库",
                        package_benefit="LLM Token：550万\nEmbedding Token：250万",
                        llm_token=5_500_000,
                        embedding_token=2_500_000,
                        sort_order=20,
                    ),
                ]
            )

        if settings.bootstrap_admin_enabled:
            admin = await db.scalar(select(User).where(User.username == settings.bootstrap_admin_username))
            if not admin:
                db.add(
                    User(
                        username=settings.bootstrap_admin_username,
                        password=hash_password(settings.bootstrap_admin_password),
                        role="ADMIN",
                        org_tags="default,admin",
                        primary_org="default",
                    )
                )
        await db.commit()
