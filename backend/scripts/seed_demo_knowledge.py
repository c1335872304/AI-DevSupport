from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

# Allow `python scripts/seed_demo_knowledge.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.time import utcnow

DEMO_DIR = ROOT / "demo_knowledge"
MANIFEST_PATH = DEMO_DIR / "manifest.json"


def load_manifest() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("demo_knowledge/manifest.json must contain a non-empty documents list")
    seen: set[str] = set()
    for item in documents:
        file_name = str(item.get("file") or "").strip()
        if not file_name or Path(file_name).name != file_name or not file_name.endswith(".md"):
            raise ValueError(f"Invalid demo knowledge file: {file_name!r}")
        if file_name in seen:
            raise ValueError(f"Duplicate demo knowledge file: {file_name}")
        seen.add(file_name)
        path = DEMO_DIR / file_name
        if not path.is_file():
            raise FileNotFoundError(path)
    return data


async def _delete_upload(db, upload) -> None:
    from sqlalchemy import delete

    from app.db.models import ChunkInfo, DocumentParentChunk, DocumentVector, FileUpload, ProcessingJob
    from app.documents.storage import storage_service
    from app.knowledge.elasticsearch import elasticsearch_service

    if upload.storage_key:
        try:
            await storage_service.delete(upload.storage_key)
        except Exception:
            # Database/index cleanup should still proceed if a stale demo storage object is gone.
            pass
    try:
        await elasticsearch_service.delete_file(upload.file_md5, str(upload.user_id))
    except Exception:
        # A local DB-only demo must remain resettable when Elasticsearch is not running.
        pass

    await db.execute(delete(DocumentVector).where(
        DocumentVector.file_md5 == upload.file_md5,
        DocumentVector.user_id == str(upload.user_id),
    ))
    await db.execute(delete(DocumentParentChunk).where(
        DocumentParentChunk.file_md5 == upload.file_md5,
        DocumentParentChunk.user_id == str(upload.user_id),
    ))
    await db.execute(delete(ChunkInfo).where(
        ChunkInfo.file_md5 == upload.file_md5,
        ChunkInfo.user_id == str(upload.user_id),
    ))
    await db.execute(delete(ProcessingJob).where(ProcessingJob.file_id == upload.id))
    await db.execute(delete(FileUpload).where(FileUpload.id == upload.id))
    await db.commit()


