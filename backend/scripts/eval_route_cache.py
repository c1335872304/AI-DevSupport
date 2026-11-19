"""Save/reset/restore only the frozen evaluation questions' routing cache keys."""

import asyncio
import json
import sys
import time
from pathlib import Path


async def main(action):
    from app.agent.route_cache import route_cache

    root = Path("/evaluation")
    state = root / "private/route-cache.json"
    client = await route_cache._redis()
    if client is None:
        print("Routing cache disabled by existing configuration")
        return
    cases = json.loads((root / "cases.json").read_text(encoding="utf8"))["cases"]
    keys = {route_cache._key(c["question"]) for c in cases}
    if action == "backup":
        assert not state.exists()
        rows = {key: {"value": await client.get(key), "ttl": await client.pttl(key)} for key in keys}
        state.write_text(json.dumps({"savedAt": time.time(), "keys": rows}), encoding="utf8")
    elif action == "reset":
        saved = json.loads(state.read_text())
        assert keys == set(saved["keys"])
        await client.delete(*keys)
    elif action == "restore":
        saved = json.loads(state.read_text())
        assert keys == set(saved["keys"])
        elapsed = int((time.time() - saved["savedAt"]) * 1000)
        for key, row in saved["keys"].items():
            remaining = row["ttl"] - elapsed
            if row["value"] is None or row["ttl"] != -1 and remaining <= 0:
                await client.delete(key)
            elif row["ttl"] == -1:
                await client.set(key, row["value"])
            else:
                await client.set(key, row["value"], px=remaining)
    else:
        raise ValueError(action)
    await client.aclose()
    print(f"Only {len(keys)} frozen evaluation route-cache keys: {action}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
