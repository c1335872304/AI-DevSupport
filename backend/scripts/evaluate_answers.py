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

from app.evaluation.answer import aggregate_answer_results, evaluate_answer
from app.evaluation.answer import run_live_answer_case, run_llm_judge, validate_answer_case
from app.evaluation.skills import load_jsonl
from app.skill_runtime.registry import skill_registry
from app.tools.registry import tool_registry


def _selected_skills(args) -> list[str]:
    names = args.skill or skill_registry.names()
    unknown = [name for name in names if not skill_registry.get(name)]
    if unknown:
        raise SystemExit(f"Unknown skills: {', '.join(unknown)}")
    return names


def _answer_cases(names: list[str], case_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in names:
        skill = skill_registry.get(name)
        if not skill:
            continue
        paths = [relative for relative in skill.evals if relative.endswith("answer.jsonl")]
        for relative in paths:
            for case in load_jsonl(skill.root / relative):
                if case_ids and str(case.get("id") or "") not in case_ids:
                    continue
                rows.append(case)
    return rows


def _result_dict(result) -> dict[str, Any]:
    return {
        "score": result.score,
        "pass": result.passed,
        "deterministicScore": result.deterministic_score,
        "judgeScore": result.judge_score,
        "metrics": result.metrics,
        "details": result.details,
    }


def run_static(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details = [validate_answer_case(case) for case in cases]
    return {
        "cases": len(details),
        "pass": all(row["pass"] for row in details),
        "passRate": round(sum(1 for row in details if row["pass"]) / len(details), 4) if details else 0.0,
        "details": details,
    }


async def _judge_if_requested(args, answer: str, case: dict[str, Any], evidence: list[dict[str, Any]]):
    if not args.llm_judge:
        return None
    from app.core.config import get_settings
    from app.agent.llm import llm_service

    if not get_settings().llm_api_key:
        raise RuntimeError("--llm-judge requires LLM_API_KEY")
    return await run_llm_judge(answer=answer, case=case, evidence=evidence, llm_service=llm_service)


async def run_artifact_eval(args, cases: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    case_by_id = {str(case.get("id")): case for case in cases}
    details = []
    scores = []
    missing_cases = []
    for artifact in load_jsonl(path):
        case_id = str(artifact.get("caseId") or artifact.get("id") or "")
        case = case_by_id.get(case_id)
        if not case:
            continue
        answer = str(artifact.get("answer") or "")
        evidence = list(artifact.get("evidence") or case.get("evidence") or [])
        references = artifact.get("references") if isinstance(artifact.get("references"), dict) else None
        judge = await _judge_if_requested(args, answer, case, evidence)
        result = evaluate_answer(
            answer,
            case,
            evidence=evidence,
            references=references,
            judge=judge,
            judge_weight=args.judge_weight,
        )
        scores.append(result)
        details.append({"id": case_id, "skill": case.get("skill"), "answer": answer, "trace": artifact.get("trace"), **_result_dict(result)})
    evaluated = {row["id"] for row in details}
    for case in cases:
        if str(case.get("id")) not in evaluated:
            missing_cases.append(case.get("id"))
    return {"summary": aggregate_answer_results(scores), "missingCases": missing_cases, "details": details}


async def run_live(args, cases: list[dict[str, Any]]) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.agent.llm import llm_service

    if not get_settings().llm_api_key:
        return {
            "skipped": True,
            "reason": "LLM_API_KEY is not configured; live End-to-End Answer Eval requires a real model.",
        }

    skilled_scores = []
    baseline_scores = []
    details = []
    for case in cases:
        skilled_artifact = await run_live_answer_case(
            case,
            registry=skill_registry,
            llm_service=llm_service,
            tool_registry=tool_registry,
            with_skill=True,
        )
        skilled_judge = await _judge_if_requested(args, skilled_artifact["answer"], case, skilled_artifact["evidence"])
        skilled = evaluate_answer(
            skilled_artifact["answer"],
            case,
            evidence=skilled_artifact["evidence"],
            references=skilled_artifact["references"],
            judge=skilled_judge,
            judge_weight=args.judge_weight,
        )
        skilled_scores.append(skilled)
        row: dict[str, Any] = {
            "id": case.get("id"),
            "skill": case.get("skill"),
            "question": case.get("question"),
            "withSkill": {"answer": skilled_artifact["answer"], "trace": skilled_artifact["trace"], **_result_dict(skilled)},
        }
        if args.compare_no_skill:
            baseline_artifact = await run_live_answer_case(
                case,
                registry=skill_registry,
                llm_service=llm_service,
                tool_registry=tool_registry,
                with_skill=False,
            )
            baseline_judge = await _judge_if_requested(args, baseline_artifact["answer"], case, baseline_artifact["evidence"])
            baseline = evaluate_answer(
                baseline_artifact["answer"],
                case,
                evidence=baseline_artifact["evidence"],
                references=baseline_artifact["references"],
                judge=baseline_judge,
                judge_weight=args.judge_weight,
            )
            baseline_scores.append(baseline)
            row["withoutSkill"] = {"answer": baseline_artifact["answer"], "trace": baseline_artifact["trace"], **_result_dict(baseline)}
            row["skillLift"] = round(skilled.score - baseline.score, 4)
        details.append(row)

    report: dict[str, Any] = {"withSkill": aggregate_answer_results(skilled_scores), "details": details}
    if args.compare_no_skill:
        report["withoutSkill"] = aggregate_answer_results(baseline_scores)
        report["averageSkillLift"] = round(sum(float(row.get("skillLift") or 0.0) for row in details) / len(details), 4) if details else 0.0
    return report


async def main_async(args) -> None:
    names = _selected_skills(args)
    case_ids = set(args.case or []) or None
    cases = _answer_cases(names, case_ids)
    report: dict[str, Any] = {
        "skills": names,
        "caseFilter": sorted(case_ids) if case_ids else None,
        "static": run_static(cases),
    }
    if args.artifact_jsonl:
        report["artifactEval"] = await run_artifact_eval(args, cases, Path(args.artifact_jsonl))
    if args.live:
        report["liveEndToEnd"] = await run_live(args, cases)

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate API Assistant final answers: deterministic grounding/citations/completeness plus optional LLM judge and Skill A/B."
    )
    parser.add_argument("--skill", action="append", help="Skill to evaluate; repeat to select multiple. Default: all skills.")
    parser.add_argument("--case", action="append", help="Evaluate only this case id; repeat to select multiple.")
    parser.add_argument("--artifact-jsonl", help="Evaluate saved run artifacts containing caseId, answer, references/evidence, and optional trace.")
    parser.add_argument("--live", action="store_true", help="Run real LLM + deterministic fixture tools end-to-end; requires LLM_API_KEY.")
    parser.add_argument("--compare-no-skill", action="store_true", help="With --live, run the same cases again without Skill guidance and report final-answer lift.")
    parser.add_argument("--llm-judge", action="store_true", help="Add an optional semantic LLM judge. Deterministic metrics remain the majority score.")
    parser.add_argument("--judge-weight", type=float, default=0.40, help="LLM judge weight in combined score, clamped to 0..0.5. Default: 0.40.")
    parser.add_argument("--output", help="Optional JSON report path.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
