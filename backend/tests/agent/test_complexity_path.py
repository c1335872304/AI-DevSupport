from types import SimpleNamespace
from typing import ClassVar

import pytest

from app.agent.complexity import simple_document_question, usable_document_read
from app.agent.llm import llm_service
from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.db.models import User
from app.db.session import engine
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry


@pytest.mark.parametrize(
    "question",
    [
        "DeepSeek JSON Output的response_format应该如何配置？",
        "Qwen北京地域API Key应配哪个Base URL？",
        "OpenAI后台响应如何开启并轮询？",
        "Qwen的OpenAI兼容流式聊天include_usage如何设置？",
    ],
)
def test_independent_single_vendor_configuration_is_eligible(question):
    assert simple_document_question(question)
    assert not simple_document_question(question, history=[{"role": "user", "content": "之前请求失败"}])
    assert not simple_document_question(question, entity_memory={"request_id": "req_old"})


@pytest.mark.parametrize(
    "question",
    [
        "DeepSeek请求req_demo_401返回401怎么排查？",
        "Qwen返回429，降低频率后恢复了吗？",
        "我已修复OpenAI的Key，请复查请求req_fixed",
        "比较DeepSeek与OpenAI的JSON Schema",
        "Qwen我的账号怎么开通？",
        "DeepSeek JSON退款，帮我转人工",
        "Please reimburse my DeepSeek API Key charges",
        "JSON结构化输出怎么配置才能保证Schema？",
        "Qwen未来API Key会永久免费吗？",
        "DeepSeek JSON如何配置并升级套餐？",
        "How to configure DeepSeek API Key and cancel my subscription?",
    ],
)
def test_diagnostics_comparisons_and_operations_never_take_shortcut(question):
    assert not simple_document_question(question)


@pytest.mark.parametrize("status", ["NO_EVIDENCE", "BACKEND_UNAVAILABLE", "CONFLICT", "NEEDS_CLARIFICATION"])
def test_uncertain_read_cannot_stop_planning(status):
    call = AgentToolCall("x", "search_knowledge", {}, "knowledge")
    assert not usable_document_read(
        [(call, ToolResult(status="SUCCESS", data={"status": status, "results": []}))],
        "DeepSeek JSON如何配置",
    )


class ReadDocument(BaseTool):
    name = "search_knowledge"
    description = "bounded authorized read"
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer"},
            "filters": {"type": "object"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, data):
        self.data = data
        self.calls = []

    async def execute(self, context, arguments):
        self.calls.append((context.user.id, arguments))
        return self.data


async def run_graph(monkeypatch, tool):
    counts = {"classify": 0, "planner": 0, "generate": 0}
    events = []
    monkeypatch.setattr(llm_service.settings, "llm_api_key", "test-only")

    async def classify(*args, **kwargs):
        counts["classify"] += 1
        return {}

    async def planner(*args, **kwargs):
        counts["planner"] += 1
        if False:
            yield {}

    async def answer(*args, **kwargs):
        counts["generate"] += 1
        tool.answer_messages = args[0] if args else kwargs['messages']
        yield "参数见对应文档，证据不足时暂不确认。"

    monkeypatch.setattr(llm_service, "classify_intent", classify)
    monkeypatch.setattr(llm_service, "stream_agent_turn", planner)
    monkeypatch.setattr(llm_service, "stream_messages", answer)

    async def send(event):
        events.append(event)

    async def chunk(_value):
        pass

    await engine.dispose()
    try:
        answer, refs = await AgentRuntime(ToolRegistry([tool])).run(
            user=User(id=987, username="complexity-test", password="x", role="USER"),
            question="DeepSeek JSON Output如何配置？",
            history=[],
            generation_id="complexity-test-" + str(bool(tool.data.get("results"))),
            send_json=send,
            on_chunk=chunk,
        )
    finally:
        await engine.dispose()
    return counts, events, answer, refs


async def test_simple_document_uses_shared_tool_once_and_one_generation(monkeypatch):
    tool = ReadDocument(
        {
            "status": "OK",
            "results": [
                {
                    "product": "DeepSeek API",
                    "fileMd5": "a" * 32,
                    "fileName": "doc.md",
                    "chunkId": 0,
                    "indexVersion": "v1",
                    "citationId": "signed-test",
                    "textContent": "JSON response_format setting. " * 10,
                }
            ],
        }
    )
    counts, events, answer, refs = await run_graph(monkeypatch, tool)
    assert counts == {"classify": 0, "planner": 0, "generate": 1}
    assert len(tool.calls) == 1 and tool.calls[0][0] == 987
    assert tool.calls[0][1]["filters"] == {"product": "DeepSeek API"}
    assert refs and "来源#1: doc.md" in answer
    assert any(e.get("type") == "quality_gate" for e in events)
    assert any(e.get("action") == "generate_with_verified_sources" for e in events)
    assert any(e.get('type') == 'document_context_budget' and e.get('bounded') for e in events)
    assert 'signed-test' not in str(tool.answer_messages)
    assert 'indexVersion' not in str(tool.answer_messages)
    assert not any(e.get("tool") == "create_support_handoff" for e in events)


async def test_empty_read_falls_back_to_full_specialist_instead_of_claiming_fast_success(monkeypatch):
    counts, events, _answer, refs = await run_graph(
        monkeypatch, ReadDocument({"status": "NO_EVIDENCE", "results": []})
    )
    assert counts["planner"] >= 1 and not refs
    assert any(e.get("action") == "fallback_to_full_specialist" for e in events)


def test_foreign_or_unsigned_evidence_cannot_complete_shortcut():
    call = AgentToolCall("x", "search_knowledge", {}, "knowledge")
    for row in ({"product": "Qwen API", "citationId": "x"}, {"product": "DeepSeek API"}):
        assert not usable_document_read(
            [(call, SimpleNamespace(status="SUCCESS", data={"status": "OK", "results": [row]}))],
            "DeepSeek JSON如何配置",
        )


async def test_final_numbering_matches_signed_sources_without_reordering_retrieval(monkeypatch):
    rows = [{'product': 'DeepSeek API', 'fileMd5': name * 32, 'fileName': name + '.md',
             'chunkId': 0, 'indexVersion': 'v1', 'citationId': 'signed-' + name,
             'textContent': 'JSON response_format必须按接口配置。' * 8} for name in ['z', 'a']]
    tool = ReadDocument({'status': 'OK', 'results': rows})
    counts, events, answer, refs = await run_graph(monkeypatch, tool)
    assert counts == {'classify': 0, 'planner': 0, 'generate': 1}
    assert rows[0]['fileName'] == 'z.md'
    assert refs['1']['fileName'] == 'a.md' and refs['1']['citationId'] == 'signed-a'
    assert refs['2']['fileName'] == 'z.md' and refs['2']['citationId'] == 'signed-z'
    assert '来源#1: a.md' in answer and '来源#2: z.md' in answer
    assert any(e.get('type') == 'document_reference_remap' and e['mapping'] == {2: 1, 1: 2} for e in events)
