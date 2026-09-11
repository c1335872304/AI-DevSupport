import pytest

from app.knowledge.embedding import embedding_service


@pytest.mark.asyncio
async def test_local_embedding_is_deterministic():
    old_key = embedding_service.settings.embedding_api_key
    embedding_service.settings.embedding_api_key = ""
    try:
        a = await embedding_service.embed_one("Spring Bean 生命周期")
        b = await embedding_service.embed_one("Spring Bean 生命周期")
        c = await embedding_service.embed_one("完全不相关的天气话题")
        assert a == b
        assert embedding_service.cosine(a, b) > embedding_service.cosine(a, c)
    finally:
        embedding_service.settings.embedding_api_key = old_key


@pytest.mark.asyncio
async def test_qwen_remote_embedding_requests_configured_dimension(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class FakeResponse:
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
