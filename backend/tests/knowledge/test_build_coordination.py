"""Same scenarios run against isolated SQLite and opt-in real MySQL/ES."""

import asyncio
import hashlib
import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.accounting.embedding_usage import record_embedding_usage
from app.core.config import get_settings
from app.db.models import (
    Base,
    DocumentVector,
    EmbeddingAttempt,
    FileUpload,
    IndexBuild,
    IndexOutbox,
    ProcessingJob,
    User,
)
from app.documents.coordination import IndexBusy, LeaseLost, claim_document, database_now
from app.documents.lifecycle import collect_garbage, tombstone_document
from app.knowledge.build_pipeline import process_file, settle_attempt
from app.knowledge.embedding import embedding_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.documents.storage import storage_service


@pytest.fixture
async def setup_build(tmp_path, monkeypatch):
    url = os.environ.get("RAG_TEST_MYSQL_URL") or f"sqlite+aiosqlite:///{(tmp_path / 'case.db').as_posix()}"
    if os.environ.get("RAG_TEST_MYSQL_URL") and not url.endswith("/rag_acceptance"):
        raise RuntimeError("Only the isolated rag_acceptance DB is allowed")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(storage_service.settings, "local_storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(storage_service, "backend", "local")
    monkeypatch.setattr(storage_service, "_minio", None)
    settings = get_settings()
    monkeypatch.setattr(settings, "index_lease_seconds", 30)
    if not os.environ.get("RAG_TEST_REAL_ES"):
        monkeypatch.setattr(elasticsearch_service, "client", None)
    else:
        from elasticsearch import AsyncElasticsearch

        monkeypatch.setattr(elasticsearch_service, "client", AsyncElasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:19216")))
        monkeypatch.setattr(settings, "elasticsearch_index", "rag-acceptance-test")
    calls = []

    async def encode(texts):
        calls.extend(texts)
        record_embedding_usage({"total_tokens": 3})
        return [[1.0] + [0.0] * (settings.embedding_dimension - 1) for _ in texts]

    monkeypatch.setattr(embedding_service, "embed", encode)
    import app.documents.job_runtime as jobs

    monkeypatch.setattr(jobs, "SessionLocal", sessions)
    raw = ("# Authentication\n401 requires Bearer token. " + uuid.uuid4().hex).encode()
    async with sessions() as db:
        user = User(
            username="case-" + uuid.uuid4().hex[:12], password="unused", embedding_token_balance=10000
        )
        db.add(user)
        await db.flush()
        key = "tests/" + uuid.uuid4().hex + ".md"
        file = FileUpload(
            file_md5=hashlib.md5(raw).hexdigest(),
            user_id=str(user.id),
            file_name="sample.md",
            storage_key=key,
            status=1,
        )
        db.add(file)
        await db.commit()
        file_id, user_id = file.id, user.id
    await storage_service.put_bytes(key, raw)
    yield sessions, file_id, user_id, calls
    if os.environ.get("RAG_TEST_REAL_ES"):
        await elasticsearch_service.delete_file(hashlib.md5(raw).hexdigest(), str(user_id))
        await elasticsearch_service.close()
    await engine.dispose()


async def build(sessions, file_id):
    async with sessions() as db:
        await process_file(db, file_id)


async def _owner_id(sessions, file_id):
    async with sessions() as db:
        return (await db.get(FileUpload, file_id)).user_id


@pytest.mark.asyncio
async def test_two_claims_only_one_wins_and_other_document_can_run(setup_build):
    sessions, file_id, _, _ = setup_build
    claims = await asyncio.gather(
        claim_document(sessions, file_id), claim_document(sessions, file_id), return_exceptions=True
    )
    assert sum(not isinstance(c, Exception) for c in claims) == 1
    assert sum(isinstance(c, IndexBusy) for c in claims) == 1
    async with sessions() as db:
        original = await db.get(FileUpload, file_id)
        other = FileUpload(
            file_name="other.md", file_md5=uuid.uuid4().hex, user_id=original.user_id, storage_key="other"
        )
        db.add(other)
        await db.commit()
        other_id = other.id
    assert await claim_document(sessions, other_id)


@pytest.mark.asyncio
async def test_gc_interleaved_with_new_publication_keeps_new_version(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        old = (await db.get(FileUpload, file_id)).active_vector_version
    await build(sessions, file_id)
    async with sessions() as db:
        now = await database_now(db)
        await db.execute(
            update(IndexBuild).where(IndexBuild.build_id == old).values(updated_at=now - timedelta(seconds=2))
        )
        await db.commit()
    entered, resume = asyncio.Event(), asyncio.Event()
    original = elasticsearch_service.delete_version

    async def gated(md5, owner, version):
        if version == old:
            entered.set()
            await resume.wait()
        await original(md5, owner, version)

    monkeypatch.setattr(elasticsearch_service, "delete_version", gated)
    gc = asyncio.create_task(collect_garbage(sessions=sessions, retention_seconds=0, document_id=file_id))
    await asyncio.wait_for(entered.wait(), 10)
    try:
        await build(sessions, file_id)
    finally:
        resume.set()
    await gc
    async with sessions() as db:
        active = (await db.get(FileUpload, file_id)).active_vector_version
        assert active != old and await db.scalar(
            select(func.count()).select_from(DocumentVector).where(DocumentVector.vector_version == active)
        )


@pytest.mark.asyncio
async def test_duplicate_job_and_healthy_restart(setup_build, monkeypatch):
    from app.documents import job_runtime as jobs

    sessions, file_id, _, _ = setup_build
    one = await jobs.create_processing_job(file_id)
    assert await jobs.create_processing_job(file_id) == one
    claims = await asyncio.gather(jobs.claim_job(one), jobs.claim_job(one))
    assert sum(c is not None for c in claims) == 1
    dispatched = []

    async def capture(job_id):
        dispatched.append(job_id)

    monkeypatch.setattr(jobs, "dispatch_processing_job", capture)
    await jobs.resume_processing_jobs(user_id=(await _owner_id(sessions, file_id)))
    assert one not in dispatched


@pytest.mark.asyncio
async def test_old_execution_cannot_overwrite_new_build(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    entered, resume = asyncio.Event(), asyncio.Event()
    original = embedding_service.embed
    count = 0

    async def gated(texts):
        nonlocal count
        count += 1
        if count == 1:
            entered.set()
            await resume.wait()
        return await original(texts)

    monkeypatch.setattr(embedding_service, "embed", gated)
    old = asyncio.create_task(build(sessions, file_id))
    await asyncio.wait_for(entered.wait(), 10)
    async with sessions() as db:
        now = await database_now(db)
        await db.execute(
            update(FileUpload).where(FileUpload.id == file_id).values(lease_until=now - timedelta(seconds=1))
        )
        await db.commit()
    await build(sessions, file_id)
    async with sessions() as db:
        winner = (await db.get(FileUpload, file_id)).active_vector_version
    resume.set()
    with pytest.raises(LeaseLost):
        await old
    async with sessions() as db:
        assert (await db.get(FileUpload, file_id)).active_vector_version == winner
        assert (await db.get(IndexBuild, winner)).status == "PUBLISHED"


@pytest.mark.asyncio
async def test_failed_rebuild_preserves_active_and_gc_never_deletes_it(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        active = (await db.get(FileUpload, file_id)).active_vector_version

    async def broken(*args):
        raise RuntimeError("injected ES bulk failure")

    monkeypatch.setattr(elasticsearch_service, "bulk_index", broken)
    with pytest.raises(RuntimeError, match="injected"):
        await build(sessions, file_id)
    await collect_garbage(sessions=sessions, retention_seconds=0, document_id=file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        assert file.active_vector_version == active
        assert await db.scalar(
            select(func.count()).select_from(DocumentVector).where(DocumentVector.vector_version == active)
        )


@pytest.mark.asyncio
async def test_deletion_during_build_prevents_resurrection(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    original = embedding_service.embed

    async def delete_while_encoding(texts):
        async with sessions() as db:
            await tombstone_document(db, file_id)
        return await original(texts)

    monkeypatch.setattr(embedding_service, "embed", delete_while_encoding)
    with pytest.raises(LeaseLost):
        await build(sessions, file_id)
    await collect_garbage(sessions=sessions, retention_seconds=0, document_id=file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        assert file.deleted_at is not None and file.active_vector_version is None
        assert not await db.scalar(
            select(func.count()).select_from(DocumentVector).where(DocumentVector.file_md5 == file.file_md5)
        )


@pytest.mark.asyncio
async def test_known_usage_is_settled_once_even_when_replayed(setup_build):
    sessions, file_id, user_id, calls = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        attempts = list(
            (
                await db.scalars(
                    select(EmbeddingAttempt)
                    .join(IndexBuild, IndexBuild.build_id == EmbeddingAttempt.build_id)
                    .where(IndexBuild.file_id == file_id)
                )
            ).all()
        )
        before = (await db.get(User, user_id)).embedding_token_balance
    for a in attempts:
        await settle_attempt(sessions, a.attempt_id, user_id)
    async with sessions() as db:
        assert (await db.get(User, user_id)).embedding_token_balance == before == 10000 - 3 * len(attempts)
    assert calls


@pytest.mark.asyncio
async def test_partial_gc_can_retry_without_touching_active(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    await build(sessions, file_id)
    await build(sessions, file_id)
    async with sessions() as db:
        now = await database_now(db)
        await db.execute(
            update(IndexBuild)
            .where(IndexBuild.file_id == file_id, IndexBuild.status == "SUPERSEDED")
            .values(updated_at=now - timedelta(seconds=2))
        )
        await db.commit()
    original = elasticsearch_service.delete_version

    async def fail(*args):
        raise RuntimeError("GC backend unavailable")

    monkeypatch.setattr(elasticsearch_service, "delete_version", fail)
    with pytest.raises(RuntimeError):
        await collect_garbage(sessions=sessions, retention_seconds=0, document_id=file_id)
    monkeypatch.setattr(elasticsearch_service, "delete_version", original)
    await collect_garbage(sessions=sessions, retention_seconds=0, document_id=file_id)
    async with sessions() as db:
        active = (await db.get(FileUpload, file_id)).active_vector_version
        assert await db.scalar(
            select(func.count()).select_from(DocumentVector).where(DocumentVector.vector_version == active)
        )


@pytest.mark.asyncio
async def test_es_stale_acl_missing_document_and_legacy_are_rejected(setup_build):
    from app.knowledge.rag import rag_service

    sessions, file_id, user_id, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        candidate = {
            "fileMd5": file.file_md5,
            "ownerUserId": str(user_id),
            "indexVersion": file.active_vector_version,
        }
        outsider = User(id=9999999, username="outsider", password="unused", role="USER")
        assert not await rag_service._filter_active_versions(db, [candidate], 6, outsider)
        missing = {**candidate, "fileMd5": "0" * 32, "indexVersion": "legacy"}
        assert not await rag_service._filter_active_versions(db, [missing], 6, await db.get(User, user_id))


@pytest.mark.asyncio
async def test_publication_response_lost_does_not_delete_published_build(setup_build, monkeypatch):
    from app.knowledge import build_pipeline

    sessions, file_id, _, _ = setup_build
    original = build_pipeline._build

    async def committed_then_disconnected(*args):
        await original(*args)
        raise RuntimeError("injected lost publication acknowledgement")

    monkeypatch.setattr(build_pipeline, "_build", committed_then_disconnected)
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        assert file.active_vector_version
        assert (await db.get(IndexBuild, file.active_vector_version)).status == "PUBLISHED"


@pytest.mark.asyncio
async def test_metadata_change_fences_inflight_build(setup_build, monkeypatch):
    sessions, file_id, _, _ = setup_build
    original = embedding_service.embed

    async def update_during_encoding(texts):
        async with sessions() as db:
            await db.execute(
                update(FileUpload)
                .where(FileUpload.id == file_id)
                .values(input_revision=FileUpload.input_revision + 1)
            )
            await db.commit()
        return await original(texts)

    monkeypatch.setattr(embedding_service, "embed", update_during_encoding)
    with pytest.raises(LeaseLost):
        await build(sessions, file_id)
    async with sessions() as db:
        assert not (await db.get(FileUpload, file_id)).active_vector_version


@pytest.mark.asyncio
async def test_lost_notification_is_scanned_and_completed_request_is_reused(setup_build, monkeypatch):
    from app.documents import job_runtime as jobs

    sessions, file_id, _, calls = setup_build
    monkeypatch.setattr(get_settings(), "task_mode", "background")
    job_id = await jobs.create_processing_job(file_id)
    async with sessions() as db:
        assert await db.scalar(select(IndexOutbox).where(IndexOutbox.job_id == job_id))
    await jobs.resume_processing_jobs(user_id=(await _owner_id(sessions, file_id)))
    async with sessions() as db:
        assert (await db.get(ProcessingJob, job_id)).status == "COMPLETED"
    count = len(calls)
    reused = await jobs.create_processing_job(file_id)
    await jobs.run_processing_job(reused)
    assert len(calls) == count


@pytest.mark.asyncio
async def test_current_acl_revocation_and_version_bound_citation(setup_build):
    from app.api.v1.documents import read_citation
    from app.knowledge.citations import issue_citation
    from fastapi import HTTPException

    sessions, file_id, user_id, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        owner = await db.get(User, user_id)
        token = issue_citation(str(user_id), file.file_md5, file.active_vector_version, 0)
        detail=(await read_citation(token, owner, db))["data"]
        assert detail['textContent'] and detail['contextText']
        document_token=issue_citation(str(user_id),file.file_md5,file.active_vector_version,0,scope='document',max_chars=5000)
        document_detail=(await read_citation(document_token,owner,db))['data']
        assert document_detail['contextType']=='document' and document_detail['contextText']
    await build(sessions, file_id)
    async with sessions() as db:
        with pytest.raises(HTTPException) as error:
            await read_citation(token, await db.get(User, user_id), db)
        assert error.value.status_code == 410


@pytest.mark.asyncio
async def test_desired_metadata_does_not_relabel_old_active_version(setup_build, monkeypatch):
    from app.knowledge.metadata import stage_metadata

    sessions, file_id, _, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        active = file.active_vector_version
        stage_metadata(file, {"product": "new-product", "version": "v2"})
        file.input_revision += 1
        await db.commit()
        assert file.knowledge_product is None
    original = embedding_service.embed

    async def fail(texts):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(embedding_service, "embed", fail)
    with pytest.raises(RuntimeError):
        await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        assert file.active_vector_version == active and file.knowledge_product is None
    monkeypatch.setattr(embedding_service, "embed", original)
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        assert file.knowledge_product == "new-product" and file.knowledge_version == "v2"
        assert file.desired_metadata_json is None


@pytest.mark.asyncio
async def test_malformed_response_with_known_usage_is_still_accounted(setup_build, monkeypatch):
    sessions, file_id, user_id, _ = setup_build

    async def malformed(texts):
        record_embedding_usage({"total_tokens": 7}, "fixture-request-id")
        return []

    monkeypatch.setattr(embedding_service, "embed", malformed)
    with pytest.raises(ValueError):
        await build(sessions, file_id)
    async with sessions() as db:
        assert (await db.get(User, user_id)).embedding_token_balance == 9993
        attempt = await db.scalar(
            select(EmbeddingAttempt)
            .join(IndexBuild, IndexBuild.build_id == EmbeddingAttempt.build_id)
            .where(IndexBuild.file_id == file_id)
        )
        assert attempt.status == "KNOWN" and "fixture-request-id" in attempt.provider_request_ids_json


@pytest.mark.asyncio
async def test_publication_commit_failure_rolls_back_pointer(setup_build, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    sessions, file_id, _, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        old = (await db.get(FileUpload, file_id)).active_vector_version
    original = AsyncSession.commit
    failed = False

    async def injected(db):
        nonlocal failed
        if not failed:
            version = await db.scalar(
                select(FileUpload.active_vector_version).where(FileUpload.id == file_id)
            )
            if version and version != old:
                failed = True
                raise RuntimeError("injected publication DB commit failure")
        return await original(db)

    monkeypatch.setattr(AsyncSession, "commit", injected)
    with pytest.raises(RuntimeError, match="commit failure"):
        await build(sessions, file_id)
    assert failed
    async with sessions() as db:
        assert (await db.get(FileUpload, file_id)).active_vector_version == old


@pytest.mark.asyncio
async def test_bounded_refill_after_stale_candidates_and_backend_status(setup_build, monkeypatch):
    from app.knowledge.rag import rag_service

    sessions, file_id, user_id, _ = setup_build
    await build(sessions, file_id)
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        owner = await db.get(User, user_id)
        valid = {
            "fileMd5": file.file_md5,
            "ownerUserId": str(user_id),
            "indexVersion": file.active_vector_version,
            "chunkId": 0,
            "textContent": "401 token",
            "fileName": file.file_name,
            "score": 1.0,
        }
        limits = []

        async def candidates(user, query, vector, limit, **kwargs):
            limits.append(limit)
            return [{**valid, "indexVersion": "stale"}] if len(limits) == 1 else [valid]

        monkeypatch.setattr(get_settings(), "search_backend", "elasticsearch")
        monkeypatch.setattr(elasticsearch_service, "search", candidates)
        result = await rag_service.search(db, owner, "401", 1)
        assert result and len(limits) == 2 and limits[1] > limits[0]

        async def unavailable(*args, **kwargs):
            raise RuntimeError("injected backend outage")

        monkeypatch.setattr(rag_service, "search", unavailable)
        assert (await rag_service.search_evidence(db, owner, "401"))["status"] == "BACKEND_UNAVAILABLE"


@pytest.mark.asyncio
async def test_conflicting_declared_rules_keep_both_sources(setup_build, monkeypatch):
    from app.knowledge.rag import rag_service

    sessions, _, user_id, _ = setup_build

    async def conflicting(*args, **kwargs):
        return [
            {
                "product": "Test API",
                "knowledgeVersion": "v1",
                "region": "CN",
                "fileName": name,
                "textContent": f"rag-claim: auth.invalid.http_status={status}",
            }
            for name, status in [("source-a.md", 401), ("source-b.md", 403)]
        ]

    monkeypatch.setattr(rag_service, "search", conflicting)
    async with sessions() as db:
        result = await rag_service.search_evidence(
            db,
            await db.get(User, user_id),
            "invalid token",
            metadata_filters={"product": "Test API", "version": "v1"},
        )
    assert result["status"] == "CONFLICT" and len(result["results"]) == 2
    assert {a["value"] for a in result["conflicts"][0]["alternatives"]} == {"401", "403"}


@pytest.mark.asyncio
async def test_explicit_rebuild_key_survives_completed_request_replay(setup_build):
    from app.documents import job_runtime as jobs

    sessions, file_id, _, calls = setup_build
    first = await jobs.create_processing_job(file_id, force=True, idempotency_key="rebuild-001")
    await jobs.run_processing_job(first)
    count = len(calls)
    assert await jobs.create_processing_job(file_id, force=True, idempotency_key="rebuild-001") == first
    await jobs.run_processing_job(first)
    assert len(calls) == count
    async with sessions() as db:
        await db.execute(update(FileUpload).where(FileUpload.id == file_id).values(input_revision=1))
        await db.commit()
    with pytest.raises(ValueError, match="different input revision"):
        await jobs.create_processing_job(file_id, force=True, idempotency_key="rebuild-001")


@pytest.mark.asyncio
async def test_legacy_running_job_without_a_lease_can_be_recovered(setup_build):
    from app.documents import job_runtime as jobs

    sessions, file_id, _, _ = setup_build
    job_id = await jobs.create_processing_job(file_id)
    async with sessions() as db:
        await db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.job_id == job_id)
            .values(status="RUNNING", lease_owner=None, lease_until=None)
        )
        await db.commit()
    assert await jobs.claim_job(job_id) is not None


@pytest.mark.asyncio
async def test_stable_document_content_revisions_and_identical_independent_documents(setup_build):
    import io
    from fastapi import BackgroundTasks, UploadFile, HTTPException
    from app.documents.revisions import create_content_document, replace_content_revision
    from app.documents import job_runtime as jobs

    sessions, _, user_id, _ = setup_build
    raw = b"# Stable document\nOriginal authentication rule: HTTP 401."
    async with sessions() as db:
        user = await db.get(User, user_id)
        first = (
            await create_content_document(
                BackgroundTasks(), UploadFile(filename="same.md", file=io.BytesIO(raw)), "{}", user, db
            )
        )["data"]
        second = (
            await create_content_document(
                BackgroundTasks(), UploadFile(filename="same.md", file=io.BytesIO(raw)), "{}", user, db
            )
        )["data"]
    assert first["documentId"] != second["documentId"] and first["fileMd5"] != second["fileMd5"]
    assert first["contentMd5"] == second["contentMd5"]
    await jobs.run_processing_job(first["processingJobId"])
    changed = b"# Stable document\nUpdated authentication rule: HTTP 403."
    async with sessions() as db:
        user = await db.get(User, user_id)
        update_data = (
            await replace_content_revision(
                first["documentId"],
                BackgroundTasks(),
                UploadFile(filename="updated.md", file=io.BytesIO(changed)),
                0,
                "{}",
                user,
                db,
            )
        )["data"]
        document = await db.get(FileUpload, first["documentId"])
        assert update_data["documentId"] == first["documentId"] and update_data["fileMd5"] == first["fileMd5"]
        assert await storage_service.get_bytes(document.active_source_key) == raw
        with pytest.raises(HTTPException) as error:
            await replace_content_revision(
                first["documentId"],
                BackgroundTasks(),
                UploadFile(filename="updated.md", file=io.BytesIO(changed)),
                0,
                "{}",
                user,
                db,
            )
        assert error.value.status_code == 409
    await jobs.run_processing_job(update_data["processingJobId"])
    async with sessions() as db:
        document = await db.get(FileUpload, first["documentId"])
        assert document.active_file_name == "updated.md"
        assert await storage_service.get_bytes(document.active_source_key) == changed


@pytest.mark.asyncio
async def test_seed_reset_updates_content_in_place_without_erasing_identity(
    setup_build, tmp_path, monkeypatch
):
    import json
    import app.db.session as session_module
    import app.db.init_db as initializer
    from scripts.seed_demo_knowledge import seed

    sessions, _, user_id, _ = setup_build
    monkeypatch.setattr(session_module, "SessionLocal", sessions)

    async def ready():
        pass

    monkeypatch.setattr(initializer, "init_db", ready)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"documents": [{"file": "seed-source.md", "metadata": {"product": "Seed test"}}]})
    )
    source = tmp_path / "seed-source.md"
    source.write_text("# Seed source\nOriginal rule: HTTP 401.")
    async with sessions() as db:
        username = (await db.get(User, user_id)).username
    await seed(username, reset=False, reindex=False, is_public=False, org_tag="", manifest_path=manifest)
    async with sessions() as db:
        original = await db.scalar(
            select(FileUpload).where(
                FileUpload.file_name == "seed-source.md", FileUpload.user_id == str(user_id)
            )
        )
        file_id, handle = original.id, original.file_md5
    source.write_text("# Seed source\nUpdated rule: HTTP 403.")
    await seed(username, reset=True, reindex=False, is_public=False, org_tag="", manifest_path=manifest)
    async with sessions() as db:
        document = await db.get(FileUpload, file_id)
        assert document.file_md5 == handle and document.deleted_at is None
        assert await storage_service.get_bytes(document.active_source_key) == source.read_bytes()


@pytest.mark.asyncio
async def test_obsolete_pending_requests_do_not_starve_current_revision(setup_build, monkeypatch):
    from app.documents import job_runtime as jobs

    sessions, file_id, user_id, _ = setup_build
    old = await jobs.create_processing_job(file_id)
    async with sessions() as db:
        await db.execute(update(FileUpload).where(FileUpload.id == file_id).values(input_revision=1))
        await db.commit()
    current = await jobs.create_processing_job(file_id)
    dispatched = []

    async def capture(job_id):
        dispatched.append(job_id)

    monkeypatch.setattr(jobs, "dispatch_processing_job", capture)
    await jobs.resume_processing_jobs(user_id=user_id)
    assert dispatched == [current]
    async with sessions() as db:
        assert (await db.get(ProcessingJob, old)).status == "CANCELLED"
