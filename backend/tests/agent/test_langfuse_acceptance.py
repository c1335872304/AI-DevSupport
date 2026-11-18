from __future__ import annotations

import json
import asyncio

import pytest

from app.agent.llm import llm_service
from app.agent.graph.workflow import CustomerServiceWorkflow
from app.agent.runtime import AgentRuntime
from app.core.langfuse_observability import record_model_usage
from app.core.config import get_settings
from app.db.models import User
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry

PRIVATE_MARKER = "trace-must-exclude-this-business-content"


@pytest.mark.asyncio
@pytest.mark.parametrize(("question", "agent", "tool"), [
    ("Qwen API 的 429 限流处理规范是什么？", "knowledge", "search_knowledge"),
    ("request_id req_demo_401 的请求为什么返回 401？", "api_diagnostic", "query_call_log"),
    ("帮我查本月实际的 API 调用量和用量", "billing", "query_usage"),
])
async def test_representative_question_exports_trace(langfuse_receiver, monkeypatch, question, agent, tool):
    async def execute(self, name, arguments, context):
        data = {"private": PRIVATE_MARKER}
        if name == "search_knowledge":
            data["results"] = [{
                "fileMd5": "a" * 32, "fileName": "qwen.md", "chunkId": 7, "pageNumber": 1,
                "score": 0.87, "product": "qwen", "textContent": "Qwen 返回 HTTP 429 时可降低请求速率并按退避策略重试。",
            }]
        if name == "query_call_log":
            data.update(found=False, ownerUserId=str(context.user.id))
        if name == "query_usage":
            data.update(found=False, ownerUserId=str(context.user.id))
        return ToolResult(status="SUCCESS", data=data, duration_ms=12)

    wrong_file = "wrong.md"
    grounded_text = "Qwen 返回 HTTP 429 时可降低请求速率并按退避策略重试。"

    async def provider(_messages, force_no_tools=False):
        await asyncio.sleep(0.08)
        if tool == "search_knowledge":
            # Reuse the citation regression: the model supplies the wrong filename.
            yield f"{grounded_text}（来源#1: {wrong_file}）"
        else:
            yield "请参考已提供的资料。"
        await asyncio.sleep(0.08)
        record_model_usage({"prompt_tokens": 18, "completion_tokens": 9})

    async def ignore(_value):
        pass

    monkeypatch.setattr(ToolRegistry, "execute", execute)
    monkeypatch.setattr(get_settings(), "llm_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "skills_semantic_routing_enabled", False)
    monkeypatch.setattr(llm_service, "_circuit_open", lambda: False)
    monkeypatch.setattr(llm_service, "_stream_agent_turn_once", llm_service._fallback_agent_turn)
    monkeypatch.setattr(llm_service, "_stream_messages_once", provider)
    answer, _ = await AgentRuntime().run(
        user=User(id=91, username="test", password="x", role="USER"),
        question=question, history=[], generation_id="langfuse-acceptance",
        send_json=ignore, on_chunk=ignore,
    )
    assert answer
    spans = langfuse_receiver(PRIVATE_MARKER, question, wrong_file, grounded_text)
    assert {tool, "routing_policy", "safety", "answer_delivery"} <= {span.name for span in spans}
    root, = [span for span in spans if not span.parent_span_id]
    assert root.name == "customer_service.question"
    assert {span.trace_id for span in spans} == {root.trace_id}
    output = next(item.value.string_value for item in root.attributes if item.key == "langfuse.observation.output")
    assert agent in json.loads(output)["agents"]

    if tool == "search_knowledge":
        model, = [span for span in spans if span.name == "answer.model"]
        model_attrs = {item.key: item.value.string_value for item in model.attributes}
        first_token_ms = json.loads(model_attrs["langfuse.observation.output"])["firstTokenMs"]
        assert 20 <= first_token_ms < (model.end_time_unix_nano - model.start_time_unix_nano) / 1e6
        assert model_attrs["langfuse.observation.completion_start_time"]
        assert json.loads(model_attrs["langfuse.observation.usage_details"]) == {"input": 18, "output": 9}
        assert any(
            item.key == "langfuse.trace.metadata.first_chunk_ms" and item.value.double_value >= 20
            for item in root.attributes
        )
        assert wrong_file not in answer
        retrieval = next(span for span in spans if span.name == tool)
        matches = next(item.value.string_value for item in retrieval.attributes if item.key == "langfuse.observation.output")
        assert json.loads(matches)["matches"] == [{"rank": 1, "fileMd5": "a" * 32, "chunkId": 7, "pageNumber": 1, "score": 0.87}]
        assert retrieval.end_time_unix_nano <= model.start_time_unix_nano


@pytest.mark.parametrize("timed_out", [False, True], ids=["cancelled", "timed-out"])
async def test_interrupted_generation_exports_closed_root(langfuse_receiver, monkeypatch, timed_out):
    started = asyncio.Event()

    async def blocked(_self, _state):
        started.set()
        if timed_out:
            async with asyncio.timeout(0.01):
                await asyncio.Event().wait()
        await asyncio.Event().wait()

    async def ignore(_value):
        pass

    monkeypatch.setattr(CustomerServiceWorkflow, "run", blocked)
    task = asyncio.create_task(AgentRuntime().run(
        user=User(id=91, username="test", password="x", role="USER"),
        question=PRIVATE_MARKER, history=[], generation_id="langfuse-interrupted",
        send_json=ignore, on_chunk=ignore,
    ))
    await asyncio.wait_for(started.wait(), 1)
    if not timed_out:
        task.cancel()
    expected = TimeoutError if timed_out else asyncio.CancelledError
    with pytest.raises(expected):
        await task

    root, = langfuse_receiver(PRIVATE_MARKER)
    assert root.name == "customer_service.question"
    assert root.end_time_unix_nano >= root.start_time_unix_nano > 0
    assert root.status.code == 2
    assert root.status.message == expected.__name__
