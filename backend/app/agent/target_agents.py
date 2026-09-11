from __future__ import annotations

"""Bounded specialist components for the target Agent architecture.

Each selected specialist independently plans only its own allowlisted Tool
calls. The shared scheduler is the only component allowed to execute them.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import uuid4

from app.agent.agent_skill_policy import _SkillRegistry
from app.agent.llm import llm_service
from app.agent.types import AgentEvidence, AgentPlan, AgentToolCall, tool_call_fingerprint


def _call_matches_attempted_fingerprint(call: AgentToolCall, attempted: set[str]) -> bool:
    """Match exact calls and legacy knowledge-search fingerprints.

    Older persisted traces may omit the default ``top_k=6`` argument. Treat
    that representation as equivalent to the current default so a fallback
    planner cannot re-issue an already executed read.
    """
    fingerprint = tool_call_fingerprint(call)
    if fingerprint in attempted:
        return True
    if call.name != "search_knowledge":
        return False

    arguments = dict(call.arguments)
    if arguments.get("top_k", 6) == 6:
        arguments.pop("top_k", None)
        legacy = AgentToolCall(
            id=call.id,
            name=call.name,
            arguments=arguments,
            source_agent=call.source_agent,
            source_skill=call.source_skill,
        )
        if tool_call_fingerprint(legacy) in attempted:
            return True
    if "top_k" not in call.arguments:
        arguments["top_k"] = 6
        defaulted = AgentToolCall(
            id=call.id,
            name=call.name,
            arguments=arguments,
            source_agent=call.source_agent,
            source_skill=call.source_skill,
        )
        return tool_call_fingerprint(defaulted) in attempted
    return False


@dataclass(frozen=True, slots=True)
class TargetAgentWork:
    """A specialist's bounded plan and its first dependency-safe proposals."""

    plan: AgentPlan
    proposed_calls: tuple[AgentToolCall, ...] = ()
    planning_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.plan.to_dict(),
            "proposedCalls": [
                {
                    "id": call.id,
                    "name": call.name,
                    "arguments": dict(call.arguments),
                    "sourceAgent": call.source_agent,
                    "sourceSkill": call.source_skill,
                }
                for call in self.proposed_calls
            ],
            "planningError": self.planning_error,
        }


class TargetSpecialistAgent:
    """Base class for a target specialist that never performs side effects."""

    name: str

    def initial_calls(self, plan: AgentPlan, question: str, entities: dict[str, str]) -> tuple[AgentToolCall, ...]:
        raise NotImplementedError

    def follow_up_calls(
        self,
        plan: AgentPlan,
        outcomes: Iterable[tuple[AgentToolCall, Any]],
        attempted_tools: set[str],
    ) -> tuple[AgentToolCall, ...]:
        """Propose a later Tool batch from verified, allowlisted result fields."""
        return ()

    def _call(self, plan: AgentPlan, name: str, arguments: dict[str, Any]) -> AgentToolCall:
        if name not in plan.allowed_tools:
            raise PermissionError(f"Target Agent {self.name} cannot request Tool {name}")
        return AgentToolCall(
            id=f"target_{self.name}_{uuid4().hex}",
            name=name,
            arguments=dict(arguments),
            source_agent=self.name,
            source_skill=plan.skill,
        )

    def evidence_from_results(self, calls_and_results: Iterable[tuple[AgentToolCall, Any]]) -> AgentEvidence:
        """Keep only execution status here; domain fact extraction comes later.

        This prevents the first migration pass from copying arbitrary remote Tool
        payloads into customer-visible model context. The evidence-join stage
        will add per-Tool fact extractors with explicit schemas.
        """
        attempted: list[str] = []
        verified_facts: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for call, result in calls_and_results:
            if call.source_agent != self.name:
                continue
            attempted.append(call.name)
            status = str(getattr(result, "status", "ERROR") or "ERROR").upper()
            if status == "SUCCESS":
                verified_facts.append({"source": call.name, "verified": True})
            else:
                failures.append({"tool": call.name, "status": status})
        status = "completed" if not failures else ("failed" if not verified_facts else "partial")
        return AgentEvidence(
            agent=self.name,
            status=status,
            verified_facts=tuple(verified_facts),
            attempted_tools=tuple(dict.fromkeys(attempted)),
            recommended_handoff=bool(failures),
            tool_failures=tuple(failures),
        )


