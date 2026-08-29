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
