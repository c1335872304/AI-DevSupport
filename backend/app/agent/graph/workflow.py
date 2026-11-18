from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextlib import aclosing
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.agent.action_contracts import handoff_receipt, render_action_answer
from app.agent.agent_skill_policy import build_target_agent_plans
from app.agent.complexity import simple_document_question, usable_document_read
from app.agent.diagnostic_window import diagnostic_window, render_window_result
from app.agent.document_context import filter_document_absence_claims, pack_document_context, relabel_evidence
from app.agent.entities import looks_like_follow_up, resolve_entities
from app.agent.evidence import (
    evidence_composer,
    evidence_joiner,
    render_document_excerpts,
    routing_decision_from_dict,
)
from app.agent.graph.answer_content import (
    build_answer_messages,
    ensure_reference_citations,
    retrieval_unavailable_answer,
)
from app.agent.graph.answer_safety import audit_answer, handoff_required
from app.agent.graph.engine import END, LANGGRAPH_ENGINE, START, StateGraph
from app.agent.graph.state import CustomerServiceState
from app.agent.llm import llm_service
from app.agent.memory import conversation_memory
from app.agent.query_optimizer import query_optimizer
from app.agent.question_scope import vendor_clarification
from app.agent.route_cache import route_cache
from app.agent.routing_policy import routing_policy
from app.agent.shared_scheduler import shared_tool_scheduler
from app.agent.streaming import StreamUnitBuffer, without_citation_footer
from app.agent.target_agents import TargetAgentWork, target_specialist_agents
from app.agent.types import AgentEvidence, AgentPlan, AgentToolCall, HandoffResult, tool_call_fingerprint
from app.core.langfuse_observability import langfuse_span, observation_output
from app.core.redaction import redact_text
from app.knowledge.product_scope import named_products
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.trace import SkillTrace
from app.support.handoff_contract import HANDOFF_CREATE, authorize_handoff
from app.tools.mcp.billing import billing_mcp_adapter

if TYPE_CHECKING:
    from app.agent.runtime import AgentRuntime, ChunkCallback, SendJson
    from app.db.models import User
    from app.tools.base import ToolResult


logger = logging.getLogger(__name__)


def _gid(generation_id: str | None) -> str:
    return (generation_id or "-")[:8]


def _console(message: str) -> None:
    print(message, flush=True)


_CORRECTED_FAILURE = re.compile(
    r"(?:说错|更正|纠正)[^。！？；]{0,16}[，,:：]\s*(?:应该)?是\s*[^，,。！？；]{1,48}?(?:失败|报错|出错|异常)"
)
_FAILURE_DURING_OPERATION = re.compile(
    r"(?:^|[，,。！？；])\s*[^，,。！？；]{1,36}?(?:时|的时候)"
    r"(?:总是?|经常|一直|反复|就|会|才)*(?:失败|报错|出错|异常)"
)


def _diagnostic_clarification(
    classification: dict, entities: dict[str, str], *, diagnostic: bool, question: str = "",
) -> str:
    """Resolve the next missing diagnostic fact before specialist execution."""
    scope = classification.get("diagnostic_scope")
    if entities.get("request_id"):
        return ""
    if diagnostic and scope == "unspecified" and (
        _CORRECTED_FAILURE.search(question) or _FAILURE_DURING_OPERATION.search(question)
    ):
        scope = "incident"
    if scope == "unspecified" and not entities.get("endpoint"):
        return "具体是哪项操作或哪个接口失败？"
    if diagnostic and scope == "incident":
        if entities.get("http_status") or entities.get("error_code"):
            return "能提供一条失败请求的 request_id 吗？有了这条记录，才能核对实际触发原因。"
        return "失败时看到什么报错？如果手头有一条失败请求的 request_id，也可以直接发给我。"
    intent = str(classification.get("intent") or "").strip().lower()
    diagnostic_intents = {"api_diagnostic", "authentication_error", "network_error", "upload_error"}
    anchors = {"request_id", "error_code", "http_status", "endpoint"}
    if diagnostic and intent in diagnostic_intents and not anchors.intersection(entities):
        return "为了准确定位，请补充 request_id、接口路径，或返回的错误码/HTTP 状态码中的任意一项。"
    return ""


def _route_after_intent(state: CustomerServiceState) -> str:
    if state.get("clarification_question"):
        return "clarify"
    if state.get("diagnostic_window"):
        return "historical_diagnosis"
    return "target_specialist_dispatch"


async def _persist_entity_memory(conversation_id: str | None, entities: dict[str, str]) -> None:
    """Persist safe structured entities without making observability an outage risk."""
    if not conversation_id:
        return
    await conversation_memory.update_entities(conversation_id, entities, replace=True)
    try:
        from app.db.models import ConversationSession
        from app.db.session import SessionLocal

        async with SessionLocal() as db:
            session = await db.get(ConversationSession, conversation_id)
            if session:
                session.collected_entities_json = json.dumps(entities, ensure_ascii=False)
                await db.commit()
    except Exception as exc:
        logger.warning("[ROUTER] entity memory persistence skipped: %s", exc)


