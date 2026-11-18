"""Merge measured reports; missing, failed or skipped acceptance is never green."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/checkpoints/phase4"
sys.path.insert(0, str(ROOT))


def main():
    from app.evaluation.trajectory import score_episode, summarize

    expected = {
        case["id"]: case
        for case in (
            json.loads(line)
            for line in (ROOT / "eval/phase4/diagnosis.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    # Rescore persisted execution artifacts with the same scorer; no model replay.
    for mode in ("preopt", "final", "live"):
        path = OUTPUT / f"diagnosis-{mode}.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for artifact, previous in zip(saved["artifacts"], saved["rows"], strict=True):
            if mode == "live":
                artifact["plannerCalls"] = artifact["providerRequests"]
            row = {
                **score_episode(expected[artifact["id"]]["expected"], artifact),
                "split": expected[artifact["id"]]["split"],
            }
            if previous.get("checks", {}).get("providerAvailableAndMetered") is False:
                row["passed"] = False
            rows.append(row)
        saved["rows"], saved["summary"] = rows, summarize(rows)
        saved["bySplit"] = {
            split: summarize([r for r in rows if r["split"] == split]) for split in {r["split"] for r in rows}
        }
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    retrieval = {
        name: json.loads((OUTPUT / f"retrieval-{name}.json").read_text(encoding="utf-8"))
        for name in ("plain", "baseline", "final")
    }
    episodes = {
        name: json.loads((OUTPUT / f"diagnosis-{name}.json").read_text(encoding="utf-8"))
        for name in ("preopt", "final")
    }
    assert all({row["id"] for row in value["rows"]} == set(expected) for value in episodes.values())
    assert all(value["summary"]["queries"] == 120 for value in retrieval.values())
    assert len({value["datasetSha256"] for value in retrieval.values()}) == 1
    final, before = retrieval["final"]["summary"], retrieval["baseline"]["summary"]
    retrieval_pass = all(
        final[metric] + 1e-9 >= before[metric] for metric in ("hitRate", "recall", "mrr", "ndcg")
    )
    matched = {row["id"]: row for row in episodes["preopt"]["rows"]}
    unchanged_quality = all(
        row["passed"] and matched[row["id"]]["passed"] for row in episodes["final"]["rows"]
    )
    integration = ET.parse(ROOT / "data/checkpoints/phase4-integration.xml").getroot()
    suites = list(integration.iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, 0)) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    before_plans, after_plans = (episodes[name]["summary"]["plannerCalls"] for name in ("preopt", "final"))
    live = json.loads((OUTPUT / "diagnosis-live.json").read_text(encoding="utf-8"))
    cleanup = json.loads((OUTPUT / "index-cleanup-comparison.json").read_text(encoding="utf-8"))
    cleanup_tests = [
        test
        for test in integration.iter("testcase")
        if test.get("name") == "test_gc_interleaved_with_new_publication_keeps_new_version"
    ]
    cleanup_pass = (
        cleanup["reproduced"]
        and len(cleanup_tests) == 1
        and not any(cleanup_tests[0].find(tag) is not None for tag in ("failure", "error", "skipped"))
    )
    first_live = (
        json.loads((OUTPUT / "diagnosis-live-first.json").read_text(encoding="utf-8"))
        if (OUTPUT / "diagnosis-live-first.json").exists()
        else {}
    )
    report = {
        "passed": retrieval_pass
        and cleanup_pass
        and unchanged_quality
        and after_plans < before_plans
        and counts["tests"] > 0
        and not any(counts[k] for k in ("failures", "errors", "skipped"))
        and live["summary"]["pass"],
        "retrieval": {
            name: {key: value[key] for key in ("summary", "byCaseType", "latency", "failures")}
            for name, value in retrieval.items()
        },
        "trajectory": {name: value["summary"] for name, value in episodes.items()},
        "planningReduction": {
            "before": before_plans,
            "after": after_plans,
            "fraction": (before_plans - after_plans) / before_plans,
        },
        "qualityUnchanged": unchanged_quality,
        "retrievalNotRegressed": retrieval_pass,
        "realIntegration": counts,
        "indexCleanupComparison": {**cleanup, "finalInvariantPassed": cleanup_pass},
        "live": {
            key: live[key]
            for key in (
                "summary",
                "providerCalls",
                "tokens",
                "usage",
                "conservativeCostUpperCny",
                "configuredModel",
                "acceptanceModel",
            )
        },
        "liveAllAttempts": {
            "providerCalls": live["providerCalls"] + first_live.get("providerCalls", 0),
            "tokens": live["tokens"] + first_live.get("tokens", 0),
            "conservativeCostUpperCny": live["conservativeCostUpperCny"]
            + first_live.get("conservativeCostUpperCny", 0),
        },
        "limitations": [
            "plain dense-only RAG and phase1 baseline have no durable diagnosis/recheck metrics; N/A",
            "120 retrieval questions are pre-existing regression cases, not a blind holdout",
            "24 diagnosis episodes use synthetic business events; 16 retained cases are not third-party blind testing",
            "offline planners are deterministic substitutes; timing excludes provider latency and is not load performance",
            "live acceptance uses an explicit model override; actual .env remains unchanged",
            "provider cost is conservatively estimated, not a billing receipt",
        ],
    }
    (OUTPUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in {"retrieval", "trajectory"}}, ensure_ascii=False
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
