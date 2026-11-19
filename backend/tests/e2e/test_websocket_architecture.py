from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, ClassVar
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.agent.llm import llm_service
from app.agent.runtime import agent_runtime
from app.agent.types import AgentToolCall
from app.core.security import create_access_token
from app.db.init_db import init_db
from app.db.models import User
from app.db.session import SessionLocal, engine
from app.main import app
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.registry import ToolRegistry


class _WebSocketKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = "fixed knowledge result for WebSocket architecture E2E"
    input_schema: ClassVar[dict] = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    read_only = True
    parallel_safe = True

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, context: ToolExecutionContext, arguments: dict) -> dict[str, Any]:
        self.calls.append(dict(arguments))
        return {
            "results": [
                {
                    "fileMd5": "b" * 32,
                    "fileName": "refund-policy.md",
                    "chunkId": 1,
                    "pageNumber": 1,
                    "textContent": "符合条件的购买可在支付后 7 天内提交退款申请。",
                }
            ]
        }


class _WebSocketDocumentTool(BaseTool):
    name = "get_document"
    description = "fixed parent-context result for WebSocket architecture E2E"
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "file_md5": {"type": "string"},
            "chunk_id": {"type": "integer"},
            "max_chars": {"type": "integer"},
        },
        "required": ["file_md5"],
        "additionalProperties": False,
    }
    read_only = True
    parallel_safe = True

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, context: ToolExecutionContext, arguments: dict) -> dict[str, Any]:
        self.calls.append(dict(arguments))
        return {
            "fileMd5": "b" * 32,
            "fileName": "refund-policy.md",
            "chunkId": int(arguments.get("chunk_id") or 1),
            "pageNumber": 1,
            "text": "符合条件的购买可在支付后 7 天内提交退款申请。",
        }


async def _create_user(username: str) -> tuple[int, str]:
    async with SessionLocal() as db:
        user = User(
            username=username,
            password="test-only",
            role="USER",
            llm_token_balance=100_000,
            embedding_token_balance=100_000,
            token_version=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        token = create_access_token(username, int(user.id), user.role, int(user.token_version or 0))
        user_id = int(user.id)
    await engine.dispose()
    return user_id, token


async def _delete_user(username: str) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user:
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()
    await engine.dispose()


def test_websocket_to_agent_final_answer_with_mocked_model(monkeypatch: pytest.MonkeyPatch):
    """Exercise the browser transport through the target workflow with fixed model output."""
    username = f"ws-architecture-{uuid4().hex}"
    asyncio.run(engine.dispose())
    # This test creates the user before TestClient starts the app lifespan, so
    # the normal init_db() hook has not run yet in a clean local SQLite setup.
    # Initialize the schema explicitly to keep the test self-contained.
    asyncio.run(init_db())
    # MySQL/aiomysql connections are bound to the event loop that created them.
    # The setup helpers below intentionally use separate ``asyncio.run`` calls,
    # so drain the pool before moving to the next loop.
    asyncio.run(engine.dispose())
    _user_id, token = asyncio.run(_create_user(username))
    knowledge = _WebSocketKnowledgeTool()
    document = _WebSocketDocumentTool()
    previous_redis = bool(agent_runtime.settings.redis_enabled)
    planner_turn = 0
    release_tail = threading.Event()
    provider_finished = threading.Event()

    async def no_semantic_route(*_args, **_kwargs):
        return {}

    async def specialist_plan(messages, tools):
        nonlocal planner_turn
        planner_turn += 1
        names = {row["function"]["name"] for row in tools}
        if planner_turn == 1 and "search_knowledge" in names:
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    AgentToolCall(
                        "ws-knowledge-search",
                        "search_knowledge",
                        {"query": str(messages[-1].get("content") or "")},
                    )
                ],
            }
        elif planner_turn == 2 and "get_document" in names:
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    AgentToolCall(
                        "ws-knowledge-document",
                        "get_document",
                        {"file_md5": "b" * 32, "chunk_id": 1, "max_chars": 5000},
                    )
                ],
            }

    async def final_response(messages, force_no_tools=False):
        payload = json.loads(str(messages[-1]["content"]))
        excerpts = payload["evidenceSummary"]["knowledgeExcerpts"]
        assert any("7 天" in item["text"] for item in excerpts)
        assert any(item["source"].get("referenceNumber") == 1 for item in excerpts)
        assert payload["handoffResult"]["attempted"] is False
        yield "符合条件的购买可在支付后 7 天内提交退款申请；是否批准仍需按订单和账单核验（来源#1）。"
        # The browser transport must deliver this sentence before the model can
        # finish. A whole-answer buffer makes this handshake fail deterministically.
        async with asyncio.timeout(8):
            while not release_tail.is_set():
                await asyncio.sleep(0.01)
        yield "\n请按适用条件进一步核对。"
        yield "\n\n```python\nimport os\ntoken = os.getenv('PAISMART_TOKEN')\npri"
        yield "nt(token)\n```\n"
        provider_finished.set()

    monkeypatch.setattr(llm_service, "classify_intent", no_semantic_route)
    monkeypatch.setattr(llm_service, "stream_agent_turn", specialist_plan)
    monkeypatch.setattr(llm_service, "stream_messages", final_response)
    monkeypatch.setattr(llm_service.settings, "llm_api_key", "test-only")
    monkeypatch.setattr(agent_runtime, "registry", ToolRegistry([knowledge, document]))
    monkeypatch.setattr(agent_runtime.settings, "redis_enabled", False)

    try:
        with TestClient(app) as client, client.websocket_connect("/chat") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "connection"
            websocket.send_text("退款政策是什么？")

            events: list[dict[str, Any]] = []
            while True:
                event = websocket.receive_json()
                events.append(event)
                if event.get("type") == "chunk" and "7 天内提交退款申请" in str(event.get("chunk") or ""):
                    assert not provider_finished.is_set()
                    release_tail.set()
                if event.get("code", 0) >= 400:
                    raise AssertionError("WebSocket generation failed: " + str(event))
                if event.get("type") == "completion":
                    break

        event_types = {str(event.get("type")) for event in events}
        assert {"start", "routing_decision", "target_specialists_dispatched", "tool_call", "evidence_summary", "handoff_decision", "chunk", "completion"} <= event_types
        nodes = [str(event["node"]) for event in events if event.get("type") == "workflow_node"]
        assert nodes.index("target_execute_tools") < nodes.index("target_evidence_join") < nodes.index("target_handoff_decision")
        assert nodes.index("target_handoff_decision") < nodes.index("target_generate_response") < nodes.index("safety")
        assert "target_create_handoff" not in nodes
        assert knowledge.calls == [{"query": "退款政策是什么？"}]
        # The verified search excerpt already answers this question.
        assert document.calls == []
        assert any("7 天内提交退款申请" in str(event.get("chunk") or "") for event in events)
        assert events[-1]["type"] == "completion"
        assert release_tail.is_set() and provider_finished.is_set()
        assert "请按适用条件" in events[-1]["content"]
        visible = "".join(
            str(event.get("chunk") or event.get("content") or "")
            for event in events if event.get("type") in {"chunk", "answer_replace", "completion"}
        )
        assert "print(token)" not in visible
        assert "os.getenv('PAISMART_TOKEN')" in visible
    finally:
        release_tail.set()
        monkeypatch.setattr(agent_runtime.settings, "redis_enabled", previous_redis)
        asyncio.run(engine.dispose())
        asyncio.run(_delete_user(username))
