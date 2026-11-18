"""Rebuild the selected knowledge corpus with real Qwen vectors and bounded spend.

Uses the configured application database. Existing incompatible documents owned by
the selected user are rebuilt in place; source text and other users are preserved.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def rebuild(args) -> None:
    from sqlalchemy import func, select

    from app.accounting.embedding_usage import capture_embedding_usage
    from app.core.config import get_settings
    from app.db.models import DocumentVector, FileUpload, ProcessingJob, User
    from app.db.session import SessionLocal, engine
    from app.knowledge.embedding import embedding_service
    from app.documents.jobs import create_processing_job, run_processing_job
    from scripts.evaluate_rag import main_async as evaluate
    from scripts.seed_demo_knowledge import load_manifest, seed

    settings = get_settings()
    if not settings.embedding_api_key.strip():
        raise RuntimeError("EMBEDDING_API_KEY is required; no local encoding is available")
    if settings.embedding_model != "text-embedding-v4":
        raise RuntimeError("This bounded migration is configured for Qwen text-embedding-v4")
    manifest = load_manifest(args.manifest)
    report = {
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "model": settings.embedding_model,
        "dimension": settings.embedding_dimension,
        "manifest": str(args.manifest),
        "selectedDocuments": len(manifest["documents"]),
        "tokenUpperBoundLimit": args.max_tokens,
        "tokenUpperBoundSubmitted": 0,
        "providerReportedTokens": 0,
        "oldDocumentsRebuilt": [],
        "backup": None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    original_embed = embedding_service.embed

    async def bounded_embed(texts):
        # UTF-8 bytes are a conservative token bound for this text corpus. Reserve
        # the full submitted bound, even if a network error makes usage uncertain.
        upper = sum(len(text.encode("utf-8")) for text in texts)
        if report["tokenUpperBoundSubmitted"] + upper > args.max_tokens:
            raise RuntimeError("Qwen run token budget reached; refusing another provider call")
        report["tokenUpperBoundSubmitted"] += upper
        return await original_embed(texts)

    embedding_service.embed = bounded_embed
    try:
        with capture_embedding_usage() as usage:
            try:
                async with SessionLocal() as db:
                    user = await db.scalar(select(User).where(User.username == args.username))
                    if not user:
                        raise RuntimeError("Target knowledge owner does not exist")
                    running = await db.scalar(
                        select(func.count())
                        .select_from(ProcessingJob)
                        .where(ProcessingJob.status == "RUNNING")
                    )
                    if running:
                        raise RuntimeError("Indexing jobs are running; retry after they finish")
                    owner_id = str(user.id)
                if engine.url.get_backend_name() == "sqlite" and engine.url.database != ":memory:":
                    source = Path(engine.url.database).resolve()
                    directory = ROOT / "data" / "backups"
                    directory.mkdir(parents=True, exist_ok=True)
                    backup = directory / f"before-qwen-{uuid.uuid4().hex}.sqlite"
                    with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as src:
                        with sqlite3.connect(backup) as dst:
                            src.backup(dst)
                    report["backup"] = str(backup.relative_to(ROOT))

                # A tiny real request verifies connectivity before modifying index data.
                probe = await embedding_service.embed(["Qwen embedding connection check"])
                report["probeDimension"] = len(probe[0])
                if args.reindex_existing:
                    async with SessionLocal() as db:
                        files = list(
                            (
                                await db.scalars(
                                    select(FileUpload).where(
                                        FileUpload.user_id == owner_id, FileUpload.status == 1
                                    )
                                )
                            ).all()
                        )
                        for file in files:
                            versions = list(
                                (
                                    await db.scalars(
                                        select(DocumentVector).where(
                                            DocumentVector.file_md5 == file.file_md5,
                                            DocumentVector.user_id == owner_id,
                                            DocumentVector.vector_version
                                            == (file.active_vector_version or "legacy"),
                                        )
                                    )
                                ).all()
                            )
                            compatible = (
                                file.process_status == "COMPLETED"
                                and versions
                                and all(
                                    v.model_version == settings.embedding_model
                                    and len(json.loads(v.vector_json)) == settings.embedding_dimension
                                    for v in versions
                                )
                            )
                            if compatible:
                                continue
                            job_id = await create_processing_job(file.id, force=True, db=db)
                            await run_processing_job(job_id)
                            report["oldDocumentsRebuilt"].append(file.file_name)
                            print(f"[MIGRATED] {file.file_name}", flush=True)
                await seed(
                    args.username,
                    reset=False,
                    reindex=False,
                    is_public=False,
                    org_tag=args.org_tag,
                    manifest_path=args.manifest,
                )

                if args.evaluate:
                    await evaluate(
                        argparse.Namespace(
                            dataset=str(args.dataset),
                            username=args.username,
                            k=6,
                            output=str(args.eval_output),
                        )
                    )
                    evaluation = json.loads(args.eval_output.read_text(encoding="utf-8"))
                    report["retrieval"] = {
                        "caseCount": evaluation["caseCount"],
                        "summary": evaluation["summary"],
                        "byCaseType": evaluation["byCaseType"],
                    }
                async with SessionLocal() as db:
                    rows = (
                        await db.execute(
                            select(DocumentVector.model_version, func.count())
                            .where(DocumentVector.user_id == owner_id)
                            .group_by(DocumentVector.model_version)
                        )
                    ).all()
                    report["ownerVectorsByModel"] = {model: count for model, count in rows}
                    report["ownerDocuments"] = await db.scalar(
                        select(func.count()).select_from(FileUpload).where(FileUpload.user_id == owner_id)
                    )
                report["status"] = "COMPLETED"
            finally:
                report["providerReportedTokens"] = usage.total_tokens
    except Exception as exc:
        report["status"] = "FAILED"
        report["errorType"] = type(exc).__name__
        # Avoid putting credentials, proxy URLs or provider response text into artifacts.
        raise
    finally:
        embedding_service.embed = original_embed
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        await engine.dispose()
        print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "vendor_knowledge" / "manifest.json")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--org-tag", default=None)
    parser.add_argument("--reindex-existing", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=4_000_000)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval" / "vendor_full_rag.jsonl")
    parser.add_argument("--eval-output", type=Path, default=ROOT / "eval" / "vendor-full-qwen-retrieval.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "vendor-full-qwen-build.json")
    args = parser.parse_args()
    if args.max_tokens <= 0:
        parser.error("--max-tokens must be positive")
    asyncio.run(rebuild(args))
