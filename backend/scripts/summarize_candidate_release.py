"""Recompute release quality, latency and DeepSeek usage from acceptance JSONL."""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()] \
        if path.exists() else []


def distribution(values) -> dict:
    samples = sorted(value for value in values if value is not None)
    return {
        "n": len(samples),
        **{name: round(samples[math.ceil(pct * len(samples)) - 1], 3) if samples else None
           for name, pct in (("p50", .50), ("p95", .95))},
    }


def usage(entries: list[dict]) -> dict:
    attempts = {row["requestId"]: row for row in entries if row["event"] == "attempt"}
    results = {row["requestId"]: row for row in entries if row["event"] == "result"}
    counts = Counter()
    prices = [0.0, 0.0]
    for row in results.values():
        actual = row.get("usage") or {}
        if "prompt_tokens" not in actual or "completion_tokens" not in actual:
            counts["missingUsage"] += 1
            continue
        prompt, output = actual["prompt_tokens"], actual["completion_tokens"]
        hit, miss = actual.get("prompt_cache_hit_tokens"), actual.get("prompt_cache_miss_tokens")
        counts["input"] += prompt
        counts["output"] += output
        at = datetime.fromisoformat(row["utc"])
        # This acceptance was on a non-holiday Wednesday. Retain the time
        # split instead of pricing every request at its cheapest rate.
        multiplier = 2 if at.weekday() < 5 and (1 <= at.hour < 4 or 6 <= at.hour < 10) else 1
        if hit is not None and miss is not None and hit + miss == prompt:
            counts["hit"] += hit
            counts["miss"] += miss
            value = hit * .003 + miss * .15 + output * .60
            low = high = value
        else:
            counts["unknownCache"] += 1
            low = prompt * .003 + output * .60
            high = prompt * .15 + output * .60
        prices[0] += low * multiplier / 1_000_000
        prices[1] += high * multiplier / 1_000_000
    return {
        "attempts": len(attempts), "resultRows": len(results),
        "success": sum(row.get("status") == 200 and not row.get("error") for row in results.values()),
        "missingResult": len(attempts.keys() - results.keys()),
        "truncations": sum(row.get("finishReason") == "length" for row in results.values()),
        **{field: counts[field] for field in ("input", "output", "hit", "miss", "missingUsage", "unknownCache")},
        "reportedUsageUsd": [round(v, 8) for v in prices],
        "providerLatencyMs": distribution(row.get("elapsedMs") for row in results.values()),
    }


def quality(entries: list[dict]) -> dict:
    passed = {row["caseId"] for row in entries if row.get("automatedPass")}
    pairs = Counter(key.rsplit("-", 1)[0] for key in passed)
    layers = [row.get("layers", {}).get("answerQuality", {}).get("details", {}) for row in entries]
    citations = [layer.get("citations", {}) for layer in layers]
    return {
        "cases": len(entries), "passed": len(passed), "pairs": sum(total == 2 for total in pairs.values()),
        "requiredCitations": sum(item.get("requiredFactCount", 0) for item in citations),
        "passedCitations": sum(item.get("passedFactCount", 0) for item in citations),
        "truncated": [row["caseId"] for row in entries if row.get("truncated")],
        "failures": [{"caseId": row["caseId"], "error": re.split(r"[(:]", row["error"], 1)[0] if row.get("error") else None,
                      "generationId": (row.get("snapshot") or {}).get("generationId"),
                      "layers": [name for name, layer in row.get("layers", {}).items() if not layer.get("passed")]}
                     for row in entries if row["caseId"] not in passed],
    }


def timings(entries: list[dict]) -> dict:
    return {
        "rows": len(entries),
        "firstVisibleMs": distribution(row.get("firstVisibleMs") for row in entries),
        "persistedMs": distribution(row.get("persistedMs") for row in entries),
        "clarificationMs": distribution(row.get("persistedMs") for row in entries if row.get("clarifications")),
        "toolMs": distribution(tool.get("durationMs") for row in entries for tool in row.get("tools", ())),
        "states": dict(Counter(row.get("status") for row in entries)),
    }


def summaries(root: Path, version: str) -> dict:
    smoke_name = f"{version}-smoke-controlled" if (root / f"{version}-smoke-controlled.jsonl").exists() else f"{version}-smoke"
    window_name = f"{version}-windows-controlled" if (root / f"{version}-windows-controlled.jsonl").exists() else f"{version}-windows"
    frozen = rows(root / f"{version}-frozen.jsonl")
    frozen_requests = rows(root / f"{version}-frozen-requests.jsonl")
    smoke = rows(root / f"{smoke_name}.jsonl")
    smoke_requests = rows(root / f"{smoke_name}-requests.jsonl")
    smoke_timing = rows(root / f"{smoke_name}-timing.jsonl")
    window_requests = rows(root / f"{window_name}-requests.jsonl")
    fault_requests = rows(root / f"{version}-windows-requests.jsonl")
    window_times = rows(root / f"{window_name}-timing.jsonl")
    faults_times = rows(root / f"{version}-faults-timing.jsonl")
    window_ids, fault_ids = [{row["generationId"] for row in entries} for entries in (window_times, faults_times)]
    results = {
        "frozen": {
            "quality": quality(frozen),
            "firstVisibleMs": distribution(row.get("artifact", {}).get("timing", {}).get("firstTokenMs") for row in frozen),
            "totalMs": distribution(row.get("artifact", {}).get("timing", {}).get("totalMs") for row in frozen),
            "usage": usage([row for row in frozen_requests if row.get("caseId") != "smoke"]),
            "providerSmokeUsage": usage([row for row in frozen_requests if row.get("caseId") == "smoke"]),
        },
        "smoke": {"quality": quality(smoke), "timing": timings(smoke_timing),
                  "usage": usage(smoke_requests)},
        "windows": {
            "turns": len(rows(root / f"{window_name}.jsonl")), "timing": timings(window_times),
            "usage": usage([row for row in window_requests if row.get("generationId") in window_ids]),
        },
        "faults": {
            "timing": timings(faults_times),
            "recoveryMs": distribution(item["handoffRecoverySeconds"] * 1000
                                       for item in rows(root / f"{version}-faults.jsonl")
                                       if "handoffRecoverySeconds" in item),
            "usage": usage([row for row in fault_requests if row.get("generationId") in fault_ids]),
        },
        "unjoined": usage([row for row in window_requests if row.get("generationId") not in window_ids | fault_ids]),
    }
    by_generation = defaultdict(list)
    unique_requests = { (row["requestId"], row["event"]): row
                        for row in frozen_requests + smoke_requests + window_requests + fault_requests }
    for row in unique_requests.values():
        if row.get("generationId"):
            by_generation[row["generationId"]].append(row)
    results["generations"] = {key: usage(entries) for key, entries in by_generation.items()}
    by_conversation = defaultdict(list)
    for row in window_times + faults_times + smoke_timing:
        if row.get("conversationId"):
            by_conversation[row["conversationId"]].extend(by_generation[row["generationId"]])
    results["conversations"] = {key: usage(entries) for key, entries in by_conversation.items()}
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    report = {version: summaries(args.evidence, version) for version in ("baseline", "candidate")}
    print(json.dumps(report, ensure_ascii=False, indent=2))