async def seed(username: str, *, reset: bool, reindex: bool, is_public: bool, org_tag: str | None) -> None:
    from sqlalchemy import select

    from app.core.access import user_orgs
    from app.core.config import get_settings
    from app.db.init_db import init_db
    from app.db.models import FileUpload, OrganizationTag, User
    from app.db.session import SessionLocal
    from app.documents.storage import storage_service
    from app.knowledge.indexer import process_file
    from app.knowledge.metadata import apply_metadata_to_file, file_metadata, normalize_metadata

    manifest = load_manifest()
    await init_db()
    settings = get_settings()

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            raise SystemExit(f"user not found: {username}")

        resolved_org = org_tag if org_tag is not None else user.primary_org
        if resolved_org:
            org = await db.get(OrganizationTag, resolved_org)
            if not org:
                raise SystemExit(f"organization not found: {resolved_org}")
            if user.role != "ADMIN" and resolved_org not in user_orgs(user):
                raise SystemExit(f"user {username} has no access to organization: {resolved_org}")

        file_names = [str(item["file"]) for item in manifest["documents"]]
        if reset:
            old_rows = list((await db.scalars(
                select(FileUpload).where(
                    FileUpload.user_id == str(user.id),
                    FileUpload.file_name.in_(file_names),
                )
            )).all())
            for old in old_rows:
                await _delete_upload(db, old)

        seeded = 0
        skipped = 0
        replaced = 0

        for item in manifest["documents"]:
            file_name = str(item["file"])
            source_path = DEMO_DIR / file_name
            raw = source_path.read_bytes()
            file_md5 = hashlib.md5(raw).hexdigest()

            current = await db.scalar(select(FileUpload).where(
                FileUpload.file_md5 == file_md5,
                FileUpload.user_id == str(user.id),
            ))

            # If the shipped demo document changed between versions, replace an older
            # same-name demo entry rather than leaving two versions visible to retrieval.
            same_name_rows = list((await db.scalars(select(FileUpload).where(
                FileUpload.user_id == str(user.id),
                FileUpload.file_name == file_name,
            ))).all())
            for old in same_name_rows:
                if old.file_md5 != file_md5:
                    await _delete_upload(db, old)
                    replaced += 1

            if current and current.process_status == "COMPLETED" and current.active_vector_version and not reindex:
                desired = normalize_metadata(item.get("metadata") or {})
                existing = file_metadata(current)
                comparable = {
                    "category": existing.get("category"), "product": existing.get("product"),
                    "region": existing.get("region"), "channel": existing.get("channel"),
                    "effective_date": existing.get("effective_date"), "version": existing.get("version"),
                    "error_code": existing.get("error_code"), "plan": existing.get("plan"),
                }
                desired_public = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in desired.items() if k != "effective_at"}
                metadata_changed = any(desired_public.get(k) != comparable.get(k) for k in desired_public)
                current.org_tag = resolved_org
                current.is_public = is_public
                apply_metadata_to_file(current, item.get("metadata") or {})
                await db.commit()
                if not metadata_changed:
                    skipped += 1
                    print(f"[SKIP] {file_name} already indexed ({current.actual_chunk_count or 0} chunks)")
                    continue
                print(f"[REINDEX] {file_name} metadata changed")

            storage_key = f"uploads/{user.id}/{file_md5}/{file_name}"
            await storage_service.put_bytes(storage_key, raw, content_type="text/markdown; charset=utf-8")

            if not current:
                current = FileUpload(
                    file_md5=file_md5,
                    file_name=file_name,
                    total_size=len(raw),
                    status=1,
                    process_status="PENDING",
                    user_id=str(user.id),
                    org_tag=resolved_org,
                    is_public=is_public,
                    storage_key=storage_key,
                    merged_at=utcnow(),
                )
                apply_metadata_to_file(current, item.get("metadata") or {})
                db.add(current)
                await db.commit()
                await db.refresh(current)
            else:
                current.file_name = file_name
                current.total_size = len(raw)
                current.status = 1
                current.process_status = "PENDING"
                current.process_error = None
                current.org_tag = resolved_org
                current.is_public = is_public
                current.storage_key = storage_key
                current.merged_at = utcnow()
                apply_metadata_to_file(current, item.get("metadata") or {})
                await db.commit()

            print(f"[INDEX] {file_name}")
            await process_file(db, current.id)
            refreshed = await db.get(FileUpload, current.id)
            print(
                f"       status={refreshed.process_status if refreshed else '?'} "
                f"chunks={refreshed.actual_chunk_count if refreshed else '?'}"
            )
            seeded += 1

    print()
    print("PaiSmart demo knowledge is ready.")
    print(f"documents indexed: {seeded}; skipped: {skipped}; replaced: {replaced}")
    print(f"visibility: {'public' if is_public else 'private'}; org: {resolved_org or '-'}")
    print(f"search backend: {settings.search_backend}; embedding: {settings.embedding_model if settings.embedding_api_key else 'local-hash-v1'}")
    print("RAG eval:")
    print("  python scripts/evaluate_rag.py eval/demo_knowledge_rag.jsonl --username " + username + " -k 6")


def validate_demo_documents() -> None:
    from app.knowledge.parser import parser_service

    manifest = load_manifest()
    total_parents = 0
    total_children = 0
    for item in manifest["documents"]:
        file_name = str(item["file"])
        raw = (DEMO_DIR / file_name).read_bytes()
        blocks = parser_service.parse(file_name, raw)
        parents, children = parser_service.hierarchical_chunk(blocks)
        if not parents or not children:
            raise RuntimeError(f"{file_name} produced no searchable chunks")
        total_parents += len(parents)
        total_children += len(children)
        print(f"[OK] {file_name}: parents={len(parents)} children={len(children)} bytes={len(raw)}")
    print(f"Validated {len(manifest['documents'])} demo documents: parents={total_parents}, children={total_children}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed and index the built-in PaiSmart AI customer-service demo knowledge base"
    )
    parser.add_argument("--username", default="admin", help="Existing PaiSmart user that owns the demo documents")
    parser.add_argument("--org-tag", default=None, help="Organization tag; defaults to the user's primary organization")
    parser.add_argument("--private", action="store_true", help="Keep demo documents private to the owner instead of public")
    parser.add_argument("--reset", action="store_true", help="Remove same-name demo documents and rebuild them")
    parser.add_argument("--reindex", action="store_true", help="Rebuild vectors even when the current content is already indexed")
    parser.add_argument("--validate-only", action="store_true", help="Parse/chunk shipped demo documents without touching the database")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.validate_only:
        validate_demo_documents()
    else:
        asyncio.run(
            seed(
                args.username,
                reset=args.reset,
                reindex=args.reindex,
                is_public=not args.private,
                org_tag=args.org_tag,
            )
        )