class CustomerServiceWorkflow:
    """LangGraph orchestration for one PaiSmart customer-service generation.

    LangGraph owns *workflow state and routing*. The existing ToolRegistry still owns
    schema validation, scopes, timeout and execution; AgentRuntime still owns concurrent
    tool scheduling. This keeps the graph readable instead of turning every RAG/MCP
    implementation detail into a graph node.
    """

    def __init__(
        self,
        *,
        runtime: "AgentRuntime",
        user: "User",
        send_json: "SendJson",
        on_chunk: "ChunkCallback",
    ) -> None:
        self.runtime = runtime
        self.user = user
        self.send_json = send_json
        self.on_chunk = on_chunk
        self._streamed_answer = ""

    async def _mark_node(self, state: CustomerServiceState, node: str) -> list[str]:
        path = list(state.get("graph_path") or [])
        path.append(node)
        logger.info("[GEN %s] workflow stage=%s step=%s", _gid(state.get("generation_id")), node, state.get("step", 0))
        _console(f"[GEN {_gid(state.get('generation_id'))}] workflow stage={node} step={state.get('step', 0)}")
        await self.send_json(
            {
                "type": "workflow_node",
                "node": node,
                "engine": LANGGRAPH_ENGINE,
                "generationId": state.get("generation_id"),
                "timestamp": int(time.time() * 1000),
            }
        )
        return path

    async def load_context(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "load_context")
        return {
            "history": list(state.get("history") or []),
            "entity_memory": dict(state.get("entity_memory") or {}),
            "references": dict(state.get("references") or {}),
            "content_parts": list(state.get("content_parts") or []),
            "step": int(state.get("step") or 0),
            "max_steps": max(1, self.runtime.settings.agent_max_steps),
            "graph_path": path,
            "workflow_engine": LANGGRAPH_ENGINE,
        }

    async def extract_entities(self, state: CustomerServiceState) -> dict:
        """Classify low-risk intent hints and resolve auditable request entities."""
        path = await self._mark_node(state, "extract_entities")
        catalog = skill_registry.catalog_prompt()
        classification: dict = {}
        simple_document = simple_document_question(state['question'],state.get('history'),state.get('entity_memory'))
        proposed=routing_policy.decide(state['question'])
        simple_document = bool(simple_document and proposed.selected_agents==('knowledge',) and proposed.risk_level=='LOW' and self.runtime.registry.get('search_knowledge'))
        if simple_document:
            classification={'intent':'product_usage','skills':['knowledge'],'needs_human':False,'confidence':1.0,'is_follow_up':False,'entities':{}}
        elif self.runtime.settings.skills_semantic_routing_enabled:
            can_use_cache = not state.get("history") and not state.get("entity_memory")
            if can_use_cache:
                classification = await route_cache.get(state["question"]) or {}
                if classification:
                    _console(f"[GEN {_gid(state.get('generation_id'))}] route_cache=HIT")
            if not classification:
                classification = await llm_service.classify_intent(
                    state["question"],
                    state.get("history") or [],
                    skill_catalog=catalog,
                    entity_memory=state.get("entity_memory") or {},
                )
                if can_use_cache and classification:
                    await route_cache.put(state["question"], classification)

        model_entities = classification.get("entities") if classification else {}
        follow_up = classification.get("is_follow_up") if "is_follow_up" in classification else None
        turn_context = state.get("turn_context")
        if turn_context:
            entities, entity_sources = dict(turn_context.entities), dict(turn_context.sources)
        else:
            entities, entity_sources = resolve_entities(
                state["question"], state.get("history") or [], model_entities=model_entities,
                remembered_entities=state.get("entity_memory") or {}, follow_up=follow_up,
            )
        remembered = dict(entities)
        from app.support.billing import requested_billing_month

        billing_month = requested_billing_month(state["question"])
        if billing_month:
            entities["month"] = billing_month
            entity_sources["month"] = "current"
        if classification:
            classification["entities"] = entities
            classification["entity_sources"] = entity_sources
            classification["is_follow_up"] = bool(
                classification.get("is_follow_up") or looks_like_follow_up(state["question"], state.get("history") or [])
            )
        else:
            classification = {
                "intent": "keyword_fallback",
                "skills": [],
                "needs_human": False,
                "confidence": 0.0,
                "is_follow_up": looks_like_follow_up(state["question"], state.get("history") or []),
                "entities": entities,
                "entity_sources": entity_sources,
            }

        if turn_context:
            classification["is_follow_up"] = turn_context.continuing
        else:
            await _persist_entity_memory(state.get("conversation_id"), remembered)
        shadow_metrics = {}
        if (shadow := state.get("shadow_context")) is not None:
            from app.agent.continuation import compare_context_selection

            shadow_metrics = compare_context_selection(entities, shadow, state["question"])
            await self.send_json({"type": "context_shadow", "generationId": state["generation_id"],
                                  "status": "compared", **shadow_metrics})
        await self.send_json({'type':'complexity_decision','mode':'simple_document' if simple_document else 'full_workflow',
                              'reason':'independent_single_vendor_read' if simple_document else 'retain_semantic_and_specialist_steps',
                              'generationId':state['generation_id']})
        await self.send_json(
            {
                "type": "entities_extracted",
                "intent": classification["intent"],
                "confidence": classification["confidence"],
                "diagnosticScope": classification.get("diagnostic_scope"),
                "entities": entities,
                "entitySources": entity_sources,
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "intent_classification": classification,
            "simple_document_candidate": simple_document,
            "entity_memory": remembered,
            "entities": entities,
            "entity_sources": entity_sources,
            "context_shadow_metrics": shadow_metrics,
            "graph_path": path,
        }

    async def apply_routing_policy(self, state: CustomerServiceState) -> dict:
        """Select target specialists deterministically after entity extraction."""
        path = await self._mark_node(state, "routing_policy")
        classification = dict(state.get("intent_classification") or {})
        if (turn_context := state.get("turn_context")) and turn_context.ambiguous:
            clarification = "这里涉及多个请求号。请指定本轮需要排查哪一个请求。"
            return {
                "intent_classification": {**classification, "needs_human": False,
                                          "clarification_question": clarification},
                "clarification_question": clarification,
                "routing_decision": {}, "graph_path": path,
            }
        entities = dict(state.get("entities") or {})
        decision = routing_policy.decide(state["question"], entities, classification)
        if not decision.requires_handoff_after_summary and decision.reason not in {"chitchat", "document_rule_question"}:
            window = diagnostic_window(
                state["question"], state.get("history") or [], diagnostic="api_diagnostic" in decision.selected_agents,
            )
            if window:
                question = window.next_question(datetime.now(timezone.utc))
                await self.send_json({
                    "type": "routing_decision", "generationId": state["generation_id"],
                    "intent": "api_diagnostic", "routingPolicy": decision.to_dict(),
                    "targetAgentPlans": [], "needsClarification": bool(question),
                    "diagnosticMode": "historical_window",
                })
                return {
                    "intent_classification": {**classification, "clarification_question": question},
                    "clarification_question": question,
                    "diagnostic_window": window, "graph_path": path,
                }
        classification["clarification_question"] = (
            vendor_clarification(state["question"]) if decision.selected_agents == ("knowledge",) else ""
        )
        if (not classification["clarification_question"] and not decision.requires_handoff_after_summary
                and decision.reason != "chitchat"):
            classification["clarification_question"] = _diagnostic_clarification(
                classification, entities, diagnostic="api_diagnostic" in decision.selected_agents,
                question=state["question"],
            )
        from app.diagnosis.service import begin_turn, read_detail

        retain_idle_case = (
            turn_context and turn_context.metadata.get("retainedCase")
            and "api_diagnostic" not in decision.selected_agents
        )
        diagnosis_id = None if retain_idle_case else await begin_turn(
            user_id=str(self.user.id), conversation_id=state.get("conversation_id"),
            generation_id=state["generation_id"], question=state["question"],
            entities=entities, sources=state.get("entity_sources") or {},
            diagnostic="api_diagnostic" in decision.selected_agents,
        )
        if diagnosis_id:
            await self.send_json({"type": "diagnosis_state", "generationId": state["generation_id"],
                                  "diagnosis": await read_detail(self.user, diagnosis_id)})
        diagnosis_lease, preflight = None, []
        if diagnosis_id:
            from app.diagnosis.execution import ExecutionBusy, ExecutionLost, run_turn
            async def execute_diagnostic(call):
                return (await self.runtime._execute_parallel(calls=[call], user=self.user,
                    generation_id=state["generation_id"], send_json=self.send_json, step=0,
                    active_skills=frozenset({"api-diagnostic"})))[0]
            try:
                diagnosis_lease, preflight = await run_turn(state["generation_id"], self.user, self.runtime.registry,
                                                           executor_override=execute_diagnostic)
            except (ExecutionBusy, ExecutionLost):
                classification["clarification_question"] = "本轮诊断正在执行或已被更新，请查看最新诊断状态。"
        plans = build_target_agent_plans(decision, skill_registry)
        plan_payload = [plan.to_dict() for plan in plans]
        logger.info(
            "[GEN %s] routing_policy intent=%s agents=%s risk=%s rules=%s",
            _gid(state.get("generation_id")),
            classification.get("intent", "keyword_fallback"),
            list(decision.selected_agents),
            decision.risk_level,
            list(decision.matched_rules),
        )
        await self.send_json(
            {
                "type": "routing_decision",
                "intent": classification.get("intent") or "keyword_fallback",
                "routingPolicy": decision.to_dict(),
                "targetAgentPlans": plan_payload,
                "needsClarification": bool(classification["clarification_question"]),
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "active_skills": [],
            "diagnosis_id": diagnosis_id,
            "diagnosis_lease": diagnosis_lease,
            "target_tool_outcomes": preflight,
            "agent_evidence": [e.to_dict() for e in evidence_joiner.build_agent_evidence(preflight)],
            "executed_tool_fingerprints": [tool_call_fingerprint(call) for call, _ in preflight],
            "executed_tool_call_count": len(preflight),
            "intent_classification": classification,
            "routing_decision": decision.to_dict(),
            "clarification_question": classification["clarification_question"],
            "graph_path": path,
        }

    async def historical_diagnosis(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "historical_diagnosis")
        window = state["diagnostic_window"]
        now = datetime.now(timezone.utc)
        call = AgentToolCall(
            id=f"historical-{uuid.uuid4().hex}",
            name="query_recent_call_stats",
            arguments=window.arguments(now),
            source_skill="api-diagnostic",
        )
        results = await self.runtime._execute_parallel(
            calls=[call], user=self.user, generation_id=state["generation_id"],
            send_json=self.send_json, step=0, active_skills=frozenset({"api-diagnostic"}),
        )
        result = results[0]
        trace = SkillTrace(
            question=state["question"], intent_classification=dict(state["intent_classification"]),
            entities=dict(state.get("entities") or {}), entity_sources=dict(state.get("entity_sources") or {}),
        )
        trace.record_batch(0, [call], results)
        if result.status == "SUCCESS" and isinstance(result.data, dict) and result.data.get("windowStart"):
            answer = render_window_result(result.data, window.error)
        else:
            answer = "历史调用统计暂时不可用，目前无法核实该时段的故障。"
        return {"skill_trace": trace, "draft_answer": answer, "final_chunks": [answer], "graph_path": path}

    async def clarify(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "clarify")
        question = str(
            (state.get("intent_classification") or {}).get("clarification_question")
            or "请补充更多问题上下文，以便准确处理。"
        )
        trace = SkillTrace(
            question=state["question"],
            intent_classification=dict(state.get("intent_classification") or {}),
            entities=dict(state.get("entities") or {}),
            entity_sources=dict(state.get("entity_sources") or {}),
            initial_skills=list(state.get("active_skills") or []),
            active_skills=list(state.get("active_skills") or []),
        )
        await self.send_json(
            {
                "type": "clarification_requested",
                "question": question,
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "skill_trace": trace,
            "draft_answer": question,
            "final_chunks": [question],
            "next_action": "safety",
            "graph_path": path,
        }

    async def target_specialist_dispatch(self, state: CustomerServiceState) -> dict:
        """Run selected LLM specialist planners concurrently, then schedule their Tools."""
        path = await self._mark_node(state, "target_specialist_dispatch")
        optimization = await query_optimizer.optimize(
            user_id=str(self.user.id),
            conversation_id=str(state.get("conversation_id") or ""),
            question=state["question"],
            history=list(state.get("history") or []),
            entity_memory=dict(state.get("entity_memory") or {}),
            recalled_history=state["turn_context"].recall if state.get("turn_context") else None,
            is_follow_up=bool((state.get("intent_classification") or {}).get("is_follow_up")),
        )
        retrieval_query = optimization.query
        await self.send_json(
            {
                "type": "retrieval_query_optimized",
                "applied": optimization.applied,
                "mode": optimization.mode,
                "cacheHit": optimization.cache_hit,
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        plans = [
            AgentPlan(
                agent=str(item.get("agent") or ""),
                skill=str(item.get("skill") or ""),
                allowed_tools=tuple(str(name) for name in item.get("allowedTools") or ()),
                objective=str(item.get("objective") or ""),
            )
            for item in state.get("agent_plans") or []
            if isinstance(item, dict)
        ]
        initial_dispatch = not plans
        if initial_dispatch:
            plans = build_target_agent_plans(
                routing_decision_from_dict(state.get("routing_decision")),
                skill_registry,
            )

        billing_catalog: list[dict] = []
        billing_discovery_failures: list[dict] = []
        if billing_mcp_adapter.enabled and any(plan.agent == "billing" for plan in plans):
            try:
                with langfuse_span("billing_mcp.discover", kind="tool"):
                    discovered_tools = await billing_mcp_adapter.discover_tools()
                for tool in discovered_tools:
                    self.runtime.registry.register_discovered(tool)
                discovered_names = tuple(tool.name for tool in discovered_tools)
                billing_catalog = [tool.spec.to_dict() for tool in discovered_tools]
                plans = [
                    AgentPlan(plan.agent, plan.skill, discovered_names, plan.objective)
                    if plan.agent == "billing"
                    else plan
                    for plan in plans
                ]
                await self.send_json(
                    {
                        "type": "billing_mcp_tools_discovered",
                        "tools": billing_catalog,
                        "generationId": state["generation_id"],
                        "timestamp": int(time.time() * 1000),
                    }
                )
            except Exception as exc:
                # Discovery is a Billing evidence failure, not a chance to fall
                # back silently to static local Tool schemas.
                plans = [
                    AgentPlan(plan.agent, plan.skill, (), plan.objective)
                    if plan.agent == "billing"
                    else plan
                    for plan in plans
                ]
                billing_discovery_failures.append(
                    AgentEvidence(
                        agent="billing",
                        status="failed",
                        unresolved_items=(f"mcp_discovery:{type(exc).__name__}",),
                        recommended_handoff=True,
                    ).to_dict()
                )

        from app.diagnosis.planning import api_planning_complete
        completed_agents = frozenset()
        if state.get("diagnosis_lease") and api_planning_complete(str(self.user.id), state["generation_id"],
                state.get("entities") or {}, state.get("target_tool_outcomes") or []):
            completed_agents = frozenset({"api_diagnostic"})
            await self.send_json({"type": "diagnosis_planning_skipped", "agent": "api_diagnostic",
                "reason": "versioned_at_call_evidence_sufficient", "generationId": state["generation_id"]})
        if initial_dispatch and state.get('simple_document_candidate') and len(plans)==1 and plans[0].agent=='knowledge':
            call=AgentToolCall('simple_document_'+uuid.uuid4().hex,'search_knowledge',
                {'query':state['question'],'top_k':8,'filters':{'product':named_products(state['question'])[0]}},'knowledge','knowledge')
            work=[TargetAgentWork(plan=plans[0],proposed_calls=(call,))]
            planning_mode='bounded_document_read'
        else:
            planning_mode='concurrent_llm'
            work = await target_specialist_agents.plan_work(
                plans=plans,
                question=state["question"],
                retrieval_query=retrieval_query,
                entities=dict(state.get("entities") or {}),
                registry=skill_registry,
                tool_registry=self.runtime.registry,
                agent_evidence=state.get("agent_evidence") or [],
                references=list((state.get("references") or {}).values()),
                fallback_outcomes=state.get("target_tool_outcomes") or (),
                attempted_call_fingerprints=state.get("executed_tool_fingerprints") or (),
                max_agents=self.runtime.settings.agent_max_concurrency,
                completed_agents=completed_agents,
            )
        executed_tool_count = int(state.get("executed_tool_call_count") or 0)
        remaining_tool_budget = max(0, int(self.runtime.settings.agent_max_tool_calls) - executed_tool_count)
        schedule = shared_tool_scheduler(
            max_agents=self.runtime.settings.agent_max_concurrency,
            max_tools=self.runtime.settings.agent_tool_global_concurrency,
            max_total_tools=remaining_tool_budget,
        ).plan(
            work,
            registry=self.runtime.registry,
        )
        schedule_payload = schedule.to_dict()
        calls = [entry.call for batch in schedule.tool_batches for entry in batch.calls]
        active_skills = list(state.get("active_skills") or [])
        if initial_dispatch:
            active_skills = list(dict.fromkeys(work_item.plan.skill for work_item in work))
            trace = SkillTrace(
                question=state["question"],
                intent_classification=dict(state.get("intent_classification") or {}),
                entities=dict(state.get("entities") or {}),
                entity_sources=dict(state.get("entity_sources") or {}),
                initial_skills=list(active_skills),
                active_skills=list(active_skills),
            )
            if state.get("target_tool_outcomes"):
                seeds = state["target_tool_outcomes"]
                trace.record_batch(0, [call for call, _ in seeds], [result for _, result in seeds])
        else:
            trace = state["skill_trace"]

        planning = [
            {
                "agent": item.plan.agent,
                "skill": item.plan.skill,
                "toolCalls": [call.name for call in item.proposed_calls],
                "error": item.planning_error,
            }
            for item in work
        ]
        planning_failures = [
            AgentEvidence(
                agent=item.plan.agent,
                status="failed",
                unresolved_items=(f"planner:{item.planning_error}",),
                recommended_handoff=True,
            ).to_dict()
            for item in work
            if item.planning_error
        ]
        await self.send_json(
            {
                "type": "target_specialists_dispatched",
                "planningMode": planning_mode,
                "agents": [item.plan.agent for item in work],
                "agentPlans": planning,
                "toolBatches": schedule_payload["toolBatches"],
                "toolBudget": {
                    "limit": int(self.runtime.settings.agent_max_tool_calls),
                    "used": executed_tool_count,
                    "remaining": remaining_tool_budget,
                },
                "rejectedCalls": schedule_payload["rejectedCalls"],
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "retrieval_query": retrieval_query,
            "query_optimization": optimization.to_dict(),
            "active_skills": active_skills,
            "agent_plans": [item.plan.to_dict() for item in work],
            "agent_evidence": [
                *(state.get("agent_evidence") or []),
                *billing_discovery_failures,
                *planning_failures,
            ],
            "billing_mcp_catalog": billing_catalog,
            "tool_batches": [*(state.get("tool_batches") or []), *schedule_payload["toolBatches"]],
            "target_scheduled_batches": schedule_payload["toolBatches"],
            "tool_calls": calls,
            "skill_trace": trace,
            "next_action": "target_execute_tools" if calls else "target_evidence_join",
            "graph_path": path,
        }

    async def target_execute_tools(self, state: CustomerServiceState) -> dict:
        """Execute scheduler-approved reads, then return to concurrent Agent planning."""
        path = await self._mark_node(state, "target_execute_tools")
        calls = list(state.get("tool_calls") or [])
        trace = state["skill_trace"]
        calls_by_id = {call.id: call for call in calls}
        outcomes: list[tuple[AgentToolCall, "ToolResult"]] = []
        step_offset = int(state.get("step") or 0)
        for batch_index, batch in enumerate(state.get("target_scheduled_batches") or []):
            batch_calls = [
                calls_by_id[call_id]
                for call_id in batch.get("toolCallIds") or []
                if call_id in calls_by_id
            ]
            if not batch_calls:
                continue
            batch_results = await self.runtime._execute_parallel(
                calls=batch_calls,
                user=self.user,
                generation_id=state["generation_id"],
                send_json=self.send_json,
                step=step_offset + batch_index,
                active_skills=frozenset(state.get("active_skills") or []),
                diagnosis_lease=state.get("diagnosis_lease"),
            )
            trace.record_batch(step_offset + batch_index, batch_calls, batch_results)
            outcomes.extend(zip(batch_calls, batch_results, strict=True))

        references = dict(state.get("references") or {})
        for call, result in outcomes:
            self.runtime._collect_references(call, result, references)
        evidence = evidence_joiner.build_agent_evidence(outcomes)
        agent_evidence = [*(state.get("agent_evidence") or []), *(item.to_dict() for item in evidence)]
        next_step = step_offset + 1
        max_steps = int(state.get("max_steps") or self.runtime.settings.agent_max_steps)
        completed_call_count = int(state.get("executed_tool_call_count") or 0) + len(outcomes)
        max_tool_calls = int(self.runtime.settings.agent_max_tool_calls)
        replan = next_step < max_steps and completed_call_count < max_tool_calls
        simple_complete=bool(state.get('simple_document_candidate') and usable_document_read(outcomes,state['question']))
        if state.get('simple_document_candidate'):
            await self.send_json({'type':'document_path_result','complete':simple_complete,
                'action':'generate_with_verified_sources' if simple_complete else 'fallback_to_full_specialist',
                'generationId':state['generation_id']})
        if simple_complete:
            replan=False
        if not replan and not simple_complete:
            unresolved = "TOOL_BUDGET" if completed_call_count >= max_tool_calls else "MAX_STEPS"
            for plan in state.get("agent_plans") or []:
                agent_evidence.append(
                    AgentEvidence(
                        agent=str(plan.get("agent") or ""),
                        status="partial",
                        unresolved_items=(unresolved,),
                        recommended_handoff=True,
                    ).to_dict()
                )
        await self.send_json(
            {
                "type": "agent_evidence",
                "traceOnly": False,
                "evidence": [item.to_dict() for item in evidence],
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "references": references,
            "simple_document_candidate":bool(state.get('simple_document_candidate') and simple_complete),
            "simple_document_complete":simple_complete,
            "agent_evidence": agent_evidence,
            "tool_calls": [],
            "target_tool_outcomes": [*(state.get("target_tool_outcomes") or []), *outcomes],
            "target_scheduled_batches": [],
            "executed_tool_fingerprints": list(
                dict.fromkeys([
                    *(state.get("executed_tool_fingerprints") or []),
                    *(tool_call_fingerprint(call) for call, _result in outcomes),
                ])
            ),
            "executed_tool_call_count": completed_call_count,
            "step": next_step,
            "skill_trace": trace,
            "next_action": "target_specialist_dispatch" if replan else "target_evidence_join",
            "graph_path": path,
        }

    async def target_evidence_join(self, state: CustomerServiceState) -> dict:
        """Compose internal facts before any durable human-handoff write occurs."""
        path = await self._mark_node(state, "target_evidence_join")
        from app.agent.types import AgentEvidence

        evidence = [
            AgentEvidence(
                agent=str(item.get("agent") or ""),
                status=str(item.get("status") or "unknown"),
                verified_facts=tuple(item.get("verifiedFacts") or ()),
                knowledge_excerpts=tuple(item.get("knowledgeExcerpts") or ()),
                citations=tuple(item.get("citations") or ()),
                attempted_tools=tuple(item.get("attemptedTools") or ()),
                unresolved_items=tuple(item.get("unresolvedItems") or ()),
                recommended_handoff=bool(item.get("recommendedHandoff")),
                tool_failures=tuple(item.get("toolFailures") or ()),
            )
            for item in state.get("agent_evidence") or []
            if isinstance(item, dict)
        ]
        composition = evidence_composer.compose(
            question=state["question"],
            routing=routing_decision_from_dict(state.get("routing_decision")),
            evidence=evidence,
            citations=list((state.get("references") or {}).values()),
        )
        summary = composition.to_dict()
        diagnosis_decision = {}
        if state.get("diagnosis_id") and state.get("diagnosis_lease"):
            from app.diagnosis.service import finish_turn, read_detail
            finalized = await finish_turn(user_id=str(self.user.id), conversation_id=state.get("conversation_id"),
                generation_id=state["generation_id"], question=state["question"],
                outcomes=state.get("target_tool_outcomes") or [], references=list((state.get("references") or {}).values()),
                execution_epoch=state["diagnosis_lease"].epoch)
            detail = await read_detail(self.user, state["diagnosis_id"])
            diagnosis_decision = {**((detail.get("workflow") or {}).get("decision") or {}),
                                  "caseStatus": detail["status"], "nextAction": detail["nextAction"]}
            from app.db.models import DiagnosisExecution
            from app.diagnosis import service as diagnostic_service
            async with diagnostic_service.SessionLocal() as db:
                current_execution = await db.get(DiagnosisExecution, state["generation_id"])
                same_epoch = current_execution and current_execution.epoch == state["diagnosis_lease"].epoch
            if not finalized or detail["lastGenerationId"] != state["generation_id"] or not same_epoch:
                diagnosis_decision = {"superseded": True, "handoffRequired": False}
                summary["verifiedFacts"] = []
                summary["handoffDecision"]["required"] = False
            summary["diagnosisDecision"] = diagnosis_decision
            if diagnosis_decision.get("handoffRequired"):
                from app.db.models import DiagnosisSession
                from app.diagnosis import service as diagnostic_service
                from app.diagnosis.loop import handoff_summary
                async with diagnostic_service.SessionLocal() as db:
                    case = await db.get(DiagnosisSession, state["diagnosis_id"])
                    ticket_summary = handoff_summary(case)
                summary["handoffDecision"].update(required=True,
                    reasons=diagnosis_decision["handoffReasons"], ticketSummary=ticket_summary)
        await self.send_json(
            {
                "type": "evidence_summary",
                "traceOnly": False,
                "summary": summary,
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {"evidence_summary": summary, "diagnosis_decision": diagnosis_decision, "graph_path": path}

    async def target_handoff_decision(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "target_handoff_decision")
        decision = dict((state.get("evidence_summary") or {}).get("handoffDecision") or {})
        await self.send_json(
            {
                "type": "handoff_decision",
                "decision": decision,
                "generationId": state["generation_id"],
                "timestamp": int(time.time() * 1000),
            }
        )
        return {"next_action": "target_create_handoff" if decision.get("required") else "target_generate_response", "graph_path": path}

    async def target_create_handoff(self, state: CustomerServiceState) -> dict:
        """The target path's only write node, reached after evidence summary."""
        path = await self._mark_node(state, "target_create_handoff")
        handoff = dict((state.get("evidence_summary") or {}).get("handoffDecision") or {})
        call = AgentToolCall(
            id=f"target_handoff_{uuid.uuid4().hex}",
            name=HANDOFF_CREATE,
            arguments={
                "reason": "; ".join(str(item) for item in handoff.get("reasons") or ()) or "需要人工核验",
                "summary": str(handoff.get("ticketSummary") or "客户请求人工处理，未生成足够的内部摘要。"),
                "category": str(handoff.get("category") or "GENERAL"),
                "priority": str(handoff.get("priority") or "NORMAL"),
            },
            source_agent="handoff_decision",
            source_skill="escalation",
        )
        active_skills = list(dict.fromkeys([*(state.get("active_skills") or []), "escalation"]))
        result = (await self.runtime._execute_parallel(
            calls=[call],
            user=self.user,
            generation_id=state["generation_id"],
            send_json=self.send_json,
            step=1,
            active_skills=frozenset(active_skills),
            diagnosis_lease=state.get("diagnosis_lease"),
            handoff_authorization=authorize_handoff(str(self.user.id), state["generation_id"], call.arguments),
        ))[0]
        trace = state["skill_trace"]
        trace.activate("escalation")
        trace.record_batch(1, [call], [result])
        receipt = handoff_receipt(result)
        return {
            "active_skills": active_skills,
            "skill_trace": trace,
            "handoff_attempted": True,
            "handoff_success": receipt.success,
            "handoff_id": receipt.handoff_id,
            "handoff_result": receipt.to_dict(),
            "graph_path": path,
        }

    async def target_generate_response(self, state: CustomerServiceState) -> dict:
        """Generate an answer from the evidence contract, never raw Tool payloads."""
        path = await self._mark_node(state, "target_generate_response")
        evidence = dict(state.get("evidence_summary") or {})
        handoff = dict(state.get("handoff_result") or HandoffResult().to_dict())
        references = list((state.get("references") or {}).values())
        messages = build_answer_messages(state, evidence, handoff, references)
        if state.get('simple_document_complete'):
            packed = pack_document_context(state['question'], evidence, references)
            await self.send_json({'type': 'document_context_budget', 'bounded': packed.bounded,
                                 **packed.metrics, 'generationId': state['generation_id']})
            if packed.bounded:
                messages = packed.messages
                references = packed.references
                evidence = relabel_evidence(evidence, references, packed.reference_remap)
                await self.send_json({'type': 'document_reference_remap',
                                     'mapping': packed.reference_remap,
                                     'generationId': state['generation_id']})
            else:
                # Prefer the original evidence to a cheap answer missing an
                # exception. Retrieval failures already re-enter full planning.
                messages[0]['content'] += '这是单厂商文档配置问题。直接回答所问参数，保留适用范围与引用。'
        messages[0]["content"] += (
            "凭据示例可读取环境变量，严禁将凭据打印到终端、日志或 HTTP 响应。"
            "只问 Python 怎样读取环境变量时，用 os.getenv('变量名') 给最简示例，"
            "只说明如何判断变量是否设置；只有用户要求特定厂商时才补 SDK 和端点。"
        )
        active_skills = list(dict.fromkeys([*(state.get("active_skills") or []), "customer-support"]))
        trace = state["skill_trace"]
        trace.activate("customer-support")
        reference_mappings = {str(reference["referenceNumber"]): reference for reference in references}
        await self.send_json({"type": "answer_start", "generationId": state["generation_id"],
                              "referenceMappings": reference_mappings})
        units = StreamUnitBuffer()
        ready_prefix = ""

        async def publish_ready(unit: str) -> None:
            nonlocal ready_prefix
            ready_prefix += unit
            candidate = ready_prefix
            if state.get('simple_document_complete'):
                candidate, removed = filter_document_absence_claims(candidate)
                if removed and candidate == "当前检索片段不足以确认所问信息，需要进一步核对适用的完整文档。":
                    return
            if not candidate.strip():
                return
            # Check the cumulative prefix, not isolated provider tokens. This
            # preserves the existing evidence, credential and handoff gates.
            checked = await self.safety({
                **state, "active_skills": active_skills, "draft_answer": candidate,
                "references": reference_mappings,
                "evidence_summary": evidence,
            }, preview=True)
            if checked.get("quality_gate_blocked"):
                return
            approved = without_citation_footer(checked["final_answer"])
            if approved.startswith(self._streamed_answer):
                delta = approved[len(self._streamed_answer):]
                if delta:
                    await self.on_chunk(delta)
                    self._streamed_answer = approved

        offline = not llm_service.settings.llm_api_key
        action_answer = render_action_answer(
            specialists=tuple((state.get("routing_decision") or {}).get("selectedAgents") or ()),
            handoff=handoff,
            billing_month=(state.get("entities") or {}).get("month"),
            evidence=evidence,
            attempted_tools={call.name for call, _ in state.get("target_tool_outcomes") or ()},
            offline=offline,
        )
        if action_answer is None and not offline and not handoff_required(state):
            action_answer = retrieval_unavailable_answer(state)
        if offline and action_answer is None:
            action_answer = render_document_excerpts(evidence, references, question=state["question"]) or None
            if handoff.get("attempted"):
                receipt_answer = render_action_answer(
                    specialists=(), handoff=handoff, billing_month=None, evidence={}, attempted_tools=set(),
                )
                action_answer = "\n\n".join(text for text in (action_answer, receipt_answer) if text)
        chunks: list[str] = []
        if state.get("diagnosis_decision"):
            from app.diagnosis.response import render
            chunks.append(render(state["diagnosis_decision"], evidence.get("verifiedFacts") or [], handoff))
            turn_context = state.get("turn_context")
            if turn_context and turn_context.progress and not state["diagnosis_decision"].get("superseded"):
                reports = "\n".join(f"- 「{item['text'].replace(chr(10), ' ')}」" for item in turn_context.progress)
                chunks.append(f"\n\n以下是你此前反馈的排障进度，作为续办线索：\n{reports}")
            if references:
                chunks.append("\n\n附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。")
        elif action_answer is not None:
            chunks.append(action_answer)
        else:
            async with aclosing(llm_service.stream_messages(messages, force_no_tools=True)) as stream:
                async for chunk in stream:
                    chunks.append(chunk)
                    for unit in units.feed(chunk):
                        await publish_ready(unit)
        # Bounded deterministic diagnosis text is ready immediately; no fake
        # token delays or extra model call is added to animate it.
        if state.get("diagnosis_decision") or action_answer is not None:
            for unit in units.feed("".join(chunks)):
                await publish_ready(unit)
        for unit in units.feed("", final=True):
            await publish_ready(unit)
        if not chunks:
            chunks.append("已完成信息核验；当前未能生成可安全发送的答复。")
        if state.get('simple_document_complete'):
            guarded, removed = filter_document_absence_claims(''.join(chunks))
            chunks = [guarded]
            if removed:
                await self.send_json({'type': 'document_absence_claim_filtered', 'sentences': removed,
                                     'generationId': state['generation_id']})
        draft_answer = ensure_reference_citations("".join(chunks), references)
        return {
            "active_skills": active_skills,
            "skill_trace": trace,
            "content_parts": [draft_answer],
            "draft_answer": draft_answer,
            "final_chunks": [draft_answer],
            "graph_path": path,
            "references": reference_mappings,
            "evidence_summary": evidence,
        }

    async def safety(self, state: CustomerServiceState, *, preview: bool = False) -> dict:
        path = list(state.get("graph_path") or []) if preview else await self._mark_node(state, "safety")
        result = await audit_answer(state, send_json=self.send_json, preview=preview)
        return {**result, "graph_path": path}

    async def emit_final(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "emit_final")
        replaced = False
        final = redact_text(str(state.get("final_answer") or ""))
        if self._streamed_answer:
            if final.startswith(self._streamed_answer):
                suffix = final[len(self._streamed_answer):]
                if suffix:
                    await self.on_chunk(suffix)
            else:
                # Canonical citations or final freshness checks can revise the
                # displayed prefix. Never append a second answer to the first.
                replaced = True
                await self.send_json({"type": "answer_replace", "content": final,
                                      "generationId": state["generation_id"]})
            with langfuse_span("answer_delivery") as span:
                observation_output(span, {"replaced": replaced, "answerChars": len(final)})
            return {"graph_path": path}
        chunks = [redact_text(str(chunk)) for chunk in list(state.get("final_chunks") or [])]
        if not chunks:
            chunks = [redact_text(str(state.get("final_answer") or ""))]
        for chunk in chunks:
            if chunk:
                await self.on_chunk(chunk)
        with langfuse_span("answer_delivery") as span:
            observation_output(span, {"replaced": False, "answerChars": len(final)})
        return {"graph_path": path}

    async def persist_trace(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "persist_trace")
        if state.get("diagnosis_id"):
            from app.diagnosis.service import finish_turn, read_detail

            diagnosis_id = await finish_turn(
                user_id=str(self.user.id), conversation_id=state.get("conversation_id"),
                generation_id=state["generation_id"], question=state["question"],
                outcomes=state.get("target_tool_outcomes") or [],
                references=list((state.get("references") or {}).values()),
                handoff=state.get("handoff_result"), blocked=bool(state.get("quality_gate_blocked")),
                execution_epoch=state["diagnosis_lease"].epoch if state.get("diagnosis_lease") else None,
            )
            lease = state.get("diagnosis_lease")
            handoff = state.get("handoff_result") or {}
            if lease and handoff.get("attempted") and not handoff.get("success"):
                from app.diagnosis.execution import release_pending_handoff

                await release_pending_handoff(lease)
            if diagnosis_id:
                await self.send_json({"type": "diagnosis_state", "generationId": state["generation_id"],
                                      "diagnosis": await read_detail(self.user, diagnosis_id)})
        trace = state["skill_trace"]
        active_skills = list(state.get("active_skills") or [])
        summary = trace.summary()
        agent_evidence = list(state.get("agent_evidence") or [])
        evidence_summary = dict(state.get("evidence_summary") or {})
        if state.get("routing_decision"):
            records = [
                AgentEvidence(
                    agent=str(item.get("agent") or ""),
                    status=str(item.get("status") or "unknown"),
                    verified_facts=tuple(item.get("verifiedFacts") or ()),
                    knowledge_excerpts=tuple(item.get("knowledgeExcerpts") or ()),
                    citations=tuple(item.get("citations") or ()),
                    attempted_tools=tuple(item.get("attemptedTools") or ()),
                    unresolved_items=tuple(item.get("unresolvedItems") or ()),
                    recommended_handoff=bool(item.get("recommendedHandoff")),
                    tool_failures=tuple(item.get("toolFailures") or ()),
                )
                for item in agent_evidence
                if isinstance(item, dict)
            ]
            composition = evidence_composer.compose(
                question=state.get("question") or "",
                routing=routing_decision_from_dict(state.get("routing_decision")),
                evidence=records,
                citations=list((state.get("references") or {}).values()),
            )
            evidence_summary = composition.to_dict()
            if state.get("diagnosis_decision"):
                evidence_summary["diagnosisDecision"] = state["diagnosis_decision"]
                previous = (state.get("evidence_summary") or {}).get("handoffDecision") or {}
                if state["diagnosis_decision"].get("handoffRequired"):
                    evidence_summary["handoffDecision"] = previous
            await self.send_json(
                {
                "type": "evidence_summary",
                "traceOnly": False,
                    "summary": evidence_summary,
                    "generationId": state["generation_id"],
                    "timestamp": int(time.time() * 1000),
                }
            )
        handoff_result = dict(state.get("handoff_result") or HandoffResult(
            attempted=bool(state.get("handoff_attempted")),
            success=bool(state.get("handoff_success")),
            handoff_id=state.get("handoff_id"),
        ).to_dict())
        recommended_gates: list[str] = []
        for skill_name in active_skills:
            skill = skill_registry.get(skill_name)
            if skill and skill.quality_gate and skill.quality_gate not in recommended_gates:
                recommended_gates.append(skill.quality_gate)
        quality_results = dict(state.get("quality_gate_results") or summary.get("qualityGateResults") or {})
        used_scripts = set(summary.get("scriptsUsed") or [])
        used_scripts.update(str(item.get("gate")) for item in quality_results.values() if item.get("gate"))
        missing_gates = [gate for gate in recommended_gates if gate not in used_scripts]
        repaired_gates = [key for key, item in quality_results.items() if bool(item.get("repaired"))]
        filtered_gates = [key for key, item in quality_results.items() if bool(item.get("filtered"))]
        failed_gates = [
            key for key, item in quality_results.items()
            if not bool(item.get("passed")) and not bool(item.get("repaired")) and not bool(item.get("filtered"))
        ]
        summary.update(
            {
                "architectureMode": "target",
                "routingDecision": dict(state.get("routing_decision") or {}),
                "agentPlans": list(state.get("agent_plans") or []),
                "toolBatchesV2": list(state.get("tool_batches") or []),
                "agentEvidence": agent_evidence,
                "evidenceSummary": evidence_summary,
                "handoffResult": handoff_result,
                "qualityGatesRecommended": recommended_gates,
                "qualityGatesUsed": [gate for gate in recommended_gates if gate in used_scripts],
                "qualityGatesMissing": missing_gates,
                "qualityGatesFailed": failed_gates,
                "qualityGatesRepaired": repaired_gates,
                "qualityGatesFiltered": filtered_gates,
                "qualityGateCoverage": (
                    round((len(recommended_gates) - len(missing_gates)) / len(recommended_gates), 4)
                    if recommended_gates
                    else 1.0
                ),
                "workflowEngine": LANGGRAPH_ENGINE,
                "graphPath": path,
                "graphTransitions": max(0, len(path) - 1),
                "handoffAttempted": bool(state.get("handoff_attempted")),
                "handoffSuccess": bool(state.get("handoff_success")),
                "handoffId": state.get("handoff_id"),
                "qualityGateBlocked": bool(state.get("quality_gate_blocked")),
                "qualityGateAction": state.get("quality_gate_action") or "passed",
            }
        )
        await self.send_json(
            {
                "type": "skill_trace",
                "status": "trace",
                "generationId": state["generation_id"],
                "trace": summary,
                "timestamp": int(time.time() * 1000),
            }
        )
        return {
            "trace_summary": summary,
            "agent_evidence": agent_evidence,
            "evidence_summary": evidence_summary,
            "handoff_result": handoff_result,
            "graph_path": path,
        }

    @staticmethod
    def _observed_node(name, node):
        async def run(state):
            with langfuse_span(name, kind="chain") as span:
                result = await node(state)
                if name == "routing_policy":
                    route = result.get("routing_decision") or {}
                    observation_output(span, {
                        "agents": route.get("selectedAgents") or [],
                        "rules": route.get("matchedRules") or [],
                    })
                return result

        return run

    def compile(self):
        graph = StateGraph(CustomerServiceState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("extract_entities", self._observed_node("extract_entities", self.extract_entities))
        graph.add_node("routing_policy", self._observed_node("routing_policy", self.apply_routing_policy))
        graph.add_node("clarify", self.clarify)
        graph.add_node("historical_diagnosis", self.historical_diagnosis)
        graph.add_node("target_specialist_dispatch", self._observed_node("target_specialist_dispatch", self.target_specialist_dispatch))
        graph.add_node("target_execute_tools", self._observed_node("target_execute_tools", self.target_execute_tools))
        graph.add_node("target_evidence_join", self.target_evidence_join)
        graph.add_node("target_handoff_decision", self._observed_node("target_handoff_decision", self.target_handoff_decision))
        graph.add_node("target_create_handoff", self.target_create_handoff)
        graph.add_node("target_generate_response", self.target_generate_response)
        graph.add_node("safety", self._observed_node("safety", self.safety))
        graph.add_node("emit_final", self.emit_final)
        graph.add_node("persist_trace", self.persist_trace)

        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "extract_entities")
        graph.add_edge("extract_entities", "routing_policy")
        graph.add_conditional_edges(
            "routing_policy",
            _route_after_intent,
            {
                "clarify": "clarify",
                "historical_diagnosis": "historical_diagnosis",
                "target_specialist_dispatch": "target_specialist_dispatch",
            },
        )
        graph.add_edge("clarify", "safety")
        graph.add_edge("historical_diagnosis", "safety")
        graph.add_conditional_edges(
            "target_specialist_dispatch",
            lambda state: str(state.get("next_action") or "target_evidence_join"),
            {
                "target_execute_tools": "target_execute_tools",
                "target_evidence_join": "target_evidence_join",
            },
        )
        graph.add_conditional_edges(
            "target_execute_tools",
            lambda state: str(state.get("next_action") or "target_evidence_join"),
            {
                "target_specialist_dispatch": "target_specialist_dispatch",
                "target_evidence_join": "target_evidence_join",
            },
        )
        graph.add_edge("target_evidence_join", "target_handoff_decision")
        graph.add_conditional_edges(
            "target_handoff_decision",
            lambda state: str(state.get("next_action") or "target_generate_response"),
            {
                "target_create_handoff": "target_create_handoff",
                "target_generate_response": "target_generate_response",
            },
        )
        graph.add_edge("target_create_handoff", "target_generate_response")
        graph.add_edge("target_generate_response", "safety")
        graph.add_edge("safety", "emit_final")
        graph.add_edge("emit_final", "persist_trace")
        graph.add_edge("persist_trace", END)
        return graph.compile()

    async def run(self, initial_state: CustomerServiceState) -> CustomerServiceState:
        compiled = self.compile()
        return await compiled.ainvoke(initial_state)


async def run_customer_service_graph(
    *,
    runtime: "AgentRuntime",
    user: "User",
    question: str,
    history: list[dict],
    conversation_id: str | None = None,
    entity_memory: dict[str, str] | None = None,
    turn_context=None,
    shadow_context=None,
    generation_id: str,
    send_json: "SendJson",
    on_chunk: "ChunkCallback",
) -> tuple[str, dict[str, dict]]:
    started = time.monotonic()
    first_chunk_ms = None

    async def observe_chunk(chunk: str) -> None:
        nonlocal first_chunk_ms
        if first_chunk_ms is None and chunk:
            first_chunk_ms = (time.monotonic() - started) * 1000
        await on_chunk(chunk)

    workflow = CustomerServiceWorkflow(runtime=runtime, user=user, send_json=send_json, on_chunk=observe_chunk)
    state: CustomerServiceState = {
        "question": question,
        "history": history,
        "conversation_id": conversation_id or "",
        "entity_memory": dict(entity_memory or {}),
        "turn_context": turn_context,
        "shadow_context": shadow_context,
        "generation_id": generation_id,
        "references": {},
        "content_parts": [],
        "step": 0,
        "handoff_attempted": False,
        "handoff_success": False,
        "handoff_id": None,
        "routing_decision": {},
        "agent_plans": [],
        "tool_batches": [],
        "agent_evidence": [],
        "evidence_summary": {},
        "handoff_result": {},
        "billing_mcp_catalog": [],
        "target_tool_outcomes": [],
        "target_scheduled_batches": [],
        "executed_tool_fingerprints": [],
        "executed_tool_call_count": 0,
        "graph_path": [],
        "workflow_engine": LANGGRAPH_ENGINE,
    }
    with langfuse_span(
        "customer_service.question",
        root=True,
        kind="chain",
        generation_id=generation_id,
        attributes={"langfuse.trace.metadata.generation_id": generation_id},
    ) as span:
        if span is not None and turn_context:
            for key in (
                "restoredFrom", "historyMessages", "trimmedMessages", "recalledMessages",
                "historyTokensEstimated", "progressMessages", "progressUnavailable",
                "ambiguous", "inheritedFields", "assemblyMs",
            ):
                value = turn_context.metadata.get(key)
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"langfuse.trace.metadata.context_{key}", value)
        try:
            result = await workflow.run(state)
        finally:
            if span is not None and first_chunk_ms is not None:
                span.set_attribute("langfuse.trace.metadata.first_chunk_ms", first_chunk_ms)
        answer = str(result.get("final_answer") or result.get("draft_answer") or "")
        if span is not None:
            for key, value in (result.get("context_shadow_metrics") or {}).items():
                span.set_attribute(f"langfuse.trace.metadata.context_shadow_{key}", value)
        references = dict(result.get("references") or {})
        decision = result.get("routing_decision") or {}
        observation_output(span, {
            "agents": decision.get("selectedAgents") or [],
            "status": "COMPLETED",
            "routingRules": decision.get("matchedRules") or [],
            "graphPath": result.get("graph_path") or [],
            "qualityGateAction": result.get("quality_gate_action"),
            "qualityGates": {
                name: {
                    **{key: bool(item.get(key)) for key in ("passed", "filtered", "repaired")},
                    "ruleCodes": [
                        code for code in (
                            "answer_contains_credential",
                            "credential_example_output_removed",
                            "unsupported_personal_rate_limit_claim",
                            "unsupported_unanchored_diagnostic_query_claim",
                            "high_risk_without_handoff",
                            "unsafe_business_promise",
                        )
                        if code in (item.get("warnings") or [])
                    ],
                }
                for name, item in (result.get("quality_gate_results") or {}).items()
            },
            "handoffAttempted": bool(result.get("handoff_attempted")),
            "handoffSuccess": bool(result.get("handoff_success")),
            "answerChars": len(answer),
            "citationCount": len(references),
        })
        return answer, references
