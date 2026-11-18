from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.customer_service import (
    aggregate_customer_service_results,
    evaluate_customer_service_case,
    validate_customer_service_case,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def apply_cost(artifact: dict[str, Any], input_price_per_million: float, output_price_per_million: float) -> None:
    usage = artifact.setdefault("usage", {})
    if usage.get("costUsd") is not None:
        return
    prompt = int(usage.get("promptTokens") or 0)
    completion = int(usage.get("completionTokens") or 0)
    usage["totalTokens"] = int(usage.get("totalTokens") or prompt + completion)
    usage["costUsd"] = round(
        (prompt / 1_000_000.0) * max(0.0, input_price_per_million)
        + (completion / 1_000_000.0) * max(0.0, output_price_per_million),
        10,
    )


def result_dict(result) -> dict[str, Any]:
    return {
        "id": result.case_id,
        "pass": result.passed,
        "resolutionPass": result.resolution_passed,
        "score": result.score,
        "layers": {
            name: {"score": layer.score, "pass": layer.passed, "metrics": layer.metrics, "details": layer.details}
            for name, layer in result.layers.items()
        },
        "details": result.details,
    }


def static_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details = [validate_customer_service_case(case) for case in cases]
    return {
        "cases": len(details),
        "pass": all(row["pass"] for row in details),
        "passRate": round(sum(1 for row in details if row["pass"]) / len(details), 4) if details else 0.0,
        "details": details,
    }


def evaluate_artifacts(args, cases: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(case.get("id")): case for case in cases}
    rows = []
    details = []
    seen: set[str] = set()
    for artifact in artifacts:
        case_id = str(artifact.get("caseId") or artifact.get("id") or "")
        case = by_id.get(case_id)
        if not case:
            continue
        apply_cost(artifact, args.input_cost_per_million, args.output_cost_per_million)
        result = evaluate_customer_service_case(case, artifact)
        # Keep the artifact only in output details; the aggregate stays compact.
        row = result_dict(result)
        row["artifact"] = artifact
        details.append(row)
        rows.append(result)
        seen.add(case_id)
    return {
        "summary": aggregate_customer_service_results(rows),
        "missingCases": [case.get("id") for case in cases if str(case.get("id")) not in seen],
        "details": details,
    }


def merge_rag_report(report: dict[str, Any], path: str | None) -> None:
    if not path:
        report["rag"] = {"status": "not-run", "hint": "Run scripts/evaluate_rag.py on a real customer-service knowledge dataset and pass --rag-report."}
        return
    rag = json.loads(Path(path).read_text(encoding="utf-8"))
    summary = rag.get("summary") or {}
    report["rag"] = {
        "status": "real-index",
        "k": rag.get("k"),
        "metrics": {
            "hitRate": summary.get("hitRate", 0.0),
            "recall": summary.get("recall", 0.0),
            "mrr": summary.get("mrr", 0.0),
            "ndcg": summary.get("ndcg", 0.0),
        },
        "queries": summary.get("queries", 0),
    }


async def live_report(args, cases: list[dict[str, Any]], with_skill: bool) -> dict[str, Any]:
    from app.agent.llm import llm_service
    from app.core.config import get_settings
    from app.core.langfuse_observability import flush_langfuse, langfuse_span, observation_output
    from app.evaluation.customer_service_live import run_live_customer_service_case

    if not get_settings().llm_api_key:
        return {"skipped": True, "reason": "LLM_API_KEY is not configured."}
    results = []
    details = []
    for case in cases:
        with langfuse_span(
            "customer_service.regression", root=True, kind="evaluator",
            attributes={"langfuse.trace.metadata.case_id": str(case.get("id")), "with_skill": with_skill},
        ) as span:
            artifact = await run_live_customer_service_case(case, llm_service=llm_service, with_skill=with_skill)
            apply_cost(artifact, args.input_cost_per_million, args.output_cost_per_million)
            result = evaluate_customer_service_case(case, artifact)
            observation_output(span, {
                "passed": result.passed,
                "resolutionPassed": result.resolution_passed,
                "score": result.score,
                "layers": {name: layer.passed for name, layer in result.layers.items()},
            })
            if span is not None:
                artifact["langfuseTraceId"] = f"{span.get_span_context().trace_id:032x}"
        results.append(result)
        row = result_dict(result)
        row["artifact"] = artifact
        details.append(row)
    return {
        "summary": aggregate_customer_service_results(results),
        "details": details,
        "langfuseQueueFlushed": await asyncio.to_thread(flush_langfuse) if get_settings().langfuse_enabled else None,
    }


def dataset_profile(cases: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    return {
        "cases": len(cases),
        "categories": dict(sorted(Counter(str(row.get("category") or "unknown") for row in cases).items())),
        "difficulties": dict(sorted(Counter(str(row.get("difficulty") or "unspecified") for row in cases).items())),
        "baseScenarios": len({str(row.get("baseCaseId") or row.get("id")) for row in cases}),
    }


async def main_async(args) -> None:
    dataset = Path(args.dataset)
    cases = load_jsonl(dataset)
    if args.case:
        wanted = set(args.case)
        cases = [row for row in cases if str(row.get("id")) in wanted]
    report: dict[str, Any] = {
        "benchmark": "PaiSmart AI Customer Service Benchmark",
        "dataset": str(dataset),
        "sixLayers": ["rag", "toolCalling", "agentDecision", "answerQuality", "safety", "performance"],
        "datasetProfile": dataset_profile(cases),
        "static": static_report(cases),
    }
    merge_rag_report(report, args.rag_report)

    if args.artifact_jsonl:
        report["artifactEval"] = evaluate_artifacts(args, cases, load_jsonl(Path(args.artifact_jsonl)))
    if args.live:
        report["live"] = await live_report(args, cases, True)
        if args.compare_no_skill:
            report["liveNoSkill"] = await live_report(args, cases, False)
            if not report["live"].get("skipped") and not report["liveNoSkill"].get("skipped"):
                a = float(report["live"]["summary"].get("customerResolutionRate") or 0.0)
                b = float(report["liveNoSkill"]["summary"].get("customerResolutionRate") or 0.0)
                report["skillResolutionLift"] = round(a - b, 4)

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Run PaiSmart's six-layer AI customer-service benchmark.")
    parser.add_argument("--dataset", default="eval/customer_service/benchmark.jsonl", help="Customer-service benchmark JSONL.")
    parser.add_argument("--case", action="append", help="Evaluate only this case id; repeatable.")
    parser.add_argument("--artifact-jsonl", help="Evaluate saved Agent artifacts (answer, toolCalls, skills, timing, usage).")
    parser.add_argument("--rag-report", help="JSON report generated by evaluate_rag.py against the real knowledge index.")
    parser.add_argument("--live", action="store_true", help="Run the real LLM against deterministic customer-service Tool fixtures.")
    parser.add_argument("--compare-no-skill", action="store_true", help="With --live, compare the same cases without Skill guidance.")
    parser.add_argument("--input-cost-per-million", type=float, default=0.0, help="Optional input-token price in USD per 1M tokens.")
    parser.add_argument("--output-cost-per-million", type=float, default=0.0, help="Optional output-token price in USD per 1M tokens.")
    parser.add_argument("--output", help="Optional JSON report path.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
