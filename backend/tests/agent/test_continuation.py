from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.continuation import apply_message, assemble_turn, bounded_history
from app.agent import continuation
from app.db.models import ConversationContextState, ConversationMessage, ConversationSession


def message(number, content, *, role="user", gid=None):
    return SimpleNamespace(id=number, content=content, role=role, generation_id=gid,
                           created_at=datetime(2026, 11, 18))


def test_continuation_uses_scoped_state_and_keeps_correction_provenance():
    state = {}
    apply_message(state, message(1, "request_id req_first，接口版本 v1，访问 /v1/chat"))
    apply_message(state, message(31, "谢谢"))
    entities, sources, *_ = apply_message(state, message(34, "继续排查刚才的请求"))
    assert entities["request_id"] == "req_first" and sources["request_id"] == "continuation"
    _, _, _, _, scope = apply_message(state, message(36, "刚才版本说错了，当前版本 v2"))
    assert scope["fields"]["api_version"]["supersedesMessageId"] == 1
    assert scope["fields"]["api_version"]["source"] == "user_report"
    entities, *_ = apply_message(state, message(38, "换一个请求，req_next"))
    assert entities == {"request_id": "req_next"}
    entities, *_ = apply_message(state, message(40, "继续查 req_first"))
    assert entities["api_version"] == "v2"


def test_multiple_requests_require_disambiguation_and_keep_previous_scope():
    state = {}
    apply_message(state, message(1, "排查 req_first"))
    values, sources, follow_up, ambiguous, _ = apply_message(state, message(5, "排查 req_first 和 req_second"))
    assert not values and not sources and not follow_up and ambiguous
    assert state["active"] == "request_id:req_first"


def test_history_budget_keeps_full_turns_and_never_keeps_an_orphan():
    rows = [message(1, "orphan", role="assistant", gid="zero"),
            message(2, "first value", gid="one"), message(3, "first reply", role="assistant", gid="one"),
            message(4, "new", gid="two"), message(5, "reply", role="assistant", gid="two")]
    history, ids = bounded_history(rows, max_messages=3, max_chars=12)
    assert ids == {4, 5}
    assert [item["role"] for item in history] == ["user", "assistant"]


def test_progress_snapshot_deduplicates_and_leaves_raw_text_in_message_store():
    state = {}
    apply_message(state, message(1, "排查 req_first"))
    text = "继续排查这个请求，我已尝试切换网关。"
    apply_message(state, message(2, text))
    apply_message(state, message(3, text))
    serialized = state["scopes"]["request_id:req_first"]["progress"]["attempt"]
    assert [row["messageId"] for row in serialized] == [2]
    assert text not in str(serialized)


def test_shadow_reports_only_differences_and_refresh_intent():
    candidate = continuation.TurnContext(
        [], {"request_id": "req_private", "month": "2026-11"}, {}, True, False, [], {"assemblyMs": 3},
    )
    result = continuation.compare_context_selection({}, candidate, "查刚才这个账期的当前用量")
    assert result["differences"] == 2 and result["scopeDifferent"]
    assert result["candidateNeedsCurrentRead"]
    assert "req_private" not in str(result) and "2026-11" not in str(result)


@pytest.mark.asyncio
async def test_delayed_turn_cannot_overwrite_newer_correction(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'context.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as db:
            for model in (ConversationSession, ConversationMessage, ConversationContextState):
                await db.run_sync(model.__table__.create)
        async with factory() as db:
            db.add(ConversationSession(conversation_id="one", user_id="owner"))
            old = ConversationMessage(conversation_id="one", user_id="owner", role="user",
                                      content="排查 req_test，当前版本 v1", generation_id="old")
            new = ConversationMessage(conversation_id="one", user_id="owner", role="user",
                                      content="刚才版本说错，当前版本 v2", generation_id="new")
            db.add_all([old, new])
            await db.commit()
            settings = SimpleNamespace(conversation_history_messages=20, conversation_history_chars=12000)
            first = await assemble_turn(db, new, settings)
            delayed = await assemble_turn(db, old, settings)
            stored = (await db.scalars(select(ConversationContextState))).one()
            assert delayed.metadata["mode"] == "superseded"
            assert first.entities["api_version"] == "v2" and stored.last_message_id == new.id
            assert '"value": "v2"' in stored.state_json
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_progress_timeout_keeps_scoped_entities_and_recent_history(tmp_path, monkeypatch):
    async def timeout(*_args):
        raise TimeoutError

    monkeypatch.setattr(continuation, "recover_progress", timeout)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'timeout.db'}")
    try:
        async with engine.begin() as db:
            for model in (ConversationSession, ConversationMessage, ConversationContextState):
                await db.run_sync(model.__table__.create)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            db.add(ConversationSession(conversation_id="timeout", user_id="owner"))
            values = dict(conversation_id="timeout", user_id="owner", role="user")
            old = ConversationMessage(**values, content="排查 req_first", generation_id="old")
            new = ConversationMessage(**values, content="继续这个请求，下一步查什么？", generation_id="new")
            db.add_all([old, new])
            await db.commit()
            settings = SimpleNamespace(conversation_history_messages=20, conversation_history_chars=12000,
                                       context_progress_enabled=True)
            context = await assemble_turn(db, new, settings)
            assert context.entities["request_id"] == "req_first"
            assert context.metadata["progressUnavailable"] and context.progress == []
            assert context.history == [{"role": "user", "content": "排查 req_first"}]
    finally:
        await engine.dispose()
