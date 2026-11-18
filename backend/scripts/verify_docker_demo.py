"""Real HTTP/WS acceptance of the deployed Demo; use only its private test fixture."""

import asyncio
import json
import os
from pathlib import Path
import time
import uuid

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("DOCKER_DEMO_ACCEPTANCE_DIR",str(ROOT/"data/checkpoints/docker-demo-20261020")))


async def chat(client, token, question, label):
    saved = OUTPUT/f"ws-{label}.json"
    if saved.exists():
        prior = json.loads(saved.read_text(encoding="utf-8"))
        generation = prior["snapshot"]["generationId"]
        current = client.get("/chat/generation/"+generation)
        if current.status_code == 200 and current.json()["data"]["status"] == "COMPLETED":
            return current.json()["data"], prior["events"]
    created = client.post("/users/conversations"); created.raise_for_status()
    conversation = created.json()["data"]["conversationId"]
    client.put(f"/users/conversations/{conversation}/switch").raise_for_status()
    events = []
    async with websockets.connect("ws://127.0.0.1:9527/proxy-ws/chat", proxy=None, max_size=8*1024*1024) as socket:
        await socket.send(json.dumps({"type":"auth","token":token}))
        assert json.loads(await socket.recv())["type"] == "connection"
        await socket.send(question)
        deadline = time.monotonic()+180
        while time.monotonic() < deadline:
            event = json.loads(await asyncio.wait_for(socket.recv(),timeout=60))
            events.append(event)
            if event.get("type") == "completion":
                assert event["status"] == "finished"
                generation = event["generationId"]
                break
            # Tool validation failures are recoverable structured events. Only
            # a generation-level failure fails the transport acceptance here.
            if event.get("type") == "error":
                raise AssertionError(event.get("error"))
        else:
            raise TimeoutError("WebSocket generation timed out")
    snapshot = client.get("/chat/generation/"+generation).json()["data"]
    assert snapshot["status"] == "COMPLETED" and snapshot["content"]
    (OUTPUT/f"ws-{label}.json").write_text(json.dumps({"events":events,"snapshot":snapshot},ensure_ascii=False,indent=2),encoding="utf-8")
    return snapshot, events