class ApiDiagnosticTargetAgent(TargetSpecialistAgent):
    name = "api_diagnostic"

    def initial_calls(self, plan: AgentPlan, question: str, entities: dict[str, str]) -> tuple[AgentToolCall, ...]:
        calls: list[AgentToolCall] = []
        if entities.get("request_id"):
            # Downstream API Key/error-code queries wait for this result unless
            # the entity was already provided by the customer.
            calls.append(self._call(plan, "query_call_log", {"request_id": entities["request_id"]}))
        elif entities.get("error_code"):
            calls.append(self._call(plan, "query_error_code", {"code": entities["error_code"]}))
        elif entities.get("app_id") or entities.get("api_key_id"):
            arguments = {key: value for key, value in entities.items() if key in {"app_id", "api_key_id"}}
            calls.append(self._call(plan, "query_api_key_status", arguments))
        elif entities.get("endpoint") and entities.get("http_status") == "429":
            calls.append(self._call(plan, "query_recent_call_stats", {"endpoint": entities["endpoint"], "minutes": 60}))
        return tuple(calls)

    def follow_up_calls(
        self,
        plan: AgentPlan,
        outcomes: Iterable[tuple[AgentToolCall, Any]],
        attempted_tools: set[str],
    ) -> tuple[AgentToolCall, ...]:
        calls: list[AgentToolCall] = []
        for call, result in outcomes:
            if call.source_agent != self.name or call.name != "query_call_log":
                continue
            if str(getattr(result, "status", "")).upper() != "SUCCESS":
                continue
            data = getattr(result, "data", None)
            if not isinstance(data, dict) or not data.get("found"):
                continue
            app_id = str(data.get("appId") or "").strip()
            error_code = str(data.get("errorCode") or "").strip()
            endpoint = str(data.get("endpoint") or "").strip()
            http_status = data.get("httpStatus")
            if app_id and "query_api_key_status" not in attempted_tools:
                calls.append(self._call(plan, "query_api_key_status", {"app_id": app_id}))
            if error_code and "query_error_code" not in attempted_tools:
                calls.append(self._call(plan, "query_error_code", {"code": error_code}))
            if endpoint and http_status == 429 and "query_recent_call_stats" not in attempted_tools:
                calls.append(self._call(plan, "query_recent_call_stats", {"endpoint": endpoint, "minutes": 60}))
        return tuple(calls)


class BillingTargetAgent(TargetSpecialistAgent):
    name = "billing"

    def initial_calls(self, plan: AgentPlan, question: str, entities: dict[str, str]) -> tuple[AgentToolCall, ...]:
        lower = question.lower()
        month = entities.get("month")
        calls: list[AgentToolCall] = []
        if any(token in lower for token in ("套餐", "配额", "qps", "余额")):
            calls.append(self._call(plan, "query_plan", {}))
        if any(token in lower for token in ("用量", "调用量", "超额")):
            calls.append(self._call(plan, "query_usage", {"month": month} if month else {}))
        if entities.get("invoice_id") or any(token in lower for token in ("账单", "费用", "扣费", "发票", "invoice", "退款", "退费")):
            calls.append(self._call(plan, "query_bill", {"month": month} if month else {}))
        # A high-risk Billing request must still collect at least a permitted
        # read-only fact before the later summary and handoff decision.
        if not calls:
            calls.append(self._call(plan, "query_plan", {}))
        return tuple(calls)


class KnowledgeTargetAgent(TargetSpecialistAgent):
    name = "knowledge"

    def initial_calls(self, plan: AgentPlan, question: str, entities: dict[str, str]) -> tuple[AgentToolCall, ...]:
        return (self._call(plan, "search_knowledge", {"query": question, "top_k": 6}),)

    def follow_up_calls(
        self,
        plan: AgentPlan,
        outcomes: Iterable[tuple[AgentToolCall, Any]],
        attempted_tools: set[str],
    ) -> tuple[AgentToolCall, ...]:
        if "get_document" in attempted_tools:
            return ()
        for call, result in outcomes:
            if call.source_agent != self.name or call.name != "search_knowledge":
                continue
            if str(getattr(result, "status", "")).upper() != "SUCCESS":
                continue
            data = getattr(result, "data", None)
            results = data.get("results") if isinstance(data, dict) else None
            if not isinstance(results, list):
                continue
            for item in results:
                if not isinstance(item, dict):
                    continue
                file_md5 = str(item.get("fileMd5") or "").strip().lower()
                if len(file_md5) != 32:
                    continue
                arguments: dict[str, Any] = {"file_md5": file_md5, "max_chars": 5000}
                if isinstance(item.get("chunkId"), int):
                    arguments["chunk_id"] = item["chunkId"]
                return (self._call(plan, "get_document", arguments),)
        return ()


