"""Verify a deployed candidate over public routes, with isolated synthetic accounts."""
import asyncio
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit, urlunsplit

import httpx
import websockets

from observe_rollout import data, now, trace_probe


URL = os.environ["PROBE_APP_URL"].rstrip("/")
PASSWORD = os.environ["PROBE_PASSWORD"]
REPORT = Path("/app/data/release-context.json")
PROBE_TOKEN = Path("/app/data/release-probe-token")


def websocket_url():
    base = urlsplit(URL)
    return urlunsplit(("wss" if base.scheme == "https" else "ws", base.netloc, base.path + "/chat", "", ""))


async def login(client, name):
    token = data(await client.post("/users/login", json={"username": name, "password": PASSWORD}))["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def send(client, token, question):
    started = now()
    async with asyncio.timeout(50), websockets.connect(websocket_url(), proxy=None) as socket:
        await socket.send(json.dumps({"type": "auth", "token": token}))
        assert json.loads(await socket.recv()).get("type") == "connection"
        await socket.send(question)
        events = []
        while True:
            event = json.loads(await socket.recv())
            events.append(event)
            if event.get("type") == "completion":
                break
            assert not (event.get("error") and not event.get("type")), event
    entities = next(e for e in events if e.get("type") == "entities_extracted")
    authoritative = data(await client.get("/chat/generation/" + event["generationId"]))
    assert authoritative["status"] == "COMPLETED" and authoritative["content"] == event["content"]
    return {
        "generationId": event["generationId"], "conversationId": authoritative["conversationId"],
        "entities": entities["entities"], "sources": entities["entitySources"],
        "shadow": next((e for e in events if e.get("type") == "context_shadow"), None),
        "context": next((e for e in events if e.get("type") == "context_assembled"), None),
        "tools": [e["tool"] for e in events if e.get("type") == "tool_call" and e.get("status") == "executing"],
        "startedAt": started.isoformat(),
    }


async def verify(phase):
    results = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    async with httpx.AsyncClient(base_url=URL + "/api/v1", timeout=10, trust_env=False) as client:
        if phase == "redis_offline":
            response = await client.post("/users/login", json={"username": "trace-down-1", "password": PASSWORD})
            assert response.status_code == 503, response.status_code
            token = PROBE_TOKEN.read_text()
        else:
            token = await login(client, "trace-down-1")
        if phase == "shadow":
            data(await client.post("/users/conversations"))
            results["first"] = await send(client, token, "排查 request_id req_context_001，接口 /v1/chat，当前 API 版本 v1。")
            for index in range(11):
                await send(client, token, f"谢谢，第 {index} 段。" + "普通交流文字" * 220)
        if phase == "redis_offline":
            async with asyncio.timeout(12), websockets.connect(websocket_url(), proxy=None) as socket:
                await socket.send(json.dumps({"type": "auth", "token": token}))
                try:
                    event = json.loads(await socket.recv())
                except websockets.ConnectionClosed as exc:
                    assert exc.rcvd and exc.rcvd.code == 1013
                    results[phase] = {"loginStatus": 503, "closedCode": exc.rcvd.code if exc.rcvd else None}
                else:
                    assert event.get("code") in {429, 503}, event
                    results[phase] = {"loginStatus": 503, "websocketStatus": event["code"]}
        elif phase == "shield":
            result = results[phase] = await send(client, token, "排查 req_context_001 和 req_context_002 哪一个？")
            assert not result["entities"] and not result["tools"], result
            different_user = await login(client, "trace-down-2")
            isolated = results["otherAccount"] = await send(client, different_user, "继续排查刚才的请求。")
            assert not isolated["entities"].get("request_id") and "query_call_log" not in isolated["tools"], isolated
        else:
            if phase == "rollback":
                conversation = results["first"]["conversationId"]
                data(await client.put(f"/users/conversations/{conversation}/switch"))
            result = results[phase] = await send(client, token, "请继续排查刚才的请求。")
            assert result["conversationId"] == results["first"]["conversationId"]
            if phase == "shadow":
                assert result["shadow"]["scopeDifferent"] and not result["entities"].get("request_id"), result
                assert "query_call_log" not in result["tools"]
            elif phase == "rollback":
                assert not result["context"] and not result["shadow"]
                history = data(await client.get("/users/conversation", params={"conversationId": result["conversationId"]}))
                assert any(row["generationId"] == results["first"]["generationId"] and
                           "req_context_001" in row["content"] for row in history)
                results["rollbackPreservedOriginal"] = True
            else:
                assert result["context"] and result["entities"]["request_id"] == "req_context_001", result
                if phase == "active":
                    PROBE_TOKEN.write_text(token)
                    assert result["context"]["recalledMessages"] >= 1
                    await send(client, token, "刚才版本说错了，确认当前 API 版本 v2。")
                    corrected = results["corrected"] = await send(client, token, "继续排查这个请求。")
                    assert corrected["entities"]["api_version"] == "v2", corrected
                elif phase == "redis_restored":
                    assert result["entities"]["api_version"] == "v2", result
            if phase in {"shadow", "active", "redis_restored"}:
                from datetime import datetime

                trace = {"generationId": result["generationId"]}
                await trace_probe(trace, datetime.fromisoformat(result["startedAt"]),
                                  os.environ["PROBE_LANGFUSE_URL"], 30)
                assert trace["outcome"] == "healthy", trace
                result["trace"] = trace
    REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{phase}: passed", flush=True)


if __name__ == "__main__":
    asyncio.run(verify(sys.argv[1]))
