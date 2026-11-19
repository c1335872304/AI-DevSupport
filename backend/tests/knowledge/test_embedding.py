import pytest

from app.knowledge.embedding import embedding_service


def test_nested_provider_usage_rolls_up_without_double_counting():
    from app.accounting.embedding_usage import capture_embedding_usage, record_embedding_usage

    with capture_embedding_usage() as run:
        record_embedding_usage({"total_tokens": 7})
        with capture_embedding_usage() as document:
            record_embedding_usage({"total_tokens": 100})
            record_embedding_usage({"total_tokens": 50})
        record_embedding_usage({"total_tokens": 3})
    assert document.total_tokens == 150
    assert run.total_tokens == 160


@pytest.mark.asyncio
async def test_missing_key_fails_instead_of_generating_synthetic_vectors(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_api_key", "")
    with pytest.raises(RuntimeError, match="requires EMBEDDING_API_KEY"):
        await embedding_service.embed_one("退款政策")
    assert not hasattr(embedding_service, "_local_hash_embedding")


@pytest.mark.asyncio
async def test_empty_embedding_batch_does_not_require_a_provider_call(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_api_key", "")
    assert await embedding_service.embed([]) == []


@pytest.mark.asyncio
async def test_qwen_remote_embedding_requests_configured_dimension(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class FakeResponse:
        headers = {"x-request-id": "test-provider-request"}
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"index": 0, "embedding": [0.1] * 256}], "usage": {"total_tokens": 1}}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, headers, json):
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.knowledge.embedding.httpx.AsyncClient", FakeClient)
    old_key = embedding_service.settings.embedding_api_key
    old_model = embedding_service.settings.embedding_model
    old_dimension = embedding_service.settings.embedding_dimension
    embedding_service.settings.embedding_api_key = "test-qwen-key"
    embedding_service.settings.embedding_model = "text-embedding-v4"
    embedding_service.settings.embedding_dimension = 256
    try:
        vectors = await embedding_service.embed(["退款政策"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 256
        assert captured["headers"]["Authorization"] == "Bearer test-qwen-key"
        assert captured["json"]["dimensions"] == 256
        assert captured["json"]["encoding_format"] == "float"
    finally:
        embedding_service.settings.embedding_api_key = old_key
        embedding_service.settings.embedding_model = old_model
        embedding_service.settings.embedding_dimension = old_dimension


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [
    [],
    [{"index": 1, "embedding": [0.1] * 256}],
    [{"index": 0, "embedding": [0.1] * 256}, {"index": 0, "embedding": [0.1] * 256}],
    [{"index": 0, "embedding": [0.1] * 128}],
    [{"index": 0, "embedding": [float("nan")] * 256}],
])
async def test_provider_response_must_cover_inputs_with_valid_vectors(monkeypatch, data):
    class Response:
        headers = {}
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": data}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("app.knowledge.embedding.httpx.AsyncClient", Client)
    monkeypatch.setattr(embedding_service.settings, "embedding_api_key", "unit-test-only")
    monkeypatch.setattr(embedding_service.settings, "embedding_dimension", 256)
    with pytest.raises(RuntimeError):
        await embedding_service.embed(["example"])
