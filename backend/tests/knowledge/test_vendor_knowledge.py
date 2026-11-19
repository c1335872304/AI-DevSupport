from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.seed_demo_knowledge import load_manifest


ROOT = Path(__file__).resolve().parents[2]
VENDOR_MANIFEST = ROOT / "demo_knowledge" / "vendor-manifest.json"


def test_vendor_sources_have_distinct_products_and_checked_snapshots():
    manifest = load_manifest(VENDOR_MANIFEST)
    assert len(manifest["documents"]) == 9
    products = {item["metadata"]["product"] for item in manifest["documents"]}
    assert products == {"OpenAI API", "Anthropic Claude API", "DeepSeek API"}
    assert "API Platform" not in products
    for item in manifest["documents"]:
        text = (VENDOR_MANIFEST.parent / item["file"]).read_text(encoding="utf-8")
        assert item["sourceUrl"] in text
        assert item["checkedAt"] in text
        assert item["contentType"] == "attributed_summary"
        # Capture date must not silently become a vendor policy's effective date.
        assert "effectiveDate" not in item["metadata"]


def test_alternate_manifest_resolves_files_beside_it_and_detects_changes(tmp_path):
    document = tmp_path / "example.md"
    document.write_text("# Example\n\nSnapshot content", encoding="utf-8")
    manifest = tmp_path / "custom.json"
    manifest.write_text(json.dumps({"documents": [{
        "file": document.name,
        "sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
    }]}), encoding="utf-8")
    assert load_manifest(manifest)["documents"][0]["file"] == document.name
    document.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_manifest(manifest)


def test_vendor_eval_separates_given_filters_from_natural_queries():
    manifest = load_manifest(VENDOR_MANIFEST)
    shipped = {item["file"] for item in manifest["documents"]}
    cases = [json.loads(line) for line in
             (ROOT / manifest["evaluationDataset"]).read_text(encoding="utf-8").splitlines()]
    filtered = [case for case in cases if case["caseType"] == "filtered_smoke"]
    natural = [case for case in cases if case["caseType"] == "unfiltered_query"]
    assert len(filtered) == len(natural) == 9
    assert {case["expectedFileName"] for case in cases} == shipped
    assert all(case.get("filters", {}).get("product") for case in filtered)
    assert all("filters" not in case for case in natural)


@pytest.mark.asyncio
async def test_vendor_documents_index_and_retrieve_with_product_boundaries(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.db.models import Base, DocumentVector, FileUpload, User
    from app.documents.storage import storage_service
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.knowledge.embedding import embedding_service
    from app.knowledge.indexer import process_file
    from app.knowledge.metadata import apply_metadata_to_file
    from app.knowledge.parser import parser_service
    from app.knowledge.rag import rag_service

    settings = get_settings()
    # Fixed test fixture for plumbing/ACL only, never a runtime embedding backend
    # or a claim about retrieval quality. Real Qwen is verified separately.
    encoded_texts = []

    async def fixture_vectors(texts):
        encoded_texts.extend(texts)
        return [[1.0] + [0.0] * (settings.embedding_dimension - 1) for _ in texts]

    monkeypatch.setattr(embedding_service, "embed", fixture_vectors)
    monkeypatch.setattr(settings, "search_backend", "database")
    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(storage_service, "backend", "local")
    monkeypatch.setattr(storage_service, "_minio", None)
    monkeypatch.setattr(elasticsearch_service, "client", None)
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'vendor.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            user = User(id=1, username="vendor-test", password="unused", role="USER",
                        embedding_token_balance=100000)
            db.add(user)
            await db.commit()
            manifest = load_manifest(VENDOR_MANIFEST)
            expected_children = []
            for item in manifest["documents"]:
                raw = (VENDOR_MANIFEST.parent / item["file"]).read_bytes()
                _, children = parser_service.hierarchical_chunk(parser_service.parse(item["file"], raw))
                expected_children.extend(child.text for child in children)
                key = f"test/{item['file']}"
                await storage_service.put_bytes(key, raw)
                document = FileUpload(file_md5=hashlib.md5(raw).hexdigest(), file_name=item["file"],
                                      total_size=len(raw), status=1, user_id="1", is_public=False,
                                      storage_key=key)
                apply_metadata_to_file(document, item["metadata"])
                db.add(document)
                await db.commit()
                await process_file(db, document.id)
            # The indexer must send child text exactly once; parents are stored as
            # context and must not cause a second embedding pass.
            assert encoded_texts == expected_children
            for name, model, dimension in [
                ("obsolete-encoding.md", "obsolete-model", settings.embedding_dimension),
                ("wrong-dimension.md", settings.embedding_model, settings.embedding_dimension // 2),
            ]:
                identity = hashlib.md5(name.encode()).hexdigest()
                old = FileUpload(file_md5=identity, file_name=name, user_id="1", status=1,
                                 active_vector_version="old", process_status="COMPLETED")
                apply_metadata_to_file(old, {"product": "DeepSeek API"})
                db.add(old)
                db.add(DocumentVector(file_md5=identity, user_id="1", vector_version="old", chunk_id=0,
                                      model_version=model, text_content="DeepSeek 401 402 429",
                                      vector_json=json.dumps([1.0] + [0.0] * (dimension - 1))))
            await db.commit()
            for item in manifest["documents"]:
                results = await rag_service.search(db, user, item["sampleQuestions"][0], 6,
                                                  metadata_filters={"product": item["metadata"]["product"]})
                assert results
                assert all(result["product"] == item["metadata"]["product"] for result in results)
                assert item["file"] in {result["fileName"] for result in results}
                assert not {"obsolete-encoding.md", "wrong-dimension.md"}.intersection(
                    result["fileName"] for result in results)
            # Local simulated business rules cannot accidentally include vendor documents
            # when the caller explicitly selects that local product scope.
            assert not await rag_service.search(db, user, "401 429", 6,
                                                metadata_filters={"product": "API Platform"})
            outsider = User(id=2, username="outsider", password="unused", role="USER")
            assert not await rag_service.search(db, outsider, "DeepSeek 402", 6)
    finally:
        await engine.dispose()
