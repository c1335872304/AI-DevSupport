import json
from types import SimpleNamespace

import httpx
import pytest

from scripts.answer_eval_observer import CASE, ProviderObserver


async def test_budget_survives_observer_restart(tmp_path):
    path = tmp_path / "usage.jsonl"
    path.write_text(json.dumps({"event": "request", "request": 1, "reservedUpperCny": 0.1}) + "\n")
    (tmp_path / "frozen-inputs.json").write_text(json.dumps({"maxProviderRequests": 1, "maxReservedCny": 10}))
    meter = observer(tmp_path)
    assert meter.requests == 1 and meter.reserved_cny == 0.1
    async with httpx.AsyncClient() as client:
        request = client.build_request(
            "POST", "https://llm.example/v1/chat/completions", json={"messages": []}
        )
        with pytest.raises(RuntimeError, match="budget"):
            await meter.send(httpx.AsyncClient.send, client, request)


def observer(tmp_path):
    return ProviderObserver(
        SimpleNamespace(llm_base_url="https://llm.example/v1", embedding_base_url="https://embed.example/v1"),
        tmp_path / "usage.jsonl",
    )


async def test_nonstream_router_usage_preserved_without_logging_prompts(tmp_path):
    meter = observer(tmp_path)
    payload = {
        "model": "deepseek-flash",
        "usage": {"prompt_tokens": 100, "completion_tokens": 5},
        "choices": [],
    }

    async def handle(request):
        assert b"private-prompt" in request.content
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        request = client.build_request(
            "POST",
            "https://llm.example/v1/chat/completions",
            json={"model": "deepseek-chat", "messages": [{"content": "private-prompt"}]},
        )
        response = await meter.send(httpx.AsyncClient.send, client, request)
        assert response.json() == payload
    rows = [json.loads(s) for s in meter.path.read_text().splitlines()]
    assert rows[-1]["usage"]["completion_tokens"] == 5
    assert "private-prompt" not in meter.path.read_text()


async def test_streamed_usage_does_not_change_sse_and_keeps_case_id(tmp_path):
    meter = observer(tmp_path)
    raw = b'data: {"model":"deepseek-flash","choices":[]}\n\ndata: {"usage":{"prompt_tokens":12,"completion_tokens":3}}\n\ndata: [DONE]\n\n'

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield raw

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream()))
    ) as client:
        token = CASE.set("E01")
        try:
            request = client.build_request(
                "POST", "https://llm.example/v1/chat/completions", json={"model": "deepseek-chat"}
            )
            response = await meter.send(httpx.AsyncClient.send, client, request, stream=True)
            lines = [line async for line in response.aiter_lines()]
            assert "\n".join(lines) + "\n" == raw.decode()
            await response.aclose()
        finally:
            CASE.reset(token)
    usage = [json.loads(s) for s in meter.path.read_text().splitlines() if json.loads(s)["event"] == "usage"]
    assert usage[0]["caseId"] == "E01" and usage[0]["usage"]["prompt_tokens"] == 12


async def test_budget_stops_before_provider_call(tmp_path):
    meter = observer(tmp_path)
    meter.reserved_cny = 10

    async def never(*args, **kwargs):
        raise AssertionError("Must not send")

    async with httpx.AsyncClient() as client:
        request = client.build_request(
            "POST", "https://llm.example/v1/chat/completions", json={"model": "deepseek-chat"}
        )
        with pytest.raises(RuntimeError, match="budget"):
            await meter.send(never, client, request)
