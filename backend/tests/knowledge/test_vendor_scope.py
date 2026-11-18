"""Product scope is enforced by DB authorization even when ES returns bad hits."""

import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, DocumentVector, FileUpload, User
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.embedding import embedding_service
from app.knowledge.rag import rag_service


@pytest.mark.parametrize("backend", ["database", "elasticsearch"])
@pytest.mark.parametrize(
    "query,products",
    [
        ("OpenAI认证如何设置", {"OpenAI API"}),
        ("千问的流式输出怎么用", {"Qwen API"}),
        ("DeepSeek的错误码是什么", {"DeepSeek API"}),
        ("比较OpenAI和Qwen的认证", {"OpenAI API", "Qwen API"}),
    ],
)
async def test_vendor_scope_across_backends_and_final_authorization(
    tmp_path, monkeypatch, backend, query, products
):
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "scope.db").as_posix())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    candidates = []
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add_all(
                [User(id=1, username="reader", password="x"), User(id=2, username="owner", password="x")]
            )
            for n, product in enumerate(["OpenAI API", "Qwen API", "DeepSeek API", "OpenAI API"]):
                handle = str(n) * 32
                db.add(
                    FileUpload(
                        file_md5=handle,
                        file_name=f"doc{n}.md",
                        user_id="2",
                        is_public=n != 3,
                        active_vector_version="v1",
                        knowledge_product=product,
                        status=1,
                        process_status="COMPLETED",
                    )
                )
                db.add(
                    DocumentVector(
                        file_md5=handle,
                        user_id="2",
                        is_public=n != 3,
                        chunk_id=0,
                        vector_version="v1",
                        text_content="认证与流式接口",
                        model_version=embedding_service.settings.embedding_model,
                        vector_json=json.dumps([1.0, 0.0]),
                    )
                )
                candidates.append(
                    {
                        "fileMd5": handle,
                        "fileName": f"doc{n}.md",
                        "ownerUserId": "2",
                        "indexVersion": "v1",
                        "chunkId": 0,
                        "textContent": "认证与流式接口",
                        "score": 1.0,
                        "product": product,
                    }
                )
            await db.commit()
        monkeypatch.setattr(rag_service.settings, "search_backend", backend)
        monkeypatch.setattr(rag_service.settings, "embedding_dimension", 2)

        async def embed(_texts):
            return [[1.0, 0.0]]

        async def es_search(*args, **kwargs):
            assert (
                set(
                    kwargs["metadata_filters"]["product"]
                    if isinstance(kwargs["metadata_filters"]["product"], list)
                    else [kwargs["metadata_filters"]["product"]]
                )
                == products
            )
            # Deliberately ignore both product and ACL filters, like a stale ES projection.
            return candidates

        monkeypatch.setattr(embedding_service, "embed", embed)
        monkeypatch.setattr(elasticsearch_service, "search", es_search)
        async with sessions() as db:
            results = await rag_service.search(db, await db.get(User, 1), query, 6)
            assert results and {r["product"] for r in results} == products
            assert all(r["fileName"] != "doc3.md" and r.get("citationId") for r in results)
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    "query,expected",
    [
        ("GPT-4o API认证", ["OpenAI API"]),
        ("Qwen3-235B API", ["Qwen API"]),
        ("深度求索接口", ["DeepSeek API"]),
        ("myopenaihelper和fqwenxy", []),
        ("API错误如何处理", []),
        ("OpenAI与DeepSeek对比", ["OpenAI API", "DeepSeek API"]),
        ("Qwen如何通过OpenAI兼容批量接口提交任务", ["Qwen API"]),
        ("DeepSeek如何使用OpenAI Python SDK", ["DeepSeek API"]),
        ("比较Qwen与OpenAI SDK的用法", ["OpenAI API", "Qwen API"]),
    ],
)
def test_vendor_aliases_and_ambiguous_query(query, expected):
    from app.knowledge.product_scope import named_products

    assert named_products(query) == expected


async def test_conflicting_explicit_filter_requests_clarification_without_encoding(monkeypatch):
    async def never_encode(_texts):
        raise AssertionError("Conflict must not call provider")

    monkeypatch.setattr(embedding_service, "embed", never_encode)
    result = await rag_service.search_evidence(None, None, "OpenAI认证", 6, {"product": "Qwen API"})
    assert result["status"] == "NEEDS_CLARIFICATION" and result["results"] == []
    assert result["warnings"] == ["product_scope_conflict"]


@pytest.mark.parametrize("backend", ["database", "elasticsearch"])
async def test_untagged_filters_require_body_evidence(tmp_path, monkeypatch, backend):
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "fallback.db").as_posix())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases = [
        ("slow_down applies to Professional", None, None),
        ("slow_down applies to Professional", "rate_limit", None),
        ("slow_down applies to Professional", None, "Basic"),
        ("slow_down_extra applies to Professional", None, None),
        ("slow_down applies to Professionals", None, None),
        ("a generic description", "slow_down", "Professional"),
        ("slow_down applies to Professional", None, None),
    ]
    candidates = []
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add_all([User(id=1, username="reader", password="x"), User(id=2, username="owner", password="x")])
            for index, (body, code, plan) in enumerate(cases):
                md5 = str(index) * 32
                name = f"error-{index}.md"
                db.add(FileUpload(file_md5=md5, file_name=name, user_id="2", is_public=index != 6,
                                  knowledge_product="OpenAI API", knowledge_error_code=code, knowledge_plan=plan))
                db.add(DocumentVector(file_md5=md5, user_id="2", chunk_id=0, text_content=body,
                                      model_version=rag_service.settings.embedding_model, vector_json="[1.0, 0.0]"))
                candidates.append({"fileMd5": md5, "fileName": name, "ownerUserId": "2", "indexVersion": "legacy",
                                   "chunkId": 0, "textContent": body, "score": 1.0})
            await db.commit()

        async def embed(_texts):
            return [[1.0, 0.0]]

        async def es_search(*_args, **_kwargs):
            return candidates

        monkeypatch.setattr(rag_service.settings, "search_backend", backend)
        monkeypatch.setattr(rag_service.settings, "embedding_dimension", 2)
        monkeypatch.setattr(embedding_service, "embed", embed)
        monkeypatch.setattr(elasticsearch_service, "search", es_search)
        async with sessions() as db:
            result = await rag_service.search_evidence(
                db, await db.get(User, 1), "OpenAI slow_down", 6,
                {"errorCode": ["slow_down", "other_error"], "plan": "Professional"},
            )
        assert result["status"] == "OK"
        assert {hit["fileName"] for hit in result["results"]} == {"error-0.md", "error-5.md"}
        assert result["warnings"] == ["error_code_matched_in_text", "plan_matched_in_text"]
    finally:
        await engine.dispose()
