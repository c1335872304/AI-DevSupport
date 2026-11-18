from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import uuid
from pathlib import Path

# Allow `python scripts/seed_demo_knowledge.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.time import utcnow

MANIFEST_PATH = ROOT / "vendor_knowledge" / "manifest.json"


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict:
    manifest_path = Path(manifest_path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("Knowledge manifest must contain a non-empty documents list")
    seen: set[str] = set()
    for item in documents:
        file_name = str(item.get("file") or "").strip()
        if not file_name or Path(file_name).name != file_name or not file_name.endswith(".md"):
            raise ValueError(f"Invalid demo knowledge file: {file_name!r}")
        if file_name in seen:
            raise ValueError(f"Duplicate demo knowledge file: {file_name}")
        seen.add(file_name)
        path = manifest_path.parent / file_name
        if not path.is_file():
            raise FileNotFoundError(path)
        expected_hash = item.get("sha256")
        if expected_hash and hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Knowledge snapshot checksum mismatch: {file_name}")
    return data


async def seed(
    username: str,
    *,
    reset: bool,
    reindex: bool,
    is_public: bool,
    org_tag: str | None,
    manifest_path: Path = MANIFEST_PATH,
) -> None:
    from sqlalchemy import func, select

    from app.core.access import user_orgs
    from app.core.config import get_settings
    from app.db.init_db import init_db
    from app.db.models import DocumentVector, FileUpload, OrganizationTag, User
    from app.db.session import SessionLocal
    from app.documents.storage import storage_service
    from app.documents.jobs import create_processing_job, run_processing_job
    from app.documents.revision_snapshot import remember_revision
    from app.knowledge.metadata import (
        apply_metadata_to_file,
        file_metadata,
        normalize_metadata,
        stage_metadata,
    )

    manifest_path = Path(manifest_path).resolve()
    manifest = load_manifest(manifest_path)
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

        # Reset rebuilds logical documents in place; it never erases a live
        # identity or deletes other workers' versions.
        if reset:
            reindex = True

        seeded = 0
        skipped = 0
        replaced = 0

        for item in manifest["documents"]:
            file_name = str(item["file"])
            source_path = manifest_path.parent / file_name
            raw = source_path.read_bytes()
            file_md5 = hashlib.md5(raw).hexdigest()

            same_name_rows = list(
                (
                    await db.scalars(
                        select(FileUpload).where(
                            FileUpload.user_id == str(user.id),
                            FileUpload.file_name == file_name,
                            FileUpload.deleted_at.is_(None),
                        )
                    )
                ).all()
            )
            if len(same_name_rows) > 1:
                raise ValueError(f"Ambiguous seed document name: {file_name}; use a dedicated demo account")
            current = same_name_rows[0] if same_name_rows else None
            identity = file_md5
            if not current and await db.scalar(
                select(FileUpload.id).where(
                    FileUpload.user_id == str(user.id), FileUpload.file_md5 == identity
                )
            ):
                identity = uuid.uuid4().hex  # A new logical identity; never revive a tombstone.

            if (
                current
                and current.process_status == "COMPLETED"
                and current.active_vector_version
                and not reindex
            ):
                matching = int(
                    (
                        await db.scalar(
                            select(func.count())
                            .select_from(DocumentVector)
                            .where(
                                DocumentVector.file_md5 == current.file_md5,
                                DocumentVector.user_id == str(user.id),
                                DocumentVector.vector_version == current.active_vector_version,
                                DocumentVector.model_version == settings.embedding_model,
                            )
                        )
                    )
                    or 0
                )
                desired = normalize_metadata(item.get("metadata") or {})
                existing = file_metadata(current)
                comparable = {
                    "category": existing.get("category"),
                    "product": existing.get("product"),
                    "region": existing.get("region"),
                    "channel": existing.get("channel"),
                    "effective_date": existing.get("effective_date"),
                    "version": existing.get("version"),
                    "error_code": existing.get("error_code"),
                    "plan": existing.get("plan"),
                }
                desired_public = {
                    k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in desired.items()
                    if k != "effective_at"
                }
                metadata_changed = any(desired_public.get(k) != comparable.get(k) for k in desired_public)
                current.org_tag = resolved_org
                current.is_public = is_public
                if metadata_changed:
                    replaced += 1
                await db.commit()
                if (
                    not metadata_changed
                    and current.source_md5 in (None, file_md5)
                    and matching == current.actual_chunk_count
                    and matching > 0
                ):
                    skipped += 1
                    print(f"[SKIP] {file_name} already indexed ({current.actual_chunk_count or 0} chunks)")
                    continue
                print(f"[REINDEX] {file_name} metadata or embedding model changed")

            storage_key = f"uploads/{user.id}/{file_md5}/{file_name}"
            await storage_service.put_bytes(storage_key, raw, content_type="text/markdown; charset=utf-8")

            if not current:
                current = FileUpload(
                    file_md5=identity,
                    source_md5=file_md5,
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
                if current.active_vector_version and not current.active_source_key:
                    old_raw = await storage_service.get_bytes(current.storage_key)
                    await remember_revision(db, current, old_raw, current.storage_key, apply_desired=False)
                    current.active_source_key = func.coalesce(
                        FileUpload.active_source_key, current.storage_key
                    )
                    current.active_file_name = func.coalesce(FileUpload.active_file_name, current.file_name)
                current.file_name = file_name
                current.total_size = len(raw)
                current.status = 1
                current.process_status = "PENDING"
                current.process_error = None
                current.org_tag = resolved_org
                current.is_public = is_public
                current.storage_key = storage_key
                current.source_md5 = file_md5
                current.merged_at = utcnow()
                stage_metadata(current, item.get("metadata") or {})
                current.input_revision = FileUpload.input_revision + 1
                await db.commit()
                await db.refresh(current)

            print(f"[INDEX] {file_name}")
            await remember_revision(db, current, raw, storage_key)
            job_id = await create_processing_job(current.id, force=reindex, db=db)
            await run_processing_job(job_id)
            await db.refresh(current)
            refreshed = await db.get(FileUpload, current.id)
            print(
                f"       status={refreshed.process_status if refreshed else '?'} "
                f"chunks={refreshed.actual_chunk_count if refreshed else '?'}"
            )
            seeded += 1

    print()
    print("Knowledge manifest import is complete.")
    print(f"documents indexed: {seeded}; skipped: {skipped}; replaced: {replaced}")
    print(f"visibility: {'public' if is_public else 'private'}; org: {resolved_org or '-'}")
    print(f"search backend: {settings.search_backend}; embedding: {settings.embedding_model}")
    print("RAG eval:")
    eval_path = manifest.get("evaluationDataset") or "eval/demo_knowledge_rag.jsonl"
    print(f"  python scripts/evaluate_rag.py {eval_path} --username {username} -k 6")


def validate_demo_documents(manifest_path: Path = MANIFEST_PATH) -> None:
    from app.knowledge.parser import parser_service

    manifest_path = Path(manifest_path).resolve()
    manifest = load_manifest(manifest_path)
    total_parents = 0
    total_children = 0
    for item in manifest["documents"]:
        file_name = str(item["file"])
        raw = (manifest_path.parent / file_name).read_bytes()
        blocks = parser_service.parse(file_name, raw)
        parents, children = parser_service.hierarchical_chunk(blocks)
        if not parents or not children:
            raise RuntimeError(f"{file_name} produced no searchable chunks")
        total_parents += len(parents)
        total_children += len(children)
        print(f"[OK] {file_name}: parents={len(parents)} children={len(children)} bytes={len(raw)}")
    print(
        f"Validated {len(manifest['documents'])} demo documents: parents={total_parents}, children={total_children}"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import and index a knowledge manifest (defaults to the official vendor corpus)"
    )
    parser.add_argument(
        "--username", default="admin", help="Existing PaiSmart user that owns the demo documents"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Knowledge manifest; documents are resolved beside this JSON file",
    )
    parser.add_argument(
        "--org-tag", default=None, help="Organization tag; defaults to the user's primary organization"
    )
    parser.add_argument(
        "--private", action="store_true", help="Keep demo documents private to the owner instead of public"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Rebuild matching documents in place, preserving document identity"
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Rebuild vectors even when the current content is already indexed",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Parse/chunk shipped demo documents without touching the database",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.validate_only:
        validate_demo_documents(args.manifest)
    else:
        asyncio.run(
            seed(
                args.username,
                reset=args.reset,
                reindex=args.reindex,
                is_public=not args.private,
                org_tag=args.org_tag,
                manifest_path=args.manifest,
            )
        )
