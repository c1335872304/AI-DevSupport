from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any, Iterable

from app.agent.types import AgentToolCall
from app.skill_runtime.models import SkillDefinition
from app.skill_runtime.registry import SkillRegistry
from app.skill_runtime.trace import SkillTrace
from app.tools.base import ToolResult


@dataclass(frozen=True, slots=True)
class EvalScore:
    score: float
    passed: bool
    details: dict[str, Any]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"JSONL row must be an object: {path}:{line_no}")
        rows.append(item)
    return rows


def validate_skill_contract(skill: SkillDefinition, known_tools: Iterable[str]) -> dict[str, Any]:
    known = set(known_tools)
    missing_tools = [name for name in skill.allowed_tools if name not in known]
    missing_references = [name for name in skill.references if not (skill.root / name).is_file()]
    missing_scripts = [name for name in skill.scripts if not (skill.root / "scripts" / f"{name}.py").is_file()]
    missing_evals = [name for name in skill.evals if not (skill.root / name).is_file()]
    invalid_quality_gate = []
    if skill.quality_gate and skill.quality_gate not in skill.scripts:
        invalid_quality_gate.append(skill.quality_gate)
    missing_sections = [
        heading
        for heading in ("## 目标", "## 工作流", "## 输出契约")
        if heading not in skill.instructions
    ]
    errors = {
        "missingTools": missing_tools,
        "missingReferences": missing_references,
        "missingScripts": missing_scripts,
        "missingEvals": missing_evals,
        "invalidQualityGate": invalid_quality_gate,
        "missingSections": missing_sections,
    }
    passed = not any(errors.values())
    return {"skill": skill.name, "pass": passed, **errors}


def evaluate_routing_case(case: dict[str, Any], route: Callable[[str], list[str]]) -> EvalScore:
    question = str(case.get("question") or "")
    selected = route(question)
    expected = [str(x) for x in case.get("expectedSkills") or []]
    forbidden = [str(x) for x in case.get("forbiddenSkills") or []]
    expected_hits = sum(1 for name in expected if name in selected)
    expected_ratio = expected_hits / len(expected) if expected else 1.0
    forbidden_hits = [name for name in forbidden if name in selected]
    score = max(0.0, expected_ratio - (0.5 * len(forbidden_hits)))
    passed = expected_ratio == 1.0 and not forbidden_hits
    return EvalScore(
        score=round(score, 4),
        passed=passed,
        details={
            "id": case.get("id"),
            "question": question,
            "selectedSkills": selected,
            "expectedSkills": expected,
            "forbiddenSkills": forbidden,
            "forbiddenHits": forbidden_hits,
        },
    )


def _flatten_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for batch in trace.get("toolBatches") or []:
        for item in batch.get("calls") or []:
            if isinstance(item, dict):
                rows.append(item)
    return rows


def evaluate_behavior_trace(trace: dict[str, Any], case: dict[str, Any]) -> EvalScore:
    expect = case.get("expect") or {}
    flattened = _flatten_trace(trace)
    tools = [str(item.get("tool") or "") for item in flattened]
    scripts = [str(item.get("script") or "") for item in flattened if item.get("script")]
    references = [str(item.get("reference") or "") for item in flattened if item.get("reference")]
    active_skills = [str(x) for x in trace.get("activeSkills") or []]

    required_skills = [str(x) for x in expect.get("requiredSkills") or [case.get("skill")] if x]
    required_tools = [str(x) for x in expect.get("requiredTools") or []]
    forbidden_tools = [str(x) for x in expect.get("forbiddenTools") or []]
    required_scripts = [str(x) for x in expect.get("requiredScripts") or []]
    required_refs = [str(x) for x in expect.get("requiredReferences") or []]
    min_parallel = max(0, int(expect.get("minParallelWidth") or 0))
    max_steps = int(expect.get("maxSteps") or 999)
    max_failures = int(expect.get("maxFailedToolCalls") or 999)

    checks: dict[str, Any] = {}
    weights: list[tuple[str, float, bool]] = []

    skill_ok = all(name in active_skills for name in required_skills)
    checks["requiredSkills"] = {"pass": skill_ok, "required": required_skills, "actual": active_skills}
    weights.append(("requiredSkills", 0.20, skill_ok))

    tool_ratio = sum(1 for name in required_tools if name in tools) / len(required_tools) if required_tools else 1.0
    checks["requiredTools"] = {"ratio": round(tool_ratio, 4), "required": required_tools, "actual": tools}

    script_ratio = sum(1 for name in required_scripts if name in scripts) / len(required_scripts) if required_scripts else 1.0
    checks["requiredScripts"] = {"ratio": round(script_ratio, 4), "required": required_scripts, "actual": scripts}

    ref_ratio = sum(1 for name in required_refs if name in references) / len(required_refs) if required_refs else 1.0
    checks["requiredReferences"] = {"ratio": round(ref_ratio, 4), "required": required_refs, "actual": references}

    forbidden_hits = [name for name in forbidden_tools if name in tools]
    forbidden_ok = not forbidden_hits
    checks["forbiddenTools"] = {"pass": forbidden_ok, "hits": forbidden_hits}

    actual_parallel = int(trace.get("maxParallelWidth") or 0)
    parallel_ok = actual_parallel >= min_parallel
    checks["parallelism"] = {"pass": parallel_ok, "required": min_parallel, "actual": actual_parallel}

    steps = int(trace.get("stepsUsed") or len(trace.get("toolBatches") or []))
    steps_ok = steps <= max_steps
    checks["steps"] = {"pass": steps_ok, "max": max_steps, "actual": steps}

    failures = int(trace.get("failedToolCalls") or 0)
    failures_ok = failures <= max_failures
    checks["failures"] = {"pass": failures_ok, "max": max_failures, "actual": failures}

    weighted = (
        0.20 * (1.0 if skill_ok else 0.0)
        + 0.25 * tool_ratio
        + 0.20 * script_ratio
        + 0.10 * ref_ratio
        + 0.10 * (1.0 if forbidden_ok else 0.0)
        + 0.10 * (1.0 if parallel_ok else 0.0)
        + 0.025 * (1.0 if steps_ok else 0.0)
        + 0.025 * (1.0 if failures_ok else 0.0)
    )
    pass_threshold = float(expect.get("passScore") or 0.8)
    passed = weighted >= pass_threshold and forbidden_ok and failures_ok
    return EvalScore(
        score=round(weighted, 4),
        passed=passed,
        details={
            "id": case.get("id"),
            "question": case.get("question"),
            "checks": checks,
            "passScore": pass_threshold,
        },
    )


