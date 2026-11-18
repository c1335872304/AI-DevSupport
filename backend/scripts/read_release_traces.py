"""Join release WebSocket generations with redacted Langfuse observation metadata."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


async def main(root: Path):
    generations = {}
    for filename in sorted(root.glob("*-timing.jsonl")):
        for line in filename.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            generations[row["generationId"]] = (filename.name, row["startedUtc"])
    semaphore = asyncio.Semaphore(4)

    async with httpx.AsyncClient(
        base_url=os.environ["LANGFUSE_BASE_URL"], auth=(os.environ["LANGFUSE_PUBLIC_KEY"],
                                                       os.environ["LANGFUSE_SECRET_KEY"]),
        timeout=8, trust_env=False,
    ) as client:
        async def one(gid, source, start):
            traceid = hashlib.sha256(f"paismart:chat:{gid}".encode()).hexdigest()[:32]
            interval = datetime.fromisoformat(start) - timedelta(seconds=10)
            report = {"generationId": gid, "traceId": traceid, "source": source}
            async with semaphore:
                try:
                    response = await client.get("/api/public/v2/observations", params={
                        "traceId": traceid, "fields": "core,basic,usage",
                        "fromStartTime": interval.isoformat(),
                        "toStartTime": datetime.now(timezone.utc).isoformat(), "limit": 100,
                    })
                    response.raise_for_status()
                    values = response.json()["data"]
                    report["root"] = any(item.get("name") == "customer_service.question"
                                         and not item.get("parentObservationId") for item in values)
                    report["models"] = [
                        {key: item.get(key) for key in ("id", "name", "type", "usageDetails")}
                        for item in values if item.get("type", "").upper() == "GENERATION"
                    ]
                except httpx.HTTPStatusError as error:
                    report["error"] = f"http_{error.response.status_code}"
                except (httpx.RequestError, ValueError, KeyError) as error:
                    report["error"] = type(error).__name__
                return report

        results = await asyncio.gather(*(one(gid, *item) for gid, item in generations.items()))
    with (root / "langfuse-join.jsonl").open("w", encoding="utf-8") as out:
        for row in results:
            out.write(json.dumps(row) + "\n")
    print(f"traces={len(results)} with_root={sum(row.get('root', False) for row in results)} "
          f"query_errors={sum('error' in row for row in results)}")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
