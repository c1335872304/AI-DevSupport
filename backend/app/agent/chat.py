from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ConversationMessage, ConversationSession, GenerationState, User
from app.agent.runtime import agent_runtime
from app.agent.llm import llm_service
from app.knowledge.rag import rag_service
from app.agent.trace_store import trace_store
from app.accounting.usage import estimate_tokens, usage_service
from app.accounting.llm_usage import capture_llm_usage
from app.core.observability import observe_generation, trace_span


def self_contained_query(question: str, history: list[dict]) -> str:
    """Cheap contextual rewrite for follow-up questions without an extra LLM call."""
    normalized = question.strip()
    if not history:
        return normalized
    follow_up_markers = ("这个", "那个", "它", "刚才", "上面", "前面", "为什么", "那", "所以", "继续", "呢")
    looks_contextual = len(normalized) <= 40 or any(marker in normalized for marker in follow_up_markers)
    if not looks_contextual:
        return normalized
    previous_user = next(
        (str(item.get("content") or "").strip() for item in reversed(history) if item.get("role") == "user"),
        "",
    )
    if not previous_user:
        return normalized
    return f"上一轮用户问题：{previous_user[-800:]}\n当前追问：{normalized}"


async def ensure_active_conversation(db: AsyncSession, user: User) -> ConversationSession:
    session = await db.scalar(
        select(ConversationSession)
        .where(ConversationSession.user_id == str(user.id), ConversationSession.status == "ACTIVE")
        .order_by(ConversationSession.updated_at.desc())
    )
    if session:
        return session
    session = ConversationSession(conversation_id=uuid.uuid4().hex, user_id=str(user.id), title="新对话")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def stream_chat(db: AsyncSession, user: User, question: str, send_json, generation_id: str | None = None) -> None:
    settings = get_settings()
    await usage_service.ensure_llm_balance(user, settings.llm_minimum_balance_tokens)
    conversation = await ensure_active_conversation(db, user)
    generation_id = generation_id or uuid.uuid4().hex
    generation_started = time.monotonic()
    first_token_ms: float | None = None
    now = datetime.utcnow()
    generation = GenerationState(
        generation_id=generation_id,
        conversation_id=conversation.conversation_id,
        user_id=str(user.id),
        question=question,
        status="PENDING",
    )
    db.add(generation)
    user_message = ConversationMessage(
        conversation_id=conversation.conversation_id,
        user_id=str(user.id),
        role="user",
        content=question,
        generation_id=generation_id,
    )
    db.add(user_message)
    if conversation.title == "新对话":
        conversation.title = question[:40]
    conversation.last_message_at = now
    await db.commit()

    await send_json(
        {
            "type": "start",
            "generationId": generation_id,
            "conversationId": conversation.conversation_id,
            "timestamp": int(now.timestamp() * 1000),
        }
    )

    try:
        generation.status = "STREAMING"
        await db.commit()

        history_rows = list(
            (
                await db.scalars(
                    select(ConversationMessage)
                    .where(
                        ConversationMessage.conversation_id == conversation.conversation_id,
                        ConversationMessage.user_id == str(user.id),
                        ConversationMessage.id < user_message.id,
                    )
                    .order_by(ConversationMessage.id.desc())
                    .limit(max(0, settings.conversation_history_messages))
                )
            ).all()
        )
        history_rows.reverse()
        history: list[dict] = []
        remaining_history_chars = max(0, settings.conversation_history_chars)
        for item in reversed(history_rows):
            if remaining_history_chars <= 0:
                break
            content = item.content[-remaining_history_chars:]
            history.append({"role": item.role, "content": content})
            remaining_history_chars -= len(content)
        history.reverse()

        content = ""
        last_checkpoint_at = time.monotonic()
        chars_since_checkpoint = 0

        async def emit_chunk(chunk: str) -> None:
            nonlocal content, last_checkpoint_at, chars_since_checkpoint, first_token_ms
            if first_token_ms is None:
                first_token_ms = (time.monotonic() - generation_started) * 1000.0
            content += chunk
            chars_since_checkpoint += len(chunk)
            await send_json({"type": "chunk", "chunk": chunk, "generationId": generation_id})

            now_monotonic = time.monotonic()
            checkpoint_due = (
                chars_since_checkpoint >= max(1, settings.chat_checkpoint_chars)
                or now_monotonic - last_checkpoint_at >= max(0.1, settings.chat_checkpoint_seconds)
            )
            if checkpoint_due:
                # Another replica may have processed a stop command. Refresh the durable
                # status before checkpointing so cancellation is not limited to one process.
                await db.refresh(generation, attribute_names=["status"])
                if generation.status == "CANCELLED":
                    raise asyncio.CancelledError
                generation.content = content
                await db.commit()
                chars_since_checkpoint = 0
                last_checkpoint_at = now_monotonic

        with trace_span("agent.generation", {"generation.id": generation_id, "user.id": str(user.id)}), capture_llm_usage() as usage_meter:
            if settings.agent_enabled:
                # The model sees tool schemas and chooses tool calls itself. Calls emitted
                # in the same turn are executed concurrently by AgentRuntime.
                agent_content, refs = await agent_runtime.run(
                    user=user,
                    question=question,
                    history=history,
                    generation_id=generation_id,
                    send_json=send_json,
                    on_chunk=emit_chunk,
                )
                # Normally emit_chunk has already built the same content. Keep the runtime
                # result authoritative if a provider emitted an unusual empty stream.
                if not content and agent_content:
                    content = agent_content
            else:
                # Compatibility path for deployments that deliberately disable Agent mode.
                tool_call_id = f"search-{generation_id}"
                await send_json(
                    {
                        "type": "tool_call",
                        "toolCallId": tool_call_id,
                        "tool": "search_knowledge",
                        "status": "executing",
                        "generationId": generation_id,
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    }
                )
                retrieval_query = self_contained_query(question, history)
                contexts = await rag_service.search(db, user, retrieval_query)
                await send_json(
                    {
                        "type": "tool_call",
                        "toolCallId": tool_call_id,
                        "tool": "search_knowledge",
                        "status": "success",
                        "generationId": generation_id,
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    }
                )
                refs = {
                    str(i): {
                        "fileMd5": item["fileMd5"],
                        "fileName": item["fileName"],
                        "pageNumber": item.get("pageNumber"),
                        "chunkId": item.get("chunkId"),
                    }
                    for i, item in enumerate(contexts, start=1)
                }
                async for chunk in llm_service.stream_answer(question, contexts, history):
                    await emit_chunk(chunk)

        generation.content = content
        generation.status = "COMPLETED"
        generation.reference_mappings_json = json.dumps(refs, ensure_ascii=False)
        db.add(
            ConversationMessage(
                conversation_id=conversation.conversation_id,
                user_id=str(user.id),
                role="assistant",
                content=content,
                generation_id=generation_id,
                reference_mappings_json=json.dumps(refs, ensure_ascii=False),
            )
        )
        conversation.last_message_at = datetime.utcnow()
        await db.commit()
        # Provider-independent accounting: until a provider exposes exact streaming
        # usage, charge a deterministic conservative estimate and record it in the ledger.
        fallback_tokens = estimate_tokens(question) + sum(estimate_tokens(str(x.get("content") or "")) for x in history) + estimate_tokens(content)
        charged_tokens = usage_meter.total_tokens or fallback_tokens
        accounting_mode = "provider_usage" if usage_meter.total_tokens else "estimated_usage"
        await usage_service.charge_llm(db, int(user.id), charged_tokens, "chat_generation", f"{generation_id}:{accounting_mode}")
        observe_generation(
            "COMPLETED",
            duration_ms=(time.monotonic() - generation_started) * 1000.0,
            first_token_ms=first_token_ms,
            tokens=charged_tokens,
            token_mode=accounting_mode,
        )
        await send_json(
            {
                "type": "completion",
                "status": "finished",
                "generationId": generation_id,
                "conversationId": conversation.conversation_id,
                "referenceMappings": refs,
            }
        )
    except asyncio.CancelledError:
        await db.rollback()
        await trace_store.cancel(generation_id)
        generation = await db.get(GenerationState, generation_id)
        if generation and generation.status != "CANCELLED":
            generation.status = "CANCELLED"
            generation.error = "Generation cancelled"
            await db.commit()
        observe_generation(
            "CANCELLED",
            duration_ms=(time.monotonic() - generation_started) * 1000.0,
            first_token_ms=first_token_ms,
        )
        raise
    except Exception as exc:
        await db.rollback()
        await trace_store.fail(generation_id, str(exc))
        generation = await db.get(GenerationState, generation_id)
        if generation:
            generation.status = "FAILED"
            observe_generation(
                "FAILED",
                duration_ms=(time.monotonic() - generation_started) * 1000.0,
                first_token_ms=first_token_ms,
            )
            generation.error = str(exc)
            await db.commit()
        try:
            await send_json({"code": 500, "error": str(exc), "generationId": generation_id})
        except Exception:
            pass