def aggregate_scores(rows: list[EvalScore]) -> dict[str, Any]:
    if not rows:
        return {"cases": 0, "passRate": 0.0, "averageScore": 0.0}
    return {
        "cases": len(rows),
        "passRate": round(sum(1 for row in rows if row.passed) / len(rows), 4),
        "averageScore": round(sum(row.score for row in rows) / len(rows), 4),
    }


def behavior_case_fixture(case: dict[str, Any], call: AgentToolCall) -> dict[str, Any]:
    fixtures = case.get("fixtures") or {}
    if call.name == "run_skill_script":
        script = str(call.arguments.get("script") or "")
        script_fixtures = fixtures.get("scripts") or {}
        if script in script_fixtures:
            return script_fixtures[script]
        if script == "normalize_queries":
            return {"queries": [str(case.get("question") or "")], "strategy": "single", "count": 1}
        if script.startswith("audit_"):
            return {"pass": True, "warnings": []}
        return {"ok": True}
    if call.name == "read_skill_reference":
        return {"content": "eval fixture reference loaded"}
    if call.name == "list_documents":
        return fixtures.get("list_documents") or {"documents": [{"fileMd5": "eval-doc", "fileName": "eval-document.pdf"}]}
    if call.name == "get_document":
        return fixtures.get("get_document") or {
            "fileMd5": "eval-doc",
            "fileName": "eval-document.pdf",
            "pageNumber": 1,
            "chunkId": 1,
            "textContent": "Evaluation fixture document with goals, methods, evidence, limitations, and conclusion.",
        }
    if call.name == "search_knowledge":
        return fixtures.get("search_knowledge") or {
            "results": [
                {"fileMd5": "eval-a", "fileName": "source-a.pdf", "pageNumber": 1, "chunkId": 1, "score": 0.92, "textContent": "Direct evidence A."},
                {"fileMd5": "eval-b", "fileName": "source-b.pdf", "pageNumber": 2, "chunkId": 2, "score": 0.88, "textContent": "Independent supporting evidence B."},
            ]
        }
    if call.name == "create_support_handoff":
        return {"handoffId": "CS_eval_123", "status": "OPEN", "priority": call.arguments.get("priority", "NORMAL")}
    if call.name == "get_support_handoff":
        return {"found": True, "handoff": {"handoffId": "CS_eval_123", "status": "OPEN", "priority": "NORMAL"}}
    if call.name == "activate_skill":
        return {"skill": call.arguments.get("skill")}
    return {"ok": True}


async def run_live_planning_case(
    case: dict[str, Any],
    *,
    registry: SkillRegistry,
    llm_service: Any,
    tool_registry: Any,
    with_skill: bool,
) -> dict[str, Any]:
    """Evaluate real model planning without touching PaiSmart DB or private data.

    Knowledge/file tools receive deterministic fixtures. Skill scripts/references are
    represented by fixtures too because this evaluator measures model orchestration,
    while script correctness is covered independently by unit/contract tests.
    """
    skill_name = str(case.get("skill") or "")
    active: list[str] = []
    if with_skill:
        active.extend(skill.name for skill in registry.definitions() if bool(skill.metadata.get("default_active", False)))
        if registry.get(skill_name) and skill_name not in active:
            active.append(skill_name)
    trace = SkillTrace(question=str(case.get("question") or ""), initial_skills=list(active), active_skills=list(active))
    skill_context = registry.build_prompt(active) if active else ""
    messages = llm_service.build_agent_messages(
        str(case.get("question") or ""),
        [],
        skill_catalog=registry.catalog_prompt() if with_skill else "",
        skill_context=skill_context,
    )
    if with_skill and active:
        allowed = {"activate_skill"}
        for active_name in active:
            skill = registry.get(active_name)
            if skill:
                allowed.update(skill.allowed_tools)
        tools = tool_registry.llm_tools(allowed)
    else:
        # True baseline: core capabilities only, no Skill activation/reference/script.
        tools = tool_registry.llm_tools({"search_knowledge", "list_documents", "get_document"})

    max_steps = max(1, min(8, int(case.get("liveMaxSteps") or 5)))
    for step in range(max_steps):
        calls: list[AgentToolCall] = []
        saw_content = False
        async for event in llm_service.stream_agent_turn(messages, tools):
            if event.get("type") == "content" and str(event.get("content") or "").strip():
                saw_content = True
            elif event.get("type") == "tool_calls":
                calls = event.get("tool_calls") or []
        if saw_content and not calls:
            break
        if not calls:
            break
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)}}
                for call in calls
            ],
        })
        results = [ToolResult(status="SUCCESS", data=behavior_case_fixture(case, call), duration_ms=1) for call in calls]
        trace.record_batch(step, calls, results)
        for call, result in zip(calls, results, strict=True):
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": json.dumps(result.as_payload(), ensure_ascii=False),
            })
    return trace.summary()
