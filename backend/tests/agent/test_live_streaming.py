from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.agent.graph.workflow import CustomerServiceWorkflow
from app.agent.llm import LLMService, llm_service
from app.agent.runtime import AgentRuntime
from app.agent.streaming import StreamUnitBuffer
from app.core.redaction import redact_text
from app.db.models import User
from app.skill_runtime.trace import SkillTrace


def test_units_preserve_split_fences_and_original_text():
    text = '说明。\n```python\nprint("代码里。不能拆")\n```\n下一段。'
    units, buffer = [], StreamUnitBuffer()
    for char in text:
        units.extend(buffer.feed(char))
    units.extend(buffer.feed('', final=True))
    assert ''.join(units) == text
    code = next(unit for unit in units if '```python' in unit)
    assert 'print("代码里。不能拆")' in code and code.count('```') == 2


def test_units_do_not_flush_credentials_urls_or_partial_english():
    buffer = StreamUnitBuffer()
    assert buffer.feed('Bearer sk-1234') == []
    assert buffer.feed('567890 https://host.example.com/path') == []
    assert buffer.feed('\n') == ['Bearer sk-1234567890 https://host.example.com/path\n']


def test_unfinished_unit_has_a_hard_memory_limit():
    with pytest.raises(ValueError, match='safe buffer limit'):
        StreamUnitBuffer(max_chars=10).feed('x' * 11)


@pytest.mark.parametrize('expression', ['os.environ["DASHSCOPE_API_KEY"]',
                                      "os.getenv('DASHSCOPE_API_KEY')", 'process.env.API_KEY'])
def test_documentation_environment_expression_is_not_a_secret(expression):
    code = f'api_key={expression},'
    assert redact_text(code) == code
    assert 'sk-1234567890abcdef' not in redact_text(code + '\napi_key="sk-1234567890abcdef"')
    assert '[REDACTED]' in redact_text('api_key="process.env.API_KEY"')


def service(monkeypatch):
    result = LLMService()
    result.settings = SimpleNamespace(llm_api_key='test-only', llm_max_retries=2,
                                     llm_request_timeout_seconds=5, llm_retry_backoff_seconds=0)
    monkeypatch.setattr(result, '_circuit_open', lambda: False)
    monkeypatch.setattr(result, '_record_provider_failure', lambda exc: None)
    monkeypatch.setattr(result, '_record_provider_success', lambda: None)
    monkeypatch.setattr(result, '_retryable', lambda exc: True)
    return result


@pytest.mark.asyncio
async def test_provider_first_delta_arrives_before_provider_finishes(monkeypatch):
    result, release = service(monkeypatch), asyncio.Event()

    async def provider(*args, **kwargs):
        yield 'first'
        await release.wait()
        yield 'second'

    monkeypatch.setattr(result, '_stream_messages_once', provider)
    stream = result.stream_messages([])
    assert await asyncio.wait_for(anext(stream), 1) == 'first'
    release.set()
    assert await anext(stream) == 'second'
    await stream.aclose()


