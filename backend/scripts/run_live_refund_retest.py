"""Run one controlled live WebSocket regression without printing credentials.

The command takes credentials only from arguments, sends one question through
the public chat transport, and prints a redacted JSON summary suitable for a
test report.  It intentionally does not persist access tokens or raw events.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data")
    return value if isinstance(value, dict) else {}


def _ws_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/chat"


async def main(args: argparse.Namespace) -> None:
    api_url = args.api_url.rstrip("/")
    headers: dict[str, str]
    async with httpx.AsyncClient(base_url=api_url, timeout=30.0) as client:
        if args.direct_user_id is not None:
            # The fixture account is created by the WebSocket E2E test and has
            # preallocated test credits.  Generate its normal signed access
            # token locally so no fixture password is stored or printed.
            backend_root = str(Path(__file__).resolve().parents[1])
            if backend_root not in sys.path:
                sys.path.insert(0, backend_root)
            from app.core.security import create_access_token

            access_token = create_access_token(args.username, args.direct_user_id, args.direct_role, args.token_version)
            auth_mode = "signed test-fixture access token"
        else:
            login = await client.post("/api/v1/users/login", json={"username": args.username, "password": args.password})
            login.raise_for_status()
            access_token = str(_data(login.json()).get("token") or "")
            auth_mode = "HTTP login access token"
        if not access_token:
            raise RuntimeError("Login succeeded without an access token")
        headers = {"Authorization": f"Bearer {access_token}"}
        usage_before = _data((await client.get("/api/v1/users/usage", headers=headers)).json())

        event_counts: Counter[str] = Counter()
        event_order: list[str] = []
        final_event: dict[str, Any] = {}
        generation_id = ""
        async with websockets.connect(_ws_url(api_url), open_timeout=20, close_timeout=10) as socket:
            await socket.send(json.dumps({"type": "auth", "token": access_token}))
            handshake = json.loads(await asyncio.wait_for(socket.recv(), timeout=20))
            if handshake.get("type") != "connection":
                raise RuntimeError(f"Unexpected WebSocket handshake: {handshake.get('type')!r}")
            await socket.send(args.question)
            while True:
                raw = await asyncio.wait_for(socket.recv(), timeout=args.timeout)
                event = json.loads(raw)
                kind = str(event.get("type") or f"error:{event.get('code', 'unknown')}")
                event_counts[kind] += 1
                if kind not in event_order:
                    event_order.append(kind)
                generation_id = str(event.get("generationId") or generation_id)
                if event.get("type") == "completion" or event.get("code"):
                    final_event = event
                    break

        if not generation_id:
            raise RuntimeError("The stream did not provide a generation id")
        snapshot_response = await client.get(f"/api/v1/chat/generation/{generation_id}", headers=headers)
        snapshot_response.raise_for_status()
        snapshot = _data(snapshot_response.json())
        usage_after = _data((await client.get("/api/v1/users/usage", headers=headers)).json())

    def balance(usage: dict[str, Any]) -> int | None:
        llm = usage.get("llm")
        value = llm.get("remainingTokens") if isinstance(llm, dict) else None
        return int(value) if isinstance(value, int | float | str) and str(value).strip() else None

    before_balance = balance(usage_before)
    after_balance = balance(usage_after)
    result = {
        "transport": f"{auth_mode} + WebSocket /chat",
        "question": args.question,
        "generationId": generation_id,
        "streamEventOrder": event_order,
        "streamEventCounts": dict(event_counts),
        "completionType": final_event.get("type"),
        "completionError": final_event.get("error"),
        "generationStatus": snapshot.get("status"),
        "answer": snapshot.get("content"),
        "referenceMappings": snapshot.get("referenceMappings", {}),
        "llmTokenBalanceBefore": before_balance,
        "llmTokenBalanceAfter": after_balance,
        "llmTokenConsumed": (before_balance - after_balance) if before_balance is not None and after_balance is not None else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password")
    parser.add_argument("--direct-user-id", type=int)
    parser.add_argument("--direct-role", default="USER")
    parser.add_argument("--token-version", type=int, default=0)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--question", default="退款政策是什么？")
    parser.add_argument("--timeout", type=float, default=180.0)
    parsed = parser.parse_args()
    if parsed.direct_user_id is None and not parsed.password:
        parser.error("--password is required unless --direct-user-id is supplied")
    asyncio.run(main(parsed))
