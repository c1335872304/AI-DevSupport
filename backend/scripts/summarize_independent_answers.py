"""Summarize observed usage and publish reviewable answers, without model calls."""

import argparse
import hashlib
import json
import math
import re
import statistics
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/checkpoints/independent-answer-eval-20261020"
DATASET = ROOT / "eval/independent_answers_v1.json"
REVIEW = ROOT / "eval/independent_answers_review_20261020.json"
REPORT = ROOT.parent / "docs/artifacts/2026-10-20/INDEPENDENT_ANSWER_CASES_2026-10-20.md"


def main():
    frozen = json.loads((OUT / "frozen-inputs.json").read_text())
    dataset = DATASET
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == frozen["datasetSha256"]
    cases = json.loads(dataset.read_text(encoding="utf-8"))["cases"]
    reviews = (
        {row["id"]: row for row in json.loads(REVIEW.read_text(encoding="utf-8"))["cases"]}
        if REVIEW.exists()
        else {}
    )
    for case in cases:
        for source in case["sources"]:
            assert (
                hashlib.sha256((ROOT / "vendor_knowledge" / source["file"]).read_bytes()).hexdigest()
                == source["sha256"]
            )
    requests = {}
    usage = {}
    for line in (OUT / "provider-usage.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["event"] == "request":
            requests[event["request"]] = event
        if event["event"] == "usage":
            usage[event["request"]] = event
    totals = {
        "prompt": 0,
        "completion": 0,
        "cacheHit": 0,
        "cacheMiss": 0,
        "embedding": 0,
        "estimatedCny": 0.0,
        "llmCalls": 0,
        "embeddingCalls": 0,
    }
    selected_requests = set()
    rows = []
    transcript = [
        "# 独立端到端回答评测：逐题原始回答与审阅证据",
        "",
        "2026-10-20；本轮逐题原始输出，各轮证据分开保存，不覆盖历史失败。引用令牌不公开，正文与锚点摘要保留。",
        "",
    ]
    for case in cases:
        result = json.loads((OUT / (case["id"] + ".json")).read_text(encoding="utf-8"))
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "vendor": case["vendor"],
            "status": result["status"],
            "elapsedMs": result["elapsedMs"],
            "firstContentMs": result.get("firstContentMs"),
            "estimatedCny": 0.0,
            "llmCalls": 0,
            "embeddingCalls": 0,
            "missingUsage": [],
        }
        for rid, request in requests.items():
            if request["caseId"] != case["id"]:
                continue
            started = datetime.fromisoformat(result["startedAt"])
            requested = datetime.fromisoformat(request["startedAt"])
            if not started <= requested <= started + timedelta(milliseconds=result["elapsedMs"]):
                continue
            selected_requests.add(rid)
            kind = request["kind"]
            row[kind + "Calls"] += 1
            totals[kind + "Calls"] += 1
            if rid not in usage:
                row["missingUsage"].append(rid)
                continue
            event = usage[rid]
            u = event["usage"]
            if kind == "llm":
                assert event["responseModel"] == "deepseek-flash", event["responseModel"]
                prompt = u["prompt_tokens"]
                hit = u["prompt_cache_hit_tokens"]
                miss = u["prompt_cache_miss_tokens"]
                completion = u["completion_tokens"]
                assert hit + miss == prompt
                totals["prompt"] += prompt
                totals["cacheHit"] += hit
                totals["cacheMiss"] += miss
                totals["completion"] += completion
                cost = (hit * 0.02 + miss + completion * 4) / 1e6
            else:
                tokens = u["total_tokens"]
                totals["embedding"] += tokens
                cost = tokens * 0.5 / 1e6
            row["estimatedCny"] += cost
            totals["estimatedCny"] += cost
        events = result["events"]
        row["searchCalls"] = sum(
            e.get("type") == "tool_call"
            and e.get("tool") == "search_knowledge"
            and e.get("status") == "success"
            for e in events
        )
        row["toolFailures"] = [
            {"tool": e.get("tool"), "error": e.get("error")}
            for e in events
            if e.get("type") == "tool_call" and e.get("status") == "failed"
        ]
        answer = result.get("snapshot", {}).get("content", "")
        mappings = result.get("snapshot", {}).get("referenceMappings", {})
        refs = set(re.findall(r"来源\s*#(\d+)", answer))
        row["usedReferences"] = sorted(refs)
        row["referenceCount"] = len(mappings)
        row["citationAccessOk"] = sum(c["status"] == 200 for c in result["citations"])
        row["citationAccessTotal"] = len(result["citations"])
        row["unmappedReferences"] = [ref for ref in refs if ref not in mappings]
        allowed = {
            "deepseek": {"deepseek"},
            "qwen": {"qwen"},
            "gpt": {"gpt"},
            "comparison": {"deepseek", "gpt"},
        }.get(case["vendor"])
        if case["vendor"] == "comparison":
            allowed = {source["file"].split("-")[0] for source in case["sources"]}
        row["foreignReferences"] = [
            v["fileName"] for v in mappings.values() if allowed and v["fileName"].split("-")[0] not in allowed
        ]
        row["handoffCreated"] = any(
            e.get("type") == "tool_call"
            and e.get("tool") == "create_support_handoff"
            and e.get("status") == "success"
            for e in events
        )
        row["declaredNameMismatches"] = [
            {"ref": ref, "declared": name, "mapped": mappings.get(ref, {}).get("fileName")}
            for ref, name in re.findall(r"来源\s*#(\d+)\s*[:：]\s*([a-z][a-z0-9-]+\.md)", answer)
            if name != mappings.get(ref, {}).get("fileName")
        ]
        row["filteredByDiagnosticGate"] = any(e.get("type") == "quality_gate_filtered" for e in events)
        rows.append(row)
        row["review"] = reviews.get(case["id"], {"overall": "UNREVIEWED", "note": "待按冻结要求审阅"})
        transcript += [
            f"## {case['id']} · {case['vendor']} · {case['kind']}",
            "",
            case["question"],
            "",
            "判分要求：" + "；".join(case["requiredClaims"]),
            "",
            "审阅：" + row["review"]["overall"] + "。" + row["review"]["note"],
            "",
            "### 原始回答",
            "",
            answer,
            "",
            "### 实际引用锚点",
            "",
        ]
        for ref in sorted(refs, key=int):
            mapping = mappings.get(ref)
            if not mapping:
                transcript += [f"来源#{ref}：映射缺失", ""]
                continue
            citation = next(
                (
                    c
                    for c in result["citations"]
                    if c["mapping"].get("citationId") == mapping.get("citationId")
                ),
                None,
            )
            data = (citation or {}).get("response", {}).get("data", {})
            transcript += [
                f"来源#{ref}：`{mapping['fileName']}`，chunk={mapping.get('chunkId')}，version={mapping.get('indexVersion')}，HTTP={(citation or {}).get('status')}",
                "",
                "~~~~text",
                data.get("textContent", ""),
                "\n[同版本引用上下文]\n" + data["contextText"] if data.get("contextText") else "",
                "~~~~",
                "",
            ]
    assert not [r for r in requests.values() if r["caseId"] == "unattributed"]
    durations = sorted(r["elapsedMs"] for r in rows)
    totals.update(
        {
            "cases": len(rows),
            "completed": sum(r["status"] == "COMPLETED" for r in rows),
            "requests": len(selected_requests),
            "usageCaptured": len(selected_requests.intersection(usage)),
            "reservedUpperCny": sum(requests[r]["reservedUpperCny"] for r in selected_requests),
            "meanMs": statistics.mean(durations),
            "medianMs": statistics.median(durations),
            "p95NearestRankMs": durations[math.ceil(0.95 * len(durations)) - 1],
            "sumMs": sum(durations),
        }
    )
    totals["reviewCounts"] = {
        grade: sum(row["review"]["overall"] == grade for row in rows) for grade in ("PASS", "PARTIAL", "FAIL", "UNREVIEWED")
    }
    (OUT / "metrics.json").write_text(
        json.dumps({"totals": totals, "cases": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    REPORT.write_text("\n".join(transcript), encoding="utf-8")
    print(json.dumps({"totals": totals, "cases": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=OUT)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--review", type=Path, default=REVIEW)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    OUT = args.checkpoint.resolve()
    DATASET = args.dataset.resolve()
    REVIEW = args.review.resolve()
    REPORT = args.report.resolve()
    main()