class TargetSpecialistAgents:
    """Plan bounded specialist work; never execute Tools or answer customers."""

    def __init__(self) -> None:
        self._agents: dict[str, TargetSpecialistAgent] = {
            "api_diagnostic": ApiDiagnosticTargetAgent(),
            "billing": BillingTargetAgent(),
            "knowledge": KnowledgeTargetAgent(),
        }

    @staticmethod
    def _api_call_has_diagnostic_anchor(
        name: str,
        arguments: dict[str, Any],
        entities: dict[str, str],
        outcomes: Iterable[tuple[AgentToolCall, Any]],
    ) -> bool:
        """Accept API diagnostic parameters only when the customer or a prior log supplied them.

        Tool schemas establish shape, not provenance.  In particular, an LLM
        must not turn the word “限流” into an invented error code lookup.
        """
        derived: dict[str, str] = {}
        for call, result in outcomes:
            if call.name != "query_call_log" or str(getattr(result, "status", "")).upper() != "SUCCESS":
                continue
            data = getattr(result, "data", None)
            if not isinstance(data, dict) or not data.get("found"):
                continue
            for key, result_key in (("request_id", "requestId"), ("error_code", "errorCode"), ("endpoint", "endpoint"), ("app_id", "appId")):
                value = str(data.get(result_key) or "").strip()
                if value:
                    derived[key] = value

        allowed = {**entities, **derived}
        expected = {
            "query_call_log": ("request_id", "request_id"),
            "query_error_code": ("error_code", "code"),
            "query_recent_call_stats": ("endpoint", "endpoint"),
        }.get(name)
        if expected is None:
            return True
        entity_key, argument_key = expected
        expected_value = str(allowed.get(entity_key) or "").strip()
        return bool(expected_value and str(arguments.get(argument_key) or "").strip() == expected_value)

    @staticmethod
    def _safe_context(value: Any, limit: int = 6000) -> str:
        encoded = json.dumps(value, ensure_ascii=False, default=str)
        return encoded[:limit]

    async def _plan_one(
        self,
        *,
        plan: AgentPlan,
        question: str,
        retrieval_query: str | None,
        entities: dict[str, str],
        registry: _SkillRegistry,
        tool_registry: Any,
        prior_evidence: list[dict[str, Any]],
        references: list[dict[str, Any]],
        attempted_tools: set[str],
        attempted_call_fingerprints: set[str],
        fallback_outcomes: list[tuple[AgentToolCall, Any]],
    ) -> TargetAgentWork:
        """Ask one domain LLM Agent for Tool calls within its fixed boundary."""
        skill = registry.get(plan.skill)
        skill_prompt = ""
        if skill and hasattr(skill, "prompt_block"):
            skill_prompt = str(skill.prompt_block(8000))
        elif skill:
            skill_prompt = (
                f"Skill: {plan.skill}\n"
                f"允许工具: {', '.join(getattr(skill, 'allowed_tools', ()))}"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是 {plan.agent} 专业 Agent，只负责为共享 Tool Runtime 规划本领域的只读工具调用。\n"
                    "RoutingPolicy 已固定选择你；不得改路由、不得转人工、不得给客户最终答复、不得调用未提供的工具。\n"
                    "仅在能从当前问题、实体或已验证证据中确定参数时调用工具；不要猜测参数。\n"
                    "已执行过相同工具和相同参数的调用不会再次执行；不同参数仅在确有新证据需要时才可调用。"
                    "若无需新的工具调用，直接结束且不要生成客户答复。\n"
                    f"你的目标：{plan.objective}\n"
                    f"你的 Skill、Reference、Script 约束：\n{skill_prompt}\n"
                    "本轮路由器已完成预处理："
                    + self._safe_context(
                        {
                            "question": question,
                            "retrievalQuery": retrieval_query if plan.agent == "knowledge" else "",
                            "entities": entities,
                            "attemptedTools": sorted(attempted_tools),
                            "yourVerifiedEvidence": prior_evidence,
                            "citations": references,
                        }
                    )
                ),
            },
            {"role": "user", "content": question},
        ]
        allowed_tools = tool_registry.llm_tools(plan.allowed_tools)
        proposed: list[AgentToolCall] = []
        try:
            async for event in llm_service.stream_agent_turn(messages, allowed_tools):
                if event.get("type") != "tool_calls":
                    continue
                for raw_call in event.get("tool_calls") or []:
                    name = str(getattr(raw_call, "name", "") or "").strip()
                    arguments = getattr(raw_call, "arguments", {})
                    if name not in plan.allowed_tools or not isinstance(arguments, dict):
                        continue
                    if plan.agent == "api_diagnostic" and not self._api_call_has_diagnostic_anchor(
                        name, arguments, entities, fallback_outcomes,
                    ):
                        continue
                    # The graph may have paid for one bounded rewrite.  Only
                    # knowledge search receives it; customer-facing question
                    # semantics and all non-RAG Tool parameters stay original.
                    if name == "search_knowledge" and retrieval_query:
                        arguments = {**arguments, "query": retrieval_query}
                    call = AgentToolCall(
                        id=f"target_{plan.agent}_{getattr(raw_call, 'id', '') or uuid4().hex}",
                        name=name,
                        arguments=dict(arguments),
                        source_agent=plan.agent,
                        source_skill=plan.skill,
                    )
                    if not _call_matches_attempted_fingerprint(call, attempted_call_fingerprints):
                        proposed.append(call)
        except Exception:
            # The target graph stays available without a configured provider. In
            # that explicit degraded mode only, retain the bounded deterministic
            # planner; online LLM Agents never silently fall back over a valid
            # "no Tool needed" decision.
            if llm_service.settings.llm_api_key:
                raise

        if not proposed and not llm_service.settings.llm_api_key and not any(
            name.startswith("mcp__billing__") for name in plan.allowed_tools
        ):
            agent = self._agents[plan.agent]
            if fallback_outcomes:
                proposed.extend(
                    call
                    for call in agent.follow_up_calls(plan, fallback_outcomes, attempted_tools)
                    if not _call_matches_attempted_fingerprint(call, attempted_call_fingerprints)
                )
            elif not attempted_tools:
                tool_question = retrieval_query if plan.agent == "knowledge" and retrieval_query else question
                proposed.extend(
                    call
                    for call in agent.initial_calls(plan, tool_question, entities)
                    if not _call_matches_attempted_fingerprint(call, attempted_call_fingerprints)
                )

        unique: list[AgentToolCall] = []
        seen: set[str] = set()
        for call in proposed:
            key = tool_call_fingerprint(call)
            if key not in seen:
                seen.add(key)
                unique.append(call)
        return TargetAgentWork(plan=plan, proposed_calls=tuple(unique))

    async def plan_work(
        self,
        *,
        plans: Iterable[AgentPlan],
        question: str,
        entities: dict[str, str],
        retrieval_query: str | None = None,
        registry: _SkillRegistry,
        tool_registry: Any,
        agent_evidence: Iterable[dict[str, Any]] = (),
        references: Iterable[dict[str, Any]] = (),
        fallback_outcomes: Iterable[tuple[AgentToolCall, Any]] = (),
        attempted_call_fingerprints: Iterable[str] = (),
        max_agents: int = 3,
    ) -> list[TargetAgentWork]:
        """Run up to three selected LLM planning Agents concurrently."""
        selected = list(plans)[: max(1, max_agents)]
        evidence_rows = [dict(item) for item in agent_evidence if isinstance(item, dict)]
        reference_rows = [dict(item) for item in references if isinstance(item, dict)]
        outcome_rows = list(fallback_outcomes)
        executed_fingerprints = set(attempted_call_fingerprints)

        async def plan_for(plan: AgentPlan) -> TargetAgentWork:
            if not plan.allowed_tools:
                return TargetAgentWork(plan=plan)
            own_evidence = [item for item in evidence_rows if item.get("agent") == plan.agent]
            own_outcomes = [item for item in outcome_rows if item[0].source_agent == plan.agent]
            # Repetition is prevented within one specialist. Another selected
            # specialist may legally use the same read Tool and retains its own
            # independent execution result.
            own_attempted = {call.name for call, _result in own_outcomes}
            try:
                return await self._plan_one(
                    plan=plan,
                    question=question,
                    retrieval_query=retrieval_query,
                    entities=entities,
                    registry=registry,
                    tool_registry=tool_registry,
                    prior_evidence=own_evidence,
                    references=reference_rows,
                    attempted_tools=own_attempted,
                    attempted_call_fingerprints=executed_fingerprints,
                    fallback_outcomes=own_outcomes,
                )
            except Exception as exc:
                # One specialist planning outage must not discard verified work
                # from the other concurrently selected domains.
                return TargetAgentWork(plan=plan, planning_error=type(exc).__name__)

        return list(await asyncio.gather(*(plan_for(plan) for plan in selected)))

    def get(self, name: str) -> TargetSpecialistAgent | None:
        return self._agents.get(name)

target_specialist_agents = TargetSpecialistAgents()
