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

from app.evaluation.skills import (
    aggregate_scores,
    evaluate_behavior_trace,
    evaluate_routing_case,
    load_jsonl,
    run_live_planning_case,
    validate_skill_contract,
)
from app.agent.agent_skill_policy import SHARED_NODE_SKILLS, TARGET_AGENT_SKILLS
from app.agent.routing_policy import routing_policy
from app.skill_runtime.registry import skill_registry
from app.tools.registry import tool_registry


def _skill_rows(skill_name: str, relative: str) -> list[dict[str, Any]]:
    skill = skill_registry.get(skill_name)
    if not skill:
        raise SystemExit(f"Unknown skill: {skill_name}")
    return load_jsonl(skill.root / relative)


def _selected_skills(args) -> list[str]:
    if args.skill:
        names = args.skill
    else:
        names = skill_registry.names()
    unknown = [name for name in names if not skill_registry.get(name)]
    if unknown:
        raise SystemExit(f"Unknown skills: {', '.join(unknown)}")
    return names


def _target_skill_route(question: str) -> list[str]:
    decision = routing_policy.decide(question)
    selected = [SHARED_NODE_SKILLS["generate_customer_response"]]
    selected.extend(TARGET_AGENT_SKILLS[agent] for agent in decision.selected_agents)
    if decision.requires_handoff_after_summary:
        selected.append(SHARED_NODE_SKILLS["handoff_decision"])
    return list(dict.fromkeys(selected))


def run_static(names: list[str]) -> dict[str, Any]:
    contracts = [validate_skill_contract(skill_registry.get(name), tool_registry.names()) for name in names]
    routing_details = []
    routing_scores = []
    for name in names:
        for case in _skill_rows(name, "eval/routing.jsonl"):
            score = evaluate_routing_case(case, _target_skill_route)
            routing_scores.append(score)
            routing_details.append({"skillDataset": name, "pass": score.passed, "score": score.score, **score.details})
    return {
        "contracts": {
            "pass": all(row["pass"] for row in contracts),
            "details": contracts,
        },
        "routing": {
            "summary": aggregate_scores(routing_scores),
            "details": routing_details,
        },
    }


def run_trace_eval(names: list[str], trace_path: Path) -> dict[str, Any]:
    traces = load_jsonl(trace_path)
    by_id = {str(row.get("caseId") or row.get("id") or ""): row.get("trace") or row for row in traces}
    by_question = {str((row.get("trace") or row).get("question") or ""): row.get("trace") or row for row in traces}
    details = []
    scores = []
    missing = []
    for name in names:
        for case in _skill_rows(name, "eval/behavior.jsonl"):
            trace = by_id.get(str(case.get("id") or "")) or by_question.get(str(case.get("question") or ""))
            if not trace:
                missing.append(case.get("id"))
                continue
            score = evaluate_behavior_trace(trace, case)
            scores.append(score)
            details.append({"skillDataset": name, "pass": score.passed, "score": score.score, **score.details})
    return {"summary": aggregate_scores(scores), "missingCases": missing, "details": details}


async def run_live(names: list[str], compare_no_skill: bool) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.agent.llm import llm_service

    settings = get_settings()
    if not settings.llm_api_key:
        return {
            "skipped": True,
            "reason": "LLM_API_KEY is not configured; live Skill behavior eval would be meaningless with fallback mode.",
        }

    skilled_scores = []
    baseline_scores = []
    details = []
    for name in names:
        for case in _skill_rows(name, "eval/behavior.jsonl"):
            skilled_trace = await run_live_planning_case(
                case,
                registry=skill_registry,
                llm_service=llm_service,
                tool_registry=tool_registry,
                with_skill=True,
            )
            skilled = evaluate_behavior_trace(skilled_trace, case)
            skilled_scores.append(skilled)
            row: dict[str, Any] = {
                "id": case.get("id"),
                "skill": name,
                "question": case.get("question"),
                "withSkill": {"score": skilled.score, "pass": skilled.passed, "trace": skilled_trace, "checks": skilled.details.get("checks")},
            }
            if compare_no_skill:
                baseline_trace = await run_live_planning_case(
                    case,
                    registry=skill_registry,
                    llm_service=llm_service,
                    tool_registry=tool_registry,
                    with_skill=False,
                )
                baseline_case = dict(case)
                baseline_expect = dict(case.get("expect") or {})
                baseline_expect["requiredSkills"] = []
                baseline_case["expect"] = baseline_expect
                baseline = evaluate_behavior_trace(baseline_trace, baseline_case)
                baseline_scores.append(baseline)
                row["withoutSkill"] = {
                    "score": baseline.score,
                    "pass": baseline.passed,
                    "trace": baseline_trace,
                    "checks": baseline.details.get("checks"),
                }
                row["skillLift"] = round(skilled.score - baseline.score, 4)
            details.append(row)

    result: dict[str, Any] = {
        "withSkill": aggregate_scores(skilled_scores),
        "details": details,
    }
    if compare_no_skill:
        result["withoutSkill"] = aggregate_scores(baseline_scores)
        if details:
            result["averageSkillLift"] = round(sum(float(row.get("skillLift") or 0) for row in details) / len(details), 4)
    return result


async def main_async(args) -> None:
    names = _selected_skills(args)
    report: dict[str, Any] = {"skills": names, "static": run_static(names)}
    if args.trace_jsonl:
        report["traceEval"] = run_trace_eval(names, Path(args.trace_jsonl))
    if args.live:
        report["liveBehavior"] = await run_live(names, args.compare_no_skill)

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate API Assistant Skills: contract, routing, runtime traces, and optional live LLM planning")
    parser.add_argument("--skill", action="append", help="Skill name to evaluate; repeat to select multiple. Default: all skills.")
    parser.add_argument("--trace-jsonl", help="Optional JSONL exported from skill_trace events. Match by caseId/id or exact question.")
    parser.add_argument("--live", action="store_true", help="Run real LLM orchestration against deterministic fake tool results; requires LLM_API_KEY.")
    parser.add_argument("--compare-no-skill", action="store_true", help="With --live, run each case again without Skill guidance and report score lift.")
    parser.add_argument("--output", help="Optional JSON report path")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
