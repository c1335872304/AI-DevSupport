from __future__ import annotations

import hashlib

import pytest

from app.knowledge.elasticsearch import elasticsearch_service
from app.documents.storage import storage_service


@pytest.mark.asyncio
async def test_local_merge_parts_is_streamed_and_validated(tmp_path):
    old_dir = storage_service.settings.local_storage_dir
    old_backend = storage_service.backend
    old_minio = storage_service._minio
    try:
        storage_service.settings.local_storage_dir = str(tmp_path)
        storage_service.backend = "local"
        storage_service._minio = None
        (tmp_path / "chunks").mkdir()
        (tmp_path / "chunks/a.part").write_bytes(b"abc")
        (tmp_path / "chunks/b.part").write_bytes(b"defgh")

        size, md5 = await storage_service.merge_parts(
            "uploads/merged.bin", ["chunks/a.part", "chunks/b.part"]
        )
        assert size == 8
        assert md5 == hashlib.md5(b"abcdefgh").hexdigest()
        assert (tmp_path / "uploads/merged.bin").read_bytes() == b"abcdefgh"
    finally:
        storage_service.settings.local_storage_dir = old_dir
        storage_service.backend = old_backend
        storage_service._minio = old_minio


class _FakeIndices:
    async def exists(self, *, index):
        return True

    async def get_mapping(self, *, index):
        return {index: {"mappings": {"properties": {"indexVersion": {"type": "keyword"}}}}}

    async def put_mapping(self, *, index, properties):
        return {"acknowledged": True}


class _FakeElasticsearch:
    def __init__(self):
        self.indices = _FakeIndices()
        self.operations = None

    async def bulk(self, *, operations, refresh):
        self.operations = operations
        return {"errors": False, "items": []}


@pytest.mark.asyncio
async def test_elasticsearch_bulk_index_uses_one_bulk_request():
    old_client = elasticsearch_service.client
    fake = _FakeElasticsearch()
    elasticsearch_service.client = fake  # type: ignore[assignment]
    try:
        documents = [
            {"userId": "1", "fileMd5": "a" * 32, "chunkId": 0, "textContent": "a", "vector": [0.1]},
            {"userId": "1", "fileMd5": "a" * 32, "chunkId": 1, "textContent": "b", "vector": [0.2]},
        ]
        await elasticsearch_service.bulk_index(documents)
        assert fake.operations is not None
        assert len(fake.operations) == 4
        assert fake.operations[0]["index"]["_id"].endswith(":0")
        assert fake.operations[2]["index"]["_id"].endswith(":1")
    finally:
        elasticsearch_service.client = old_client

from app.agent.chat import self_contained_query
from app.agent.llm import llm_service


def test_follow_up_query_uses_previous_user_turn():
    history = [
        {"role": "user", "content": "Python 的 GIL 是什么？"},
        {"role": "assistant", "content": "GIL 是全局解释器锁。"},
    ]
    rewritten = self_contained_query("那它为什么影响多线程？", history)
    assert "Python 的 GIL 是什么" in rewritten
    assert "那它为什么影响多线程" in rewritten


def test_llm_messages_include_history_before_current_rag_context():
    messages = llm_service.build_messages(
        "它会影响什么？",
        [{"fileName": "python.md", "textContent": "GIL affects CPU-bound threads", "pageNumber": 2}],
        [
            {"role": "user", "content": "GIL 是什么？"},
            {"role": "assistant", "content": "它是全局解释器锁。"},
        ],
    )
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert "GIL affects CPU-bound threads" in messages[-1]["content"]

from app.core.config import Settings
from app.documents.upload import upload_service


def test_upload_filename_blocks_path_traversal_by_using_basename():
    assert upload_service._safe_file_name('../../secret/report.pdf') == 'report.pdf'
    assert upload_service._safe_file_name(r'C:\\Users\\alice\\notes.txt') == 'notes.txt'
    with pytest.raises(ValueError):
        upload_service._safe_file_name('../..')


def test_production_rejects_default_security_credentials():
    settings = Settings(app_env='production')
    with pytest.raises(RuntimeError):
        settings.validate_runtime_safety()
