"""Exercise deployed Nginx -> WebSocket -> real RAG/model live output.

Credentials and signed citations stay in the checkpoint private directory.
This uses only the temporary evaluation identity prepared separately.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
import websockets

QUESTIONS = [
    ("deepseek", "DeepSeek JSON Output 的 response_format 如何配置？请给出简短 Python 示例和必要注意事项。"),
    ("qwen", "Qwen 北京地域的 OpenAI 兼容接口 Base URL 怎么配置？请给出地址和简短 Python 示例。"),
    ("openai", "OpenAI Responses API 如何开启后台响应并轮询结果？请给出简短示例。"),
]


async def main(checkpoint: Path, selected: str | None = None):
    private = checkpoint / "private"
    identity = json.loads((private / "identity.json").read_text(encoding="utf-8-sig"))
    async with httpx.AsyncClient(base_url="http://127.0.0.1:9527/api/v1", trust_env=False, timeout=40) as client:
        login = await client.post("/users/login", json={k: identity[k] for k in ("username", "password")})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["data"]["token"]
        token = login.json()["data"]["token"]
        summaries = []
        for name, question in QUESTIONS:
            if selected and name != selected:
                continue
            # Only this disposable user's sessions are selected/archived.
            sessions = (await client.get("/users/conversations")).json()["data"]
            for session in sessions:
                if session["status"] == "ACTIVE":
                    (await client.put("/users/conversations/" + session["conversationId"] + "/archive")).raise_for_status()
            created = await client.post("/users/conversations")
            created.raise_for_status()
            conversation = created.json()["data"]["conversationId"]
            (await client.put("/users/conversations/" + conversation + "/switch")).raise_for_status()
            row = {"case": name, "question": question, "events": []}
            summary = {"case": name, "question": question, "chunks": 0, "replacements": 0}
            received, first, final_gate, started = "", None, None, time.perf_counter()
            try:
                async with websockets.connect("ws://127.0.0.1:9527/proxy-ws/chat", proxy=None,
                                              max_size=8 * 1024 * 1024) as socket:
                    await socket.send(json.dumps({"type": "auth", "token": token}))
                    assert json.loads(await socket.recv())["type"] == "connection"
                    await socket.send(question)
                    async with asyncio.timeout(180):
                        while True:
                            event = json.loads(await socket.recv())
                            elapsed = round((time.perf_counter() - started) * 1000, 2)
                            row["events"].append({"elapsedMs": elapsed, **event})
                            if event.get("type") == "workflow_node" and event.get("node") == "safety":
                                final_gate = elapsed
                            if event.get("type") == "chunk":
                                first = elapsed if first is None else first
                                received += event["chunk"]
                                summary["chunks"] += 1
                            if event.get("type") == "answer_replace":
                                received = event["content"]
                                summary["replacements"] += 1
                            if event.get("code", 0) >= 400:
                                raise RuntimeError(event.get("error", "generation failed"))
                            if event.get("type") == "completion":
                                assert event["conversationId"] == conversation
                                assert received == event["content"], "live/final body diverged"
                                summary.update(firstBodyMs=first, completionMs=elapsed,
                                               finalGateMs=final_gate,
                                               bodyBeforeFinalGate=first is not None and final_gate is not None and first < final_gate,
                                               answer=received, generationId=event["generationId"])
                                snapshot = (await client.get("/chat/generation/" + event["generationId"])).json()["data"]
                                assert snapshot["content"] == received and snapshot["status"] == "COMPLETED"
                                statuses = []
                                for mapping in (event.get("referenceMappings") or {}).values():
                                    if mapping.get("citationId"):
                                        result = await client.get("/documents/citation", params={"citationId": mapping["citationId"]})
                                        statuses.append(result.status_code)
                                summary["citationStatuses"] = statuses
                                assert statuses and all(status == 200 for status in statuses)
                                assert summary["bodyBeforeFinalGate"] and summary["chunks"] >= 2
                                summary["status"] = "PASS"
                                break
            except Exception as exc:  # noqa: BLE001 - preserve failed first attempts for review
                summary.update(status="FAIL", error=repr(exc))
            (private / (name + "-events.json")).write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            summaries.append(summary)
            (checkpoint / "live-results.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
            print(name, summary["status"], "first_ms=", summary.get("firstBodyMs"),
                  "complete_ms=", summary.get("completionMs"), "chunks=", summary["chunks"], flush=True)
        usage = await client.get("/users/usage")
        (checkpoint / "application-usage.json").write_text(usage.text, encoding="utf-8")
        if any(row["status"] != "PASS" for row in summaries):
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--case", choices=[name for name, _ in QUESTIONS])
    args = parser.parse_args()
    asyncio.run(main(args.checkpoint.resolve(), args.case))
