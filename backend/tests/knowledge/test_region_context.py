"""Region/units must survive legacy boundaries, retrieval and citation reads."""

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, DocumentParentChunk, DocumentVector, FileUpload, User
from app.knowledge.source_context import parent_contexts


def rows():
    texts = [
        '# 模型价格\n核对日期：2026-10-19。\n<Tab title="北京">\n<table>\n'
        '<thead><tr><th>模型</th><th>单价（每千Token）</th><th>免费额度</th></tr></thead>',
        '<tbody><tr><td>embedding-v4</td><td>0.0005元</td><td>100万Token</td></tr>',
        '</tbody></table></Tab>\n<Tab title="新加坡">\n<table>\n'
        '<thead><tr><th>模型</th><th>单价（每千Token）</th><th>免费额度</th></tr></thead>',
        '<tbody><tr><td>embedding-v4</td><td>0.000514元</td><td>无免费额度</td></tr>',
        '</tbody></table></Tab>\n# 后续\n非地域说明。',
        '下一段独立正文。',
    ]
    return [SimpleNamespace(parent_chunk_id=i, text_content=text) for i, text in enumerate(texts)]


def test_inherited_region_units_date_and_closed_scope():
    contexts = parent_contexts(rows())
    assert '原文适用范围：北京' in contexts[1]
    assert '原文适用范围：新加坡' in contexts[3]
    assert '原文适用范围：北京' not in contexts[3]
    assert '单价（每千Token）' in contexts[3]
    assert '核对日期：2026-10-19' in contexts[3]
    assert '原文适用范围' not in contexts[5] and '原文表头' not in contexts[5]
    assert rows()[3].text_content in contexts[3]


def test_code_example_cannot_change_document_scope():
    items = [SimpleNamespace(parent_chunk_id=0, text_content='```xml\n<Tab title="假地域">\n```'),
             SimpleNamespace(parent_chunk_id=1, text_content='普通规则正文。')]
    assert parent_contexts(items)[1] == '普通规则正文。'


@pytest.mark.parametrize('backend', ['database', 'elasticsearch'])
async def test_legacy_region_context_reaches_search_read_and_signed_citation(tmp_path, monkeypatch, backend):
    from app.api.v1.documents import read_citation
    from app.knowledge.embedding import embedding_service
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.knowledge.rag import rag_service
    from app.tools.base import ToolExecutionContext
    from app.tools.local.knowledge import GetDocumentTool
    import app.db.session as session_module

    engine = create_async_engine('sqlite+aiosqlite:///' + (tmp_path / 'regions.db').as_posix())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    md5 = 'a' * 32
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add_all([User(id=1, username='reader', password='x'), User(id=2, username='owner', password='x')])
            db.add(FileUpload(file_md5=md5, user_id='2', file_name='qwen-prices.md', is_public=True,
                              active_vector_version='v2', knowledge_product='Qwen API'))
            for row in rows():
                db.add(DocumentParentChunk(file_md5=md5, user_id='2', vector_version='v2',
                    parent_chunk_id=row.parent_chunk_id, text_content=row.text_content,
                    start_chunk_id=row.parent_chunk_id * 10, end_chunk_id=row.parent_chunk_id * 10 + 9))
            # Neither another revision nor a private owner's same-content upload may supply qualifiers.
            for owner, version in [('2', 'v1'), ('99', 'v2')]:
                db.add(DocumentParentChunk(file_md5=md5, user_id=owner, vector_version=version,
                    parent_chunk_id=0, text_content='<Tab title="WRONG_SCOPE">', start_chunk_id=0, end_chunk_id=9))
            db.add(DocumentVector(file_md5=md5, user_id='2', chunk_id=30, vector_version='v2',
                text_content=rows()[3].text_content, model_version=rag_service.settings.embedding_model,
                vector_json='[1.0, 0.0]'))
            await db.commit()

        async def embed(_texts):
            return [[1.0, 0.0]]

        async def search(*_args, **_kwargs):
            return [{'fileMd5': md5, 'ownerUserId': '2', 'indexVersion': 'v2',
                     'fileName': 'qwen-prices.md', 'chunkId': 30, 'score': 1.0,
                     'textContent': rows()[3].text_content}]

        monkeypatch.setattr(embedding_service, 'embed', embed)
        monkeypatch.setattr(elasticsearch_service, 'search', search)
        monkeypatch.setattr(rag_service.settings, 'search_backend', backend)
        monkeypatch.setattr(rag_service.settings, 'embedding_dimension', 2)
        monkeypatch.setattr(session_module, 'SessionLocal', sessions)
        async with sessions() as db:
            from app.agent.target_agents import _scope_knowledge_call
            from app.agent.types import AgentToolCall
            user = await db.get(User, 1)
            question = '比较Qwen北京和新加坡的embedding-v4价格'
            call = _scope_knowledge_call(AgentToolCall('compare', 'search_knowledge', {
                'query': 'Qwen北京价格', 'filters': {'region': 'CN', 'category': 'billing'},
            }, 'knowledge'), question, {'region': 'CN'})
            results = await rag_service.search(db, user, call.arguments['query'], 1,
                                                call.arguments['filters'])
            assert len(results) == 1
            text = results[0]['textContent']
            assert '原文适用范围：新加坡' in text and '每千Token' in text and 'WRONG_SCOPE' not in text
            citation = await read_citation(results[0]['citationId'], user, db)
            assert citation['data']['contextText'] == text
        read = await GetDocumentTool().execute(ToolExecutionContext(user=user),
                                               {'file_md5': md5, 'chunk_id': 30})
        assert read['text'] == text
    finally:
        await engine.dispose()
