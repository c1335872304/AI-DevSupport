from __future__ import annotations

"""Create a small, prefixed-only corpus for the blind RAG evaluation suite.

It is intentionally separate from demo seeding.  All accounts, organizations,
storage objects and documents use the ``rag_eval``/``fixture-`` prefix so a
later cleanup can target only this test data.
"""

import argparse
import asyncio
import hashlib
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_DIR = ROOT / "eval" / "fixtures" / "advanced_rag"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
OWNER_USERNAME = "rag_eval_fixture_owner"
ORG_A = "rag-eval-org-a"
ORG_B = "rag-eval-org-b"
USER_A = "rag_eval_org_a"
USER_B = "rag_eval_org_b"


def load_manifest() -> list[dict]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = payload.get("documents") or []
    if not isinstance(rows, list) or not rows:
        raise ValueError("fixture manifest has no documents")
    names: set[str] = set()
    for row in rows:
        name = str(row.get("file") or "")
        if not name.startswith("fixture-") or Path(name).name != name or not name.endswith(".md"):
            raise ValueError(f"unsafe fixture filename: {name!r}")
        if name in names:
            raise ValueError(f"duplicate fixture filename: {name}")
        names.add(name)
        if not str(row.get("content") or "").strip():
            raise ValueError(f"empty fixture: {name}")
        if row.get("visibility") not in {"public", "private"}:
            raise ValueError(f"invalid visibility: {name}")
    return rows


async def delete_fixture_upload(db, upload) -> None:
    from app.documents.lifecycle import tombstone_document

    await tombstone_document(db, upload.id)


async def ensure_fixture_users(db):
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.db.models import OrganizationTag, User

    owner = await db.scalar(select(User).where(User.username == OWNER_USERNAME))
    if not owner:
        owner = User(
            username=OWNER_USERNAME,
            password=hash_password(secrets.token_urlsafe(32)),
            role="USER",
            org_tags=f"{ORG_A},{ORG_B}",
            primary_org=ORG_A,
            llm_token_balance=0,
            embedding_token_balance=100000,
        )
        db.add(owner)
        await db.commit()
        await db.refresh(owner)
    for tag, name in ((ORG_A, "RAG Eval Organization A"), (ORG_B, "RAG Eval Organization B")):
        if not await db.get(OrganizationTag, tag):
            db.add(
                OrganizationTag(
                    tag_id=tag, name=name, description="isolated RAG evaluation fixture", created_by=owner.id
                )
            )
    await db.commit()
    for username, org in ((USER_A, ORG_A), (USER_B, ORG_B)):
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            db.add(
                User(
                    username=username,
                    password=hash_password(secrets.token_urlsafe(32)),
                    role="USER",
                    org_tags=org,
                    primary_org=org,
                    llm_token_balance=0,
                    embedding_token_balance=0,
                )
            )
    await db.commit()
    return owner


async def cleanup(*, apply: bool) -> int:
    """Preview or delete only explicitly-owned, prefixed blind-evaluation fixtures."""
    from sqlalchemy import select

    from app.db.init_db import init_db
    from app.db.models import FileUpload, User
    from app.db.session import SessionLocal, engine
    from app.knowledge.elasticsearch import elasticsearch_service

    await init_db()
    deleted = 0
    try:
        async with SessionLocal() as db:
            owner = await db.scalar(select(User).where(User.username == OWNER_USERNAME))
            if not owner:
                print("fixture_cleanup complete deleted=0 owner_missing=true")
                return 0
            rows = list(
                (
                    await db.scalars(
                        select(FileUpload).where(
                            FileUpload.user_id == str(owner.id), FileUpload.file_name.like("fixture-%")
                        )
                    )
                ).all()
            )
            if not apply:
                print(f"fixture_cleanup dry_run=true would_delete={len(rows)}")
                return len(rows)
            for row in rows:
                await delete_fixture_upload(db, row)
                deleted += 1
        print(f"fixture_cleanup complete deleted={deleted}")
        return deleted
    finally:
        await elasticsearch_service.close()
        await engine.dispose()


async def seed(*, reset: bool) -> None:
    from sqlalchemy import select

    from app.core.time import utcnow
    from app.db.init_db import init_db
    from app.db.models import FileUpload
    from app.db.session import SessionLocal, engine
    from app.documents.storage import storage_service
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.documents.jobs import create_processing_job, run_processing_job
    from app.knowledge.metadata import apply_metadata_to_file

    documents = load_manifest()
    await init_db()
    try:
        async with SessionLocal() as db:
            owner = await ensure_fixture_users(db)

            seeded = 0
            skipped = 0
            for item in documents:
                name = str(item["file"])
                raw = str(item["content"]).encode("utf-8")
                digest = hashlib.md5(raw).hexdigest()
                current = await db.scalar(
                    select(FileUpload).where(
                        FileUpload.user_id == str(owner.id), FileUpload.file_md5 == digest
                    )
                )
                if current and current.deleted_at is not None:
                    raise ValueError(
                        "Deleted fixture identities require a fresh test database or new logical document"
                    )
                if (
                    current
                    and current.process_status == "COMPLETED"
                    and current.active_vector_version
                    and not reset
                ):
                    skipped += 1
                    continue
                storage_key = f"rag-eval-fixtures/{owner.id}/{digest}/{name}"
                await storage_service.put_bytes(storage_key, raw, content_type="text/markdown; charset=utf-8")
                if current is None:
                    current = FileUpload(
                        file_md5=digest,
                        file_name=name,
                        total_size=len(raw),
                        status=1,
                        process_status="PENDING",
                        user_id=str(owner.id),
                        org_tag=item.get("orgTag"),
                        is_public=item["visibility"] == "public",
                        storage_key=storage_key,
                        merged_at=utcnow(),
                    )
                apply_metadata_to_file(current, item.get("metadata") or {})
                db.add(current)
                await db.commit()
                await db.refresh(current)
                print(f"[INDEX] {name}")
                job_id = await create_processing_job(current.id, force=reset, db=db)
                await run_processing_job(job_id)
                await db.refresh(current)
                refreshed = await db.get(FileUpload, current.id)
                if not refreshed or refreshed.process_status != "COMPLETED":
                    raise RuntimeError(
                        f"fixture indexing failed: {name}: {refreshed.process_error if refreshed else 'missing'}"
                    )
                seeded += 1
        print(f"fixture_seed complete seeded={seeded} skipped={skipped} documents={len(documents)}")
    finally:
        await elasticsearch_service.close()
        await engine.dispose()


def parse_args():
    parser = argparse.ArgumentParser(description="Seed isolated advanced RAG test fixtures")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete only fixture-* rows owned by rag_eval_fixture_owner before rebuilding",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="preview fixture-* rows owned by rag_eval_fixture_owner, then exit",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform a cleanup after --cleanup has shown the target namespace",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.apply and not args.cleanup:
        raise SystemExit("--apply requires --cleanup")
    if args.cleanup:
        asyncio.run(cleanup(apply=args.apply))
    else:
        asyncio.run(seed(reset=args.reset))
