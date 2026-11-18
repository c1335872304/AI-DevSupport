"""Recompute the frozen evidence-packing comparison without provider calls."""

import hashlib
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path

import summarize_independent_answers as summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/checkpoints/evidence-budget-20261020"
DOCS = ROOT.parent / "docs/04-testing"


def read_usage(path):
    requests, usages = {}, {}
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event["event"] == "request":
            requests[event["request"]] = event
        elif event["event"] == "usage":
            usages[event["request"]] = event
    return requests, usages


def amount(request, event, *, cache=True):
    u = event["usage"]
    if request["kind"] == "llm":
        return (
            (
                u["prompt_cache_hit_tokens"] * 0.02 + u["prompt_cache_miss_tokens"]
                if cache
                else u["prompt_tokens"]
            )
            + u["completion_tokens"] * 4
        ) / 1e6
    return u["total_tokens"] * 0.5 / 1e6


def main():
    requests, usages = read_usage(OUT / "provider-usage.jsonl")
    assert set(requests) == set(usages), "Every paid request must have observed usage"
    result = {"groups": {}, "cases": {}}
    for phase in ("baseline", "final"):
        folder = OUT / phase
        if phase == "final":
            (folder / "provider-usage.jsonl").write_bytes((OUT / "provider-usage.jsonl").read_bytes())
        review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
        for reviewed in review["cases"]:
            assert (
                hashlib.sha256((folder / (reviewed["id"] + ".json")).read_bytes()).hexdigest()
                == reviewed["artifactSha256"]
            ), "Answer changed after manual review"
        summary.OUT, summary.DATASET, summary.REVIEW = folder, folder / "cases.json", folder / "review.json"
        summary.REPORT = DOCS / f"EVIDENCE_BUDGET_{phase.upper()}_CASES_2026-10-20.md"
        summary.main()
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
        rows = []
        for row in metrics["cases"]:
            assert not any(
                row[k]
                for k in (
                    "missingUsage",
                    "unmappedReferences",
                    "foreignReferences",
                    "declaredNameMismatches",
                    "toolFailures",
                )
            ), row["id"]
            assert row["citationAccessOk"] == row["citationAccessTotal"]
            artifact = json.loads((folder / (row["id"] + ".json")).read_text(encoding="utf-8"))
            start = datetime.fromisoformat(artifact["startedAt"])
            end = start + timedelta(milliseconds=artifact["elapsedMs"])
            selected = [
                rid
                for rid, r in requests.items()
                if r["caseId"] == row["id"] and start <= datetime.fromisoformat(r["startedAt"]) <= end
            ]
            llm = [usages[rid]["usage"] for rid in selected if requests[rid]["kind"] == "llm"]
            row.update(
                promptTokens=sum(u["prompt_tokens"] for u in llm),
                completionTokens=sum(u["completion_tokens"] for u in llm),
                cacheHitTokens=sum(u["prompt_cache_hit_tokens"] for u in llm),
                allMissCny=sum(amount(requests[rid], usages[rid], cache=False) for rid in selected),
                context=[e for e in artifact["events"] if e.get("type") == "document_context_budget"],
            )
            rows.append(row)
        result["cases"][phase] = rows
        groups = {}
        for name, ids in [
            ("original4", {"C01", "C02", "C03", "C04"}),
            ("document6", {"C01", "C02", "C03", "C04", "C05", "C06"}),
            ("diagnosis", {"D01", "D02", "D03", "D04", "D05", "D06"}),
        ]:
            group = [r for r in rows if r["id"] in ids]
            groups[name] = {
                k: sum(r[k] for r in group)
                for k in [
                    "llmCalls",
                    "embeddingCalls",
                    "promptTokens",
                    "completionTokens",
                    "cacheHitTokens",
                    "estimatedCny",
                    "allMissCny",
                ]
            }
            groups[name]["meanMs"] = statistics.mean(r["elapsedMs"] for r in group)
        result["groups"][phase] = groups
        for case, status in [("D02", "RESOLVED"), ("D04", "WAITING_USER_ACTION")]:
            assert (
                json.loads((folder / f"{case}.json").read_text(encoding="utf-8"))["diagnosis"]["status"]
                == status
            )
    turns = set()
    for folder in [
        OUT / name
        for name in [
            "baseline",
            "final",
            "first-compression-attempt",
            "second-compression-attempt",
            "third-document-attempt",
            "fourth-scope-attempt",
                "merge-scope-attempt",
        ]
    ]:
        for path in folder.glob("*.json"):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            if "case" in artifact and "startedAt" in artifact:
                turns.add((artifact["case"]["id"], artifact["startedAt"]))
    result["allAttempts"] = {
        "turns": len(turns),
        "providerRequests": len(requests),
        "usageCaptured": len(usages),
        "estimatedCny": sum(amount(requests[rid], u) for rid, u in usages.items()),
    }
    (OUT / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("COMPARISON", json.dumps({k: v for k, v in result.items() if k != "cases"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
