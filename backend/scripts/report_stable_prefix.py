"""Audit saved natural E2E and format-only cache experiments, no model calls."""

import hashlib
import json
import re
import statistics
from datetime import datetime, timedelta
from pathlib import Path

import summarize_independent_answers as answers
from report_evidence_budget import amount, read_usage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/checkpoints/stable-prefix-20261020"
DOCS = ROOT.parent / "docs/artifacts/2026-10-20"


def verify_review(folder):
    review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    for item in review["cases"]:
        assert (
            hashlib.sha256((folder / (item["id"] + ".json")).read_bytes()).hexdigest()
            == item["artifactSha256"]
        ), "Reviewed answer changed"
    return {item["id"]: item for item in review["cases"]}


def main():
    requests, usage = read_usage(OUT / "provider-usage.jsonl")
    assert set(requests) == set(usage), "Missing provider usage"
    assert all(r["caseId"] != "unattributed" for r in requests.values())
    allocated = set()

    def enrich(artifact, case_id):
        start = datetime.fromisoformat(artifact["startedAt"])
        end = start + timedelta(milliseconds=artifact["elapsedMs"])
        selected = [
            rid
            for rid, r in requests.items()
            if r["caseId"] == case_id and start <= datetime.fromisoformat(r["startedAt"]) <= end
        ]
        assert not allocated.intersection(selected), "Double counted provider request"
        allocated.update(selected)
        llm = [usage[rid]["usage"] for rid in selected if requests[rid]["kind"] == "llm"]
        for rid in selected:
            if requests[rid]["kind"] == "llm":
                assert usage[rid]["responseModel"] == "deepseek-flash"
                u = usage[rid]["usage"]
                assert u["prompt_cache_hit_tokens"] + u["prompt_cache_miss_tokens"] == u["prompt_tokens"]
        return {
            "id": case_id,
            "elapsedMs": artifact["elapsedMs"],
            "firstContentMs": artifact.get("firstContentMs"),
            "llmCalls": len(llm),
            "embeddingCalls": sum(requests[rid]["kind"] == "embedding" for rid in selected),
            "promptTokens": sum(u["prompt_tokens"] for u in llm),
            "cacheHitTokens": sum(u["prompt_cache_hit_tokens"] for u in llm),
            "completionTokens": sum(u["completion_tokens"] for u in llm),
            "estimatedCny": sum(amount(requests[rid], usage[rid]) for rid in selected),
            "allMissCny": sum(amount(requests[rid], usage[rid], cache=False) for rid in selected),
        }

    def aggregate(rows):
        keys = [
            "llmCalls",
            "embeddingCalls",
            "promptTokens",
            "cacheHitTokens",
            "completionTokens",
            "estimatedCny",
            "allMissCny",
        ]
        total = {key: sum(row[key] for row in rows) for key in keys}
        total.update(
            cases=len(rows),
            meanMs=statistics.mean(row["elapsedMs"] for row in rows),
            meanFirstContentMs=statistics.mean(
                row["firstContentMs"] for row in rows if row.get("firstContentMs") is not None
            ),
            cacheHitRatio=total["cacheHitTokens"] / total["promptTokens"] if total["promptTokens"] else None,
        )
        return total

    result = {"natural": {}, "probe": {}}
    transcript = [
        "# 稳定前缀独立缓存实验：逐题答复",
        "",
        "固定已授权证据的格式对照，不替代真实检索验收；来源签名不公开。",
        "",
    ]
    for phase in ["baseline", "final"]:
        folder = OUT / phase
        if phase == "final":
            (folder / "provider-usage.jsonl").write_bytes((OUT / "provider-usage.jsonl").read_bytes())
        reviews = verify_review(folder)
        answers.OUT, answers.DATASET, answers.REVIEW = folder, folder / "cases.json", folder / "review.json"
        answers.REPORT = DOCS / f"STABLE_PREFIX_{phase.upper()}_CASES_2026-10-20.md"
        answers.main()
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
        natural = []
        for item in metrics["cases"]:
            assert not any(
                item[key]
                for key in [
                    "missingUsage",
                    "unmappedReferences",
                    "foreignReferences",
                    "declaredNameMismatches",
                    "toolFailures",
                ]
            ), item["id"]
            assert item["citationAccessOk"] == item["citationAccessTotal"]
            artifact = json.loads((folder / (item["id"] + ".json")).read_text(encoding="utf-8"))
            row = enrich(artifact, item["id"])
            row["review"] = reviews[item["id"]]["overall"]
            natural.append(row)
        for case, expected in [("D02", "RESOLVED"), ("D04", "WAITING_USER_ACTION"), ("D06", "HANDED_OFF")]:
            artifact = json.loads((folder / (case + ".json")).read_text(encoding="utf-8"))
            assert artifact["diagnosis"]["status"] == expected
        result["natural"][phase] = {
            "all": aggregate(natural),
            "documents": aggregate([row for row in natural if row["id"].startswith("C")]),
            "diagnosis": aggregate([row for row in natural if row["id"].startswith("D")]),
            "cases": natural,
        }
        probe_folder = folder / "cache-probe"
        probe_review = verify_review(probe_folder)
        probe = []
        for path in sorted(probe_folder.glob("P-*.json")):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            assert artifact["status"] == "COMPLETED"
            row = {
                **enrich(artifact, artifact["id"]),
                "step": artifact["step"],
                "vendor": artifact["vendor"],
                "review": probe_review[artifact["id"]]["overall"],
            }
            mapping = {str(r["referenceNumber"]): r for r in artifact["references"]}
            cited = set(re.findall(r"来源\s*#(\d+)", artifact["answer"]))
            assert cited and cited.issubset(mapping)
            assert all(r["fileName"].startswith(artifact["vendor"] + "-") for r in mapping.values())
            assert all(
                mapping[n]["fileName"] == file
                for n, file in re.findall(r"来源\s*#(\d+)\s*[:：]\s*([\w.-]+\.md)", artifact["answer"])
            )
            probe.append(row)
            transcript += [
                f"## {phase} · {artifact['id']}",
                "",
                artifact["question"],
                "",
                "审阅："
                + probe_review[artifact["id"]]["overall"]
                + "；"
                + probe_review[artifact["id"]]["note"],
                "",
                artifact["answer"],
                "",
            ]
        assert len(probe) == 12
        if phase == "final":
            for group in ["DS", "QW", "GPT"]:
                artifacts = [
                    json.loads((probe_folder / f"P-{group}-{step}.json").read_text(encoding="utf-8"))
                    for step in range(1, 5)
                ]
                assert len({row["documentPrefixSha256"] for row in artifacts}) == 1
                assert artifacts[0]["messageSha256"] == artifacts[3]["messageSha256"]
        result["probe"][phase] = {
            "all": aggregate(probe),
            "priming": aggregate([r for r in probe if r["step"] == 1]),
            "changedQuestion": aggregate([r for r in probe if r["step"] in [2, 3]]),
            "exactRepeat": aggregate([r for r in probe if r["step"] == 4]),
            "byStep": {str(step): aggregate([r for r in probe if r["step"] == step]) for step in range(1, 5)},
            "cases": probe,
        }
    assert allocated == set(requests), "Unallocated provider costs"
    result["allAttempts"] = {
        "naturalAnswers": 28,
        "probeAnswers": 24,
        "providerRequests": len(requests),
        "usageCaptured": len(usage),
        "estimatedCny": sum(amount(requests[rid], event) for rid, event in usage.items()),
    }
    (OUT / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "STABLE_PREFIX_CACHE_PROBE_CASES_2026-10-20.md").write_text(
        "\n".join(transcript), encoding="utf-8"
    )
    print(
        "COMPARISON",
        json.dumps(
            {
                category: {
                    phase: {k: v for k, v in data.items() if k != "cases"}
                    for phase, data in result[category].items()
                }
                for category in ["natural", "probe"]
            },
            ensure_ascii=False,
        ),
    )
    print("ALL_ATTEMPTS", json.dumps(result["allAttempts"]))


if __name__ == "__main__":
    main()