@pytest.mark.asyncio
async def test_no_retry_or_fallback_after_a_partial_provider_answer(monkeypatch):
    result, attempts = service(monkeypatch), []

    async def provider(*args, **kwargs):
        attempts.append(1)
        yield 'first'
        raise ConnectionError('broken stream')

    monkeypatch.setattr(result, '_stream_messages_once', provider)
    stream = result.stream_messages([])
    assert await anext(stream) == 'first'
    with pytest.raises(ConnectionError):
        await anext(stream)
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_retry_still_allowed_before_any_delta(monkeypatch):
    result, attempts = service(monkeypatch), []

    async def pause(*args):
        pass

    async def provider(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError('before content')
        yield 'recovered'

    monkeypatch.setattr(result, '_stream_messages_once', provider)
    monkeypatch.setattr(result, '_retry_pause', pause)
    assert [c async for c in result.stream_messages([])] == ['recovered']
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_cancel_during_provider_stream_closes_without_retry(monkeypatch):
    result, closed = service(monkeypatch), asyncio.Event()

    async def provider(*args, **kwargs):
        try:
            yield 'first'
            await asyncio.Event().wait()
        finally:
            closed.set()

    monkeypatch.setattr(result, '_stream_messages_once', provider)
    stream = result.stream_messages([])
    assert await anext(stream) == 'first'
    task = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()


def workflow(monkeypatch, skills=None):
    events, chunks = [], []
    monkeypatch.setattr(llm_service.settings, "llm_api_key", "test-only")

    async def send(value):
        events.append(value)

    async def chunk(value):
        chunks.append(value)

    graph = CustomerServiceWorkflow(runtime=AgentRuntime(),
        user=User(id=9001, username='stream-test', password='x', role='USER'), send_json=send, on_chunk=chunk)
    trace = SkillTrace(question='配置说明')
    active = skills or ['knowledge']
    for skill in active:
        trace.activate(skill)
    state = {'question': '配置说明', 'generation_id': 'stream-unit-test', 'active_skills': active,
             'skill_trace': trace, 'graph_path': [], 'evidence_summary': {},
             'references': {'1': {'referenceNumber': 1, 'fileName': 'doc.md'}}}
    return graph, state, events, chunks


@pytest.mark.asyncio
async def test_checked_body_streams_while_generation_is_still_waiting(monkeypatch):
    graph, state, events, chunks = workflow(monkeypatch)
    release, arrived = asyncio.Event(), asyncio.Event()
    original = graph.on_chunk

    async def chunk(value):
        await original(value)
        arrived.set()

    graph.on_chunk = chunk

    async def provider(*args, **kwargs):
        yield '这是第一段配置说明。\n'
        await release.wait()
        yield '这是第二段配置说明。'

    monkeypatch.setattr(llm_service, 'stream_messages', provider)
    task = asyncio.create_task(graph.target_generate_response(state))
    try:
        await asyncio.wait_for(arrived.wait(), 5)
        assert not task.done() and '第一段' in ''.join(chunks) and '第二段' not in ''.join(chunks)
    finally:
        release.set()
    state.update(await task)
    state.update(await graph.safety(state))
    await graph.emit_final(state)
    assert ''.join(chunks) == state['final_answer']
    assert ''.join(chunks).count('第一段') == 1
    assert ''.join(chunks).count('来源#1: doc.md') == 1
    assert not any(event['type'] == 'answer_replace' for event in events)


@pytest.mark.asyncio
async def test_split_credential_is_redacted_before_any_public_chunk(monkeypatch):
    graph, state, _events, chunks = workflow(monkeypatch)

    async def provider(*args, **kwargs):
        yield '示例密钥 sk-1234'
        yield '567890abcdef。'
        yield '\n请使用自己的配置。'

    monkeypatch.setattr(llm_service, 'stream_messages', provider)
    state.update(await graph.target_generate_response(state))
    assert chunks and all('sk-1234' not in chunk for chunk in chunks)
    assert '[REDACTED]' in ''.join(chunks)


@pytest.mark.asyncio
async def test_credential_logging_example_is_sanitized_before_any_chunk(monkeypatch):
    graph, state, _events, chunks = workflow(monkeypatch)

    async def provider(*args, **kwargs):
        yield '从环境变量读取凭据。\n\n\x60\x60\x60python\nimport os\ntoken = os.getenv("PAISMART_TOKEN")\npri'
        yield 'nt(token)\nlogging.info("%s", token)\nprint("已配置")\n\x60\x60\x60\n'

    monkeypatch.setattr(llm_service, "stream_messages", provider)
    state.update(await graph.target_generate_response(state))
    state.update(await graph.safety(state))
    await graph.emit_final(state)
    for answer in ("".join(chunks), state["final_answer"]):
        assert "print(token)" not in answer
        assert 'logging.info("%s", token)' not in answer
        assert 'os.getenv("PAISMART_TOKEN")' in answer
        assert 'print("已配置")' in answer


@pytest.mark.asyncio
async def test_split_unverified_claim_never_reaches_public_stream(monkeypatch):
    graph, state, _events, chunks = workflow(monkeypatch, ['api-diagnostic'])

    async def provider(*args, **kwargs):
        yield '已确'
        yield '认该请求触发了限流。'

    monkeypatch.setattr(llm_service, 'stream_messages', provider)
    state.update(await graph.target_generate_response(state))
    assert '已确认该请求' not in ''.join(chunks)
    state.update(await graph.safety(state))
    await graph.emit_final(state)
    assert '已确认该请求' not in ''.join(chunks)


@pytest.mark.asyncio
@pytest.mark.parametrize(("draft", "facts", "expected_action", "keep_claim"), [
    ("已确认文档说明 HTTP 429 时应使用指数退避。", [], "passed", False),
    ("该请求返回 HTTP 429。文档建议遇到 429 时使用指数退避。", [
        {"tool": "query_recent_call_stats", "rateLimitedCount": 2},
    ], "filtered_unsupported_claims", False),
    ("该请求返回 HTTP 429。文档建议遇到 429 时使用指数退避。", [
        {"tool": "query_call_log", "found": True, "requestId": "req_other", "httpStatus": 429},
    ], "filtered_unsupported_claims", False),
    ("该请求返回 HTTP 429。文档建议遇到 429 时使用指数退避。", [
        {"tool": "query_call_log", "found": True, "requestId": "req_current", "httpStatus": 429},
    ], "passed", True),
    ("该请求返回 HTTP 429。答复中包含完整 API Key。", [], "fail_closed", False),
])
async def test_quality_gate_separates_document_guidance_from_personal_claims(
    monkeypatch, draft, facts, expected_action, keep_claim,
):
    graph, state, events, _chunks = workflow(monkeypatch, ["knowledge", "api-diagnostic"])
    state["draft_answer"] = draft
    state["evidence_summary"] = {"verifiedFacts": facts}
    state["entities"] = {"request_id": "req_current"}
    result = await graph.safety(state, preview=True)
    assert events == []
    assert result["quality_gate_action"] == expected_action
    assert ("指数退避" in result["final_answer"]) == (expected_action != "fail_closed")
    assert ("该请求返回 HTTP 429" in result["final_answer"]) == keep_claim
    assert "完整 API Key" not in result["final_answer"]


@pytest.mark.asyncio
async def test_final_correction_is_replacement_not_second_answer(monkeypatch):
    graph, state, events, chunks = workflow(monkeypatch)
    graph._streamed_answer = '此前获准显示的内容。'
    state['final_answer'] = '当前状态证据已过期，请重新核查。'
    await graph.emit_final(state)
    assert not chunks
    replacement = next(event for event in events if event['type'] == 'answer_replace')
    assert replacement['generationId'] == state['generation_id']
    assert replacement['content'] == state['final_answer']
