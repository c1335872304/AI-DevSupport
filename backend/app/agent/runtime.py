from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from app.agent.types import AgentToolCall
from app.core.config import get_settings
from app.core.redaction import redact_data
from app.db.models import User
from app.agent.trace_store import trace_store
from app.skill_runtime.registry import skill_registry
from app.tools.base import ToolExecutionContext, ToolResult
from app.tools.registry import ToolRegistry, tool_registry

logger = logging.getLogger(__name__)


def _console(message: str) -> None:
    print(message, flush=True)

SendJson = Callable[[dict], Awaitable[None]]
ChunkCallback = Callable[[str], Awaitable[None]]


class AgentRuntime:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or tool_registry
        self.settings = get_settings()

    async def run(
        self,
        *,
        user: User,
        question: str,
        history: list[dict],
        conversation_id: str | None = None,
        entity_memory: dict[str, str] | None = None,
        generation_id: str,
        send_json: SendJson,
        on_chunk: ChunkCallback,
    ) -> tuple[str, dict[str, dict]]:
        """Run one customer-service request through the LangGraph workflow.

        LangGraph owns state transitions and workflow routing. Tool execution remains in
        this runtime so the existing concurrency, permission, timeout and trace behavior
        is reused unchanged.
        """
        from app.agent.graph.workflow import run_customer_service_graph

        return await run_customer_service_graph(
            runtime=self,
            user=user,
            question=question,
            history=history,
            conversation_id=conversation_id,
            entity_memory=entity_memory,
            generation_id=generation_id,
            send_json=send_json,
            on_chunk=on_chunk,
        )

    def llm_tools_for_skills(self, active_skills: list[str]) -> list[dict]:
        """Return the Tool schemas visible to the LLM for the current Skill set."""
        if active_skills:
            allowed_tool_names: set[str] = {"activate_skill"}
            for skill_name in active_skills:
                skill = skill_registry.get(skill_name)
                if skill:
                    allowed_tool_names.update(skill.allowed_tools)
            # Dynamically discovered read-only MCP tools remain available while a
            # customer-service Skill is active. Write MCP tools require explicit Skill
            # allowlisting so activating a Skill never widens write permissions.
            for tool_name in self.registry.names():
                tool = self.registry.get(tool_name)
                if tool_name.startswith("mcp__") and tool and tool.read_only:
                    allowed_tool_names.add(tool_name)
            filtered = self.registry.llm_tools(allowed_tool_names)
            if filtered:
                return filtered
        return self.registry.llm_tools(
            name
            for name in self.registry.names()
            if name not in {"read_skill_reference", "run_skill_script"}
        )

    async def _execute_parallel(
        self,
        *,
        calls: list[AgentToolCall],
        user: User,
        generation_id: str,
        send_json: SendJson,
        step: int,
        active_skills: frozenset[str],
    ) -> list[ToolResult]:
        semaphore = asyncio.Semaphore(max(1, self.settings.agent_max_parallel_tools))
        resource_locks: dict[str, asyncio.Lock] = {}

        async def execute_one(call: AgentToolCall) -> ToolResult:
            tool = self.registry.get(call.name)
            event_id = call.id or f"tool-{uuid.uuid4().hex}"
            started = time.monotonic()
            logger.info("[GEN %s] tool start name=%s step=%d", generation_id[:8], call.name, step + 1)
            _console(f"[GEN {generation_id[:8]}] tool_start name={call.name} step={step + 1}")
            await send_json(
                {
                    "type": "tool_call",
                    "toolCallId": event_id,
                    "tool": call.name,
                    "status": "executing",
                    "arguments": redact_data(call.arguments),
                    "agent": call.source_agent,
                    "skill": call.source_skill,
                    "agentStep": step + 1,
                    "generationId": generation_id,
                    "timestamp": int(time.time() * 1000),
                }
            )
            async with semaphore:
                context = ToolExecutionContext(
                    user=user,
                    generation_id=generation_id,
                    active_skills=active_skills,
                )
                allowed_by_skill = not active_skills
                if active_skills:
                    allowed_names = {"activate_skill"}
                    for skill_name in active_skills:
                        skill = skill_registry.get(skill_name)
                        if skill:
                            allowed_names.update(skill.allowed_tools)
                    allowed_by_skill = call.name in allowed_names or bool(tool and call.name.startswith("mcp__") and tool.read_only)
                # Specialist-generated calls carry their owning Skill. Enforce that
                # narrower boundary even when several specialists are active at once.
                if call.source_skill:
                    owner = skill_registry.get(call.source_skill)
                    owner_allowed = bool(owner and call.name in owner.allowed_tools)
                    if tool and call.name.startswith("mcp__") and tool.read_only:
                        owner_allowed = True
                    allowed_by_skill = allowed_by_skill and owner_allowed
                if not allowed_by_skill:
                    result = ToolResult(status="DENIED", error=f"Tool {call.name} is not allowed by active Skill", duration_ms=0)
                elif tool and (not tool.parallel_safe or not tool.read_only):
                    # Unsafe/write tools sharing a resource group serialize with each
                    # other. Pure read tools remain fully parallel even when they read
                    # from the same knowledge subsystem.
                    lock_key = tool.resource_group or tool.name
                    lock = resource_locks.setdefault(lock_key, asyncio.Lock())
                    async with lock:
                        result = await self.registry.execute(call.name, call.arguments, context)
                else:
                    result = await self.registry.execute(call.name, call.arguments, context)
            ui_status = "success" if result.status == "SUCCESS" else "failed"
            logger.info("[GEN %s] tool end name=%s status=%s duration_ms=%d", generation_id[:8], call.name, result.status, int((time.monotonic() - started) * 1000))
            _console(f"[GEN {generation_id[:8]}] tool_end name={call.name} status={result.status} duration_ms={int((time.monotonic() - started) * 1000)}")
            await trace_store.tool(generation_id, event_id, call.name, step + 1, call.arguments, result)
            await send_json(
                {
                    "type": "tool_call",
                    "toolCallId": event_id,
                    "tool": call.name,
                    "status": ui_status,
                    "resultStatus": result.status,
                    "durationMs": result.duration_ms,
                    "error": redact_data(result.error),
                    "agent": call.source_agent,
                    "skill": call.source_skill,
                    "agentStep": step + 1,
                    "generationId": generation_id,
                    "timestamp": int(time.time() * 1000),
                }
            )
            return result

        # Calls emitted in the same model turn have no declared data dependency. Execute
        # them concurrently. A later model turn can consume all results and express the
        # next dependency dynamically.
        return list(await asyncio.gather(*(execute_one(call) for call in calls)))

    @staticmethod
    def _collect_references(call: AgentToolCall, result: ToolResult, refs: dict[str, dict]) -> None:
        if result.status != "SUCCESS" or not isinstance(result.data, dict):
            return
        if call.name == "get_document" and result.data.get("fileMd5"):
            item = result.data
            key = (str(item.get("fileMd5") or ""), item.get("chunkId"), item.get("pageNumber"))
            for number, existing in refs.items():
                if (existing.get("fileMd5"), existing.get("chunkId"), existing.get("pageNumber")) == key:
                    item["referenceNumber"] = int(number)
                    return
            number = str(len(refs) + 1)
            refs[number] = {
                "fileMd5": item.get("fileMd5"),
                "fileName": item.get("fileName"),
                "pageNumber": item.get("pageNumber"),
                "chunkId": item.get("chunkId"),
            }
            item["referenceNumber"] = int(number)
            return
        if call.name != "search_knowledge":
            return
        for item in result.data.get("results") or []:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("fileMd5") or ""), item.get("chunkId"), item.get("pageNumber"))
            if not key[0]:
                continue
            existing_number = next(
                (
                    number
                    for number, value in refs.items()
                    if (value.get("fileMd5"), value.get("chunkId"), value.get("pageNumber")) == key
                ),
                None,
            )
            if existing_number is not None:
                item["referenceNumber"] = int(existing_number)
                continue
            number = str(len(refs) + 1)
            refs[number] = {
                "fileMd5": item.get("fileMd5"),
                "fileName": item.get("fileName"),
                "pageNumber": item.get("pageNumber"),
                "chunkId": item.get("chunkId"),
            }
            item["referenceNumber"] = int(number)
            page = f" | 第{item.get('pageNumber')}页" if item.get("pageNumber") else ""
            item["citation"] = f"来源#{number}: {item.get('fileName') or item.get('fileMd5')}{page}"


agent_runtime = AgentRuntime()