def main():
    fixture = json.loads((OUTPUT/"private/acceptance-fixture.json").read_text(encoding="utf-8"))
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:9527/api/v1",timeout=60,trust_env=False) as client:
        assert httpx.get("http://127.0.0.1:8000/health",trust_env=False).json()["status"] == "ok"
        checks.append("api_health")
        assert client.get("/documents/accessible").status_code in {401,403}
        response = client.post("/users/login",json={"username":fixture["username"],"password":fixture["password"]})
        response.raise_for_status(); token = response.json()["data"]["token"]
        client.headers["Authorization"] = "Bearer "+token
        other = client.post("/users/login",json={"username":fixture["foreignUsername"],"password":fixture["password"]})
        other.raise_for_status()
        foreign = {"Authorization":"Bearer "+other.json()["data"]["token"]}
        checks.append("frontend_proxy_authentication")
        for case in fixture["cases"]:
            url = "/diagnoses/"+case["diagnosisId"]
            data = client.get(url).json()["data"]
            assert client.get(url,headers=foreign).status_code == 404
            if case["label"] == "human":
                assert data["status"] == "HANDED_OFF"
                for _ in range(2):
                    assert client.post(url+"/resume",json={"generationId":case["generationId"]}).status_code == 202
                handoffs = client.get("/support/handoffs").json()["data"]
                assert sum(h.get("diagnosisId") == case["diagnosisId"] for h in handoffs) == 1
            else:
                previous = (data.get("workflow") or {}).get("rechecks") or []
                if previous and previous[-1]["requestId"] == case["newRequestId"]:
                    assert data["status"] == ("RESOLVED" if case["label"] == "401" else "WAITING_USER_ACTION")
                    checks.append("diagnosis_"+case["label"]+"_and_owner_scope")
                    continue
                wanted = "KEY_EXPIRED" if case["label"] == "401" else "RATE_LIMIT"
                assert any(c["cause"] == wanted and c["status"] == "SUPPORTED" for c in data["candidates"])
                payload = {"requestId":case["newRequestId"],"expectedRevision":data["revision"],"idempotencyKey":"docker-acceptance-"+case["label"]}
                first = client.post(url+"/rechecks",json=payload); assert first.status_code == 202
                deadline = time.monotonic()+30
                while time.monotonic() < deadline:
                    after = client.get(url).json()["data"]
                    if after["workflow"].get("rechecks"):
                        break
                    time.sleep(.2)
                assert after["status"] == ("RESOLVED" if case["label"] == "401" else "WAITING_USER_ACTION")
                again = client.post(url+"/rechecks",json=payload)
                assert again.status_code == 202 and again.json()["data"]["generationId"] == first.json()["data"]["generationId"]
            checks.append("diagnosis_"+case["label"]+"_and_owner_scope")
        snapshot, _ = asyncio.run(chat(client,token,f"请求 {fixture['cases'][0]['oldRequestId']} 返回401，请核查。","diagnostic"))
        diagnosis = client.get("/diagnoses/"+snapshot["diagnosisId"]).json()["data"]
        assert any(c["cause"] == "KEY_EXPIRED" and c["status"] == "SUPPORTED" for c in diagnosis["candidates"])
        checks.append("nginx_websocket_langgraph_diagnosis")
        billing_question = os.environ.get("DOCKER_DEMO_BILLING_QUESTION","请核实2026-10的套餐、用量和账单金额。")
        snapshot, events = asyncio.run(chat(client,token,billing_question,"billing"))
        tools = {e.get("tool") for e in events if e.get("type") == "tool_call"}
        assert {"mcp__billing__get_plan","mcp__billing__get_usage","mcp__billing__get_invoice"} <= tools
        assert "12" in snapshot["content"]
        checks.append("real_billing_mcp_and_model_answer")
        owned = client.get("/documents/uploads").json()["data"]
        prior_md = next((d for d in owned if d["fileName"] == "docker-acceptance.md"),None)
        if prior_md:
            raw = client.get("/documents/download-by-md5",params={"fileMd5":prior_md["fileMd5"]}).text
            marker = raw.splitlines()[0].removeprefix("# ").strip()
        else:
            marker = "DockerAccept"+uuid.uuid4().hex[:10]
        handles = []
        def wait_job(job):
            deadline = time.monotonic()+180
            while time.monotonic() < deadline:
                state = client.get("/documents/processing-jobs/"+job).json()["data"]
                if state["status"] == "COMPLETED":
                    return state
                if state["status"] in {"FAILED","CANCELLED"}:
                    raise AssertionError(state)
                time.sleep(.5)
            raise TimeoutError("Kafka indexing did not finish")
        for name, raw, mime in (("acceptance.md",f"# {marker}\nThe acceptance rotation window is 17 minutes.".encode(),"text/markdown"),
                ("equivalent.pdf",(ROOT/"tests/fixtures/docling/equivalent.pdf").read_bytes(),"application/pdf"),
                ("equivalent.docx",(ROOT/"tests/fixtures/docling/equivalent.docx").read_bytes(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document")):
            prior = next((d for d in owned if d["fileName"] == "docker-"+name),None)
            if prior:
                assert prior["vectorizationStatus"] == "COMPLETED",prior
                document = {"documentId":prior["id"],**prior}
            else:
                upload = client.post("/documents/content",files={"file":("docker-"+name,raw,mime)},data={"metadata":json.dumps({"product":"Docker Acceptance"})})
                upload.raise_for_status(); document = upload.json()["data"]
                wait_job(document["processingJobId"])
            handles.append(document)
            assert client.get("/documents/download-by-md5",params={"fileMd5":document["fileMd5"]},headers=foreign).status_code == 404
            checks.append("kafka_minio_docling_index_"+name.rsplit('.',1)[-1])
        result = client.get("/search/hybrid",params={"query":marker+" rotation window","topK":6})
        result.raise_for_status()
        match = next(r for r in result.json()["data"] if r["fileMd5"] == handles[0]["fileMd5"])
        citation = match["citationId"]
        assert client.get("/documents/citation",params={"citationId":citation}).status_code == 200
        assert client.get("/documents/citation",params={"citationId":citation},headers=foreign).status_code == 404
        checks.append("real_qwen_es_retrieval_and_citation_acl")
        original = handles[0]
        revision = client.post(f"/documents/by-id/{original['documentId']}/content-revisions",files={"file":("docker-acceptance.md",f"# {marker}\nThe acceptance rotation window is 23 minutes.".encode(),"text/markdown")},data={"expectedRevision":original["inputRevision"],"metadata":"{}"})
        revision.raise_for_status(); wait_job(revision.json()["data"]["processingJobId"])
        assert client.get("/documents/citation",params={"citationId":citation}).status_code == 410
        checks.append("content_revision_invalidates_old_citation")
        for document in handles:
            assert client.delete("/documents/"+document["fileMd5"]).status_code == 200
        result = client.get("/search/hybrid",params={"query":marker,"topK":6}).json()["data"]
        assert all(r["fileMd5"] not in {d["fileMd5"] for d in handles} for r in result)
        checks.append("deleted_knowledge_not_retrieved")
        usage = client.get("/users/usage").json()["data"]
    report = {"passed":True,"checks":checks,"temporaryUserId":fixture["userId"],"usage":usage,"documentsCreated":len(handles),"existingKnowledgeReset":False}
    (OUTPUT/"http-acceptance.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"passed":True,"checks":checks}))


if __name__ == "__main__":
    main()
