"""Real HTTP upload/index/search/citation/update/delete acceptance."""

import hashlib
import json
import time
import uuid
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:18016/api/v1", timeout=40, trust_env=False) as c:
        login = c.post("/users/login", json={"username": "ragaccept", "password": "RagAccept123"})
        login.raise_for_status()
        c.headers["Authorization"] = "Bearer " + login.json()["data"]["token"]
        checks.append("login")
        marker = uuid.uuid4().hex[:12]
        raw = f"# Acceptance {marker}\nAUTH_KEY_INVALID returns HTTP 401. Use Authorization: Bearer TOKEN.\n".encode()
        md5 = hashlib.md5(raw).hexdigest()
        upload = c.post(
            "/upload/chunk",
            data={
                "fileMd5": md5,
                "chunkIndex": "0",
                "totalSize": str(len(raw)),
                "fileName": "acceptance-" + marker + ".md",
                "isPublic": "false",
                "knowledgeProduct": "Acceptance API",
            },
            files={"file": ("sample.md", raw, "text/markdown")},
        )
        upload.raise_for_status()
        checks.append("upload")
        merged = c.post("/upload/merge", json={"fileMd5": md5})
        merged.raise_for_status()
        job = merged.json()["data"]["processingJobId"]

        def wait_job(job_id):
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                response = c.get("/documents/processing-jobs/" + job_id)
                response.raise_for_status()
                data = response.json()["data"]
                if data["status"] == "COMPLETED":
                    return data
                if data["status"] == "FAILED":
                    raise AssertionError(data["lastError"])
                time.sleep(0.2)
            raise RuntimeError("Index job timeout")

        state = wait_job(job)
        assert state["activeIndexAvailable"]
        checks.append("index")
        response = c.get("/search/hybrid", params={"query": marker + " AUTH_KEY_INVALID", "topK": 6})
        response.raise_for_status()
        results = response.json()["data"]
        found = next(r for r in results if r["fileMd5"] == md5)
        citation = found["citationId"]
        checks.append("search")
        detail = c.get("/documents/citation", params={"citationId": citation})
        detail.raise_for_status()
        checks.append("citation")
        updated = c.put(
            "/documents/" + md5 + "/metadata",
            json={"product": "Acceptance API", "version": "v2", "reindex": True},
        )
        updated.raise_for_status()
        wait_job(updated.json()["data"]["processingJobId"])
        checks.append("update-reindex")
        stale = c.get("/documents/citation", params={"citationId": citation})
        assert stale.status_code == 410
        checks.append("old-citation-410")
        key = uuid.uuid4().hex
        forced = c.post("/documents/" + md5 + "/reindex", headers={"Idempotency-Key": key})
        forced.raise_for_status()
        forced_job = forced.json()["data"]["processingJobId"]
        wait_job(forced_job)
        replay = c.post("/documents/" + md5 + "/reindex", headers={"Idempotency-Key": key})
        replay.raise_for_status()
        assert replay.json()["data"]["processingJobId"] == forced_job
        assert wait_job(forced_job)["attempts"] == 1
        checks.append("completed-rebuild-key-replay")
        deleted = c.delete("/documents/" + md5)
        deleted.raise_for_status()
        checks.append("delete")
        rows = c.get("/documents/uploads")
        rows.raise_for_status()
        assert all(r["fileMd5"] != md5 for r in rows.json()["data"])
        assert c.get("/documents/preview", params={"fileMd5": md5}).status_code == 404
        checks.append("deleted-not-readable")
        # Canonical documents distinguish logical identity from content hashes.
        same_raw = f"# Source revision {marker}\nHTTP 401 is the original rule.\n".encode()
        created = []
        for _ in range(2):
            response = c.post(
                "/documents/content", files={"file": ("independent.md", same_raw, "text/markdown")}
            )
            response.raise_for_status()
            data = response.json()["data"]
            wait_job(data["processingJobId"])
            created.append(data)
        assert created[0]["documentId"] != created[1]["documentId"]
        assert (
            created[0]["contentMd5"] == created[1]["contentMd5"]
            and created[0]["fileMd5"] != created[1]["fileMd5"]
        )
        changed = f"# Source revision {marker}\nHTTP 403 is the updated rule.\n".encode()
        response = c.post(
            "/documents/by-id/" + str(created[0]["documentId"]) + "/content-revisions",
            data={"expectedRevision": "0"},
            files={"file": ("updated.md", changed, "text/markdown")},
        )
        response.raise_for_status()
        revision = response.json()["data"]
        wait_job(revision["processingJobId"])
        assert (
            revision["documentId"] == created[0]["documentId"]
            and revision["fileMd5"] == created[0]["fileMd5"]
        )
        conflict = c.post(
            "/documents/by-id/" + str(created[0]["documentId"]) + "/content-revisions",
            data={"expectedRevision": "0"},
            files={"file": ("updated.md", changed, "text/markdown")},
        )
        assert conflict.status_code == 409
        preview = c.get("/documents/preview", params={"fileMd5": created[0]["fileMd5"]})
        preview.raise_for_status()
        assert preview.content == changed
        checks.extend(
            ["independent-identical-documents", "stable-id-content-update", "stale-content-revision-409"]
        )
        for document in created:
            response = c.delete("/documents/" + document["fileMd5"])
            response.raise_for_status()
        (ROOT / "data/checkpoints/e2e-report.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": checks,
                    "source": "real HTTP + MySQL + ES + Qwen; isolated corpus",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Passed: " + ", ".join(checks))


if __name__ == "__main__":
    main()
