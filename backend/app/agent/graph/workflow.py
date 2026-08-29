from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING

from app.agent.graph.engine import END, START, LANGGRAPH_ENGINE, StateGraph
from app.agent.graph.routes import route_after_agent
from app.agent.graph.state import CustomerServiceState
from app.agent.llm import llm_service
from app.agent.trace_store import trace_store
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.router import skill_router
from app.skill_runtime.trace import SkillTrace

if TYPE_CHECKING:
    from app.agent.runtime import AgentRuntime, ChunkCallback, SendJson
    from app.db.models import User
    from app.tools.base import ToolResult


_HANDOFF_SUCCESS_PATTERNS = (
    "已创建人工工单",
    "已经创建人工工单",
    "已成功创建人工工单",
    "已成功转人工",
    "已经转接人工",
    "已为您转接人工",
)


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

    async def _mark_node(self, state: CustomerServiceState, node: str) -> list[str]:
        path = list(state.get("graph_path") or [])
        path.append(node)
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
            "references": dict(state.get("references") or {}),
            "content_parts": list(state.get("content_parts") or []),
            "step": int(state.get("step") or 0),
            "max_steps": max(1, self.runtime.settings.agent_max_steps),
            "graph_path": path,
            "workflow_engine": LANGGRAPH_ENGINE,
        }

    async def skill_route(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "skill_route")
        active_skills = list(dict.fromkeys(skill_router.route(state["question"])))
        trace = SkillTrace(
            question=state["question"],
            initial_skills=list(active_skills),
            active_skills=list(active_skills),
        )
        catalog = skill_registry.catalog_prompt()
        skill_context = skill_registry.build_prompt(active_skills) if active_skills else ""
        messages = llm_service.build_agent_messages(
            state["question"],
            state.get("history") or [],
            skill_catalog=catalog,
            skill_context=skill_context,
        )
        await trace_store.begin(state["generation_id"], str(self.user.id), state["question"], active_skills)
        if active_skills:
            await self.send_json(
                {
                    "type": "skill_selected",
                    "skills": active_skills,
                    "generationId": state["generation_id"],
                    "timestamp": int(time.time() * 1000),
                }
            )
        return {
            "active_skills": active_skills,
            "skill_catalog": catalog,
            "skill_trace": trace,
            "messages": messages,
            "graph_path": path,
        }

    async def agent_decide(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "agent_decide")
        step = int(state.get("step") or 0)
        max_steps = int(state.get("max_steps") or max(1, self.runtime.settings.agent_max_steps))
        if step >= max_steps:
            return {"next_action": "force_finalize", "tool_calls": [], "turn_chunks": [], "graph_path": path}

        messages = list(state.get("messages") or [])
        tool_calls = []
        turn_chunks: list[str] = []
        tools = self.runtime.llm_tools_for_skills(state.get("active_skills") or [])
        async for event in llm_service.stream_agent_turn(messages, tools):
            if event["type"] == "content":
                chunk = str(event.get("content") or "")
                if chunk:
                    # Buffer until the turn ends: providers can emit a prose preamble
                    # before tool_calls. That prose belongs to the canonical assistant
                    # tool message, not the customer-visible answer.
                    turn_chunks.append(chunk)
            elif event["type"] == "tool_calls":
                tool_calls = list(event.get("tool_calls") or [])

        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(turn_chunks) or None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments, ensure_ascii=False),
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            action = "handoff" if any(call.name == "create_support_handoff" for call in tool_calls) else "execute_tools"
            return {
                "messages": messages,
                "tool_calls": tool_calls,
                "turn_chunks": turn_chunks,
                "next_action": action,
                "graph_path": path,
            }

        if turn_chunks:
            content_parts = list(state.get("content_parts") or []) + turn_chunks
            text = "".join(content_parts)
            return {
                "content_parts": content_parts,
                "draft_answer": text,
                "final_chunks": list(turn_chunks),
                "next_action": "safety",
                "tool_calls": [],
                "turn_chunks": turn_chunks,
                "graph_path": path,
            }

        fallback = "暂无相关信息。模型本轮没有生成可执行工具调用或回答。"
        content_parts = list(state.get("content_parts") or []) + [fallback]
        return {
            "content_parts": content_parts,
            "draft_answer": "".join(content_parts),
            "final_chunks": [fallback],
            "next_action": "safety",
            "tool_calls": [],
            "turn_chunks": [],
            "graph_path": path,
        }

    async def _execute_batch(self, state: CustomerServiceState, *, node_name: str) -> dict:
        path = await self._mark_node(state, node_name)
        calls = list(state.get("tool_calls") or [])
        active_skills = list(state.get("active_skills") or [])
        messages = list(state.get("messages") or [])
        references = dict(state.get("references") or {})
        trace = state["skill_trace"]
        step = int(state.get("step") or 0)

        results = await self.runtime._execute_parallel(
            calls=calls,
            user=self.user,
            generation_id=state["generation_id"],
            send_json=self.send_json,
            step=step,
            active_skills=frozenset(active_skills),
        )

        skills_changed = False
        handoff_attempted = bool(state.get("handoff_attempted"))
        handoff_success = bool(state.get("handoff_success"))
        handoff_id = state.get("handoff_id")
        for call, result in zip(calls, results, strict=True):
            if call.name == "activate_skill" and result.status == "SUCCESS" and isinstance(result.data, dict):
                skill_name = str(result.data.get("skill") or "")
                if skill_name and skill_name not in active_skills:
                    replace_skill = str(result.data.get("replaceSkill") or "").strip()
                    if replace_skill and replace_skill in active_skills:
                        active_skills.remove(replace_skill)
                        trace.deactivate(replace_skill, reason=f"replaced-by:{skill_name}")
                    if len(active_skills) >= max(1, self.runtime.settings.skills_max_active):
                        result.status = "DENIED"
                        result.error = "maximum active skill count reached"
                        result.data = None
                    else:
                        active_skills.append(skill_name)
                        trace.activate(skill_name, dynamic=True)
                        block = skill_registry.build_prompt([skill_name])
                        if block:
                            messages[0]["content"] += (
                                "\n\n以下客服 Specialist Skill 已由 Agent 在本轮动态激活：\n\n" + block
                            )
                        skills_changed = True

            if call.name == "create_support_handoff":
                handoff_attempted = True
                if result.status == "SUCCESS" and isinstance(result.data, dict):
                    handoff_success = True
                    handoff_id = str(result.data.get("handoffId") or result.data.get("id") or "") or None

            self.runtime._collect_references(call, result, references)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": self.runtime.registry.serialize_result_for_model(result),
                }
            )

        trace.record_batch(step, calls, results)
        if skills_changed:
            await self.send_json(
                {
                    "type": "skill_selected",
                    "skills": active_skills,
                    "generationId": state["generation_id"],
                    "timestamp": int(time.time() * 1000),
                }
            )
        return {
            "messages": messages,
            "active_skills": active_skills,
            "references": references,
            "skill_trace": trace,
            "step": step + 1,
            "tool_calls": [],
            "turn_chunks": [],
            "handoff_attempted": handoff_attempted,
            "handoff_success": handoff_success,
            "handoff_id": handoff_id,
            "graph_path": path,
        }

    async def execute_tools(self, state: CustomerServiceState) -> dict:
        return await self._execute_batch(state, node_name="execute_tools")

    async def handoff(self, state: CustomerServiceState) -> dict:
        # Handoff is intentionally visible as a first-class graph stage for customer
        # service observability. The actual write still goes through ToolRegistry, so it
        # keeps schema validation, permission checks, timeout and durable Tool trace.
        return await self._execute_batch(state, node_name="handoff")

    async def force_finalize(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "force_finalize")
        content_parts = list(state.get("content_parts") or [])
        final_chunks: list[str] = []
        messages = list(state.get("messages") or [])
        async for chunk in llm_service.stream_messages(messages, force_no_tools=True):
            content_parts.append(chunk)
            final_chunks.append(chunk)
        if not content_parts:
            text = "工具调用达到最大轮数，未能生成最终回答。"
            content_parts.append(text)
            final_chunks.append(text)
        return {
            "content_parts": content_parts,
            "draft_answer": "".join(content_parts),
            "final_chunks": final_chunks,
            "graph_path": path,
        }

    async def safety(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "safety")
        answer = str(state.get("draft_answer") or "").strip()
        if not answer:
            answer = "当前信息不足，暂时无法安全确认该问题。"

        # Runtime-level transactional guard: a model may only claim a successful human
        # handoff after the real write Tool returned SUCCESS. This complements the system
        # prompt with a deterministic customer-service safety boundary.
        changed = answer != str(state.get("draft_answer") or "").strip()
        if not state.get("handoff_success"):
            claimed = any(token in answer for token in _HANDOFF_SUCCESS_PATTERNS)
            if claimed:
                for token in _HANDOFF_SUCCESS_PATTERNS:
                    answer = answer.replace(token, "人工工单尚未确认创建成功")
                if state.get("handoff_attempted"):
                    answer += "\n\n当前人工转接操作未确认成功，请稍后重试或使用其他官方人工渠道。"
                changed = True
        return {
            "final_answer": answer,
            "final_chunks": [answer] if changed else list(state.get("final_chunks") or [answer]),
            "graph_path": path,
        }

    async def emit_final(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "emit_final")
        chunks = list(state.get("final_chunks") or [])
        if not chunks:
            chunks = [str(state.get("final_answer") or "")]
        for chunk in chunks:
            if chunk:
                await self.on_chunk(chunk)
        return {"graph_path": path}

    async def persist_trace(self, state: CustomerServiceState) -> dict:
        path = await self._mark_node(state, "persist_trace")
        trace = state["skill_trace"]
        active_skills = list(state.get("active_skills") or [])
        summary = trace.summary()
        recommended_gates: list[str] = []
        for skill_name in active_skills:
            skill = skill_registry.get(skill_name)
            if skill and skill.quality_gate and skill.quality_gate not in recommended_gates:
                recommended_gates.append(skill.quality_gate)
        used_scripts = set(summary.get("scriptsUsed") or [])
        missing_gates = [gate for gate in recommended_gates if gate not in used_scripts]
        summary.update(
            {
                "qualityGatesRecommended": recommended_gates,
                "qualityGatesUsed": [gate for gate in recommended_gates if gate in used_scripts],
                "qualityGatesMissing": missing_gates,
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
            }
        )
        await trace_store.complete(state["generation_id"], active_skills, summary)
        await self.send_json(
            {
                "type": "skill_trace",
                "status": "trace",
                "generationId": state["generation_id"],
                "trace": summary,
                "timestamp": int(time.time() * 1000),
            }
        )
        return {"trace_summary": summary, "graph_path": path}

    def compile(self):
        graph = StateGraph(CustomerServiceState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("skill_route", self.skill_route)
        graph.add_node("agent_decide", self.agent_decide)
        graph.add_node("execute_tools", self.execute_tools)
        graph.add_node("handoff", self.handoff)
        graph.add_node("force_finalize", self.force_finalize)
        graph.add_node("safety", self.safety)
        graph.add_node("emit_final", self.emit_final)
        graph.add_node("persist_trace", self.persist_trace)

        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "skill_route")
        graph.add_edge("skill_route", "agent_decide")
        graph.add_conditional_edges(
            "agent_decide",
            route_after_agent,
            {
                "execute_tools": "execute_tools",
                "handoff": "handoff",
                "force_finalize": "force_finalize",
                "safety": "safety",
            },
        )
        graph.add_edge("execute_tools", "agent_decide")
        graph.add_edge("handoff", "agent_decide")
        graph.add_edge("force_finalize", "safety")
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
    generation_id: str,
    send_json: "SendJson",
    on_chunk: "ChunkCallback",
) -> tuple[str, dict[str, dict]]:
    workflow = CustomerServiceWorkflow(runtime=runtime, user=user, send_json=send_json, on_chunk=on_chunk)
    state: CustomerServiceState = {
        "question": question,
        "history": history,
        "generation_id": generation_id,
        "references": {},
        "content_parts": [],
        "step": 0,
        "handoff_attempted": False,
        "handoff_success": False,
        "handoff_id": None,
        "graph_path": [],
        "workflow_engine": LANGGRAPH_ENGINE,
    }
    result = await workflow.run(state)
    return str(result.get("final_answer") or result.get("draft_answer") or ""), dict(result.get("references") or {})
