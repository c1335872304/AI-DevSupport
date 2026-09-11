from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redaction import redact_text
from app.core.time import utcnow
from app.db.models import ConversationMessage, ConversationSession, GenerationState, User
from app.agent.runtime import agent_runtime
from app.agent.llm import llm_service
from app.agent.memory import conversation_memory
from app.knowledge.rag import rag_service
from app.agent.trace_store import trace_store
from app.accounting.usage import estimate_tokens, usage_service
from app.accounting.llm_usage import capture_llm_usage
from app.core.observability import observe_generation, trace_span

logger = logging.getLogger(__name__)


def _gid(generation_id: str | None) -> str:
    return (generation_id or "-")[:8]


def _console(message: str) -> None:
    print(message, flush=True)


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
    # Keep credentials accidentally pasted into chat out of backend history and
    # model context. The browser already has the original message for display.
    question = redact_text(question)
    logger.info("[GEN %s] start user=%s question_chars=%d workflow=target model=%s", _gid(generation_id), user.id, len(question), settings.llm_model)
    _console(f"[GEN {_gid(generation_id)}] start user={user.id} workflow=target model={settings.llm_model}")
    logger.info("[GEN %s] checking balance", _gid(generation_id))
    _console(f"[GEN {_gid(generation_id)}] stage=checking_balance")
    reservation_active = False
    try:
        await usage_service.ensure_llm_balance(user, settings.llm_minimum_balance_tokens)
    except Exception as exc:
        status_code = int(getattr(exc, "status_code", 500) or 500)
        error = str(getattr(exc, "detail", exc))
        logger.warning("[GEN %s] balance check failed status=%d balance=%s error=%s", _gid(generation_id), status_code, user.llm_token_balance, error)
        _console(f"[GEN {_gid(generation_id)}] status=FAILED stage=checking_balance balance={user.llm_token_balance} error={error}")
        try:
            await send_json({"code": status_code, "error": error, "generationId": generation_id})
        except Exception:
            pass
        return
    logger.info("[GEN %s] balance ok", _gid(generation_id))
    _console(f"[GEN {_gid(generation_id)}] stage=balance_ok")
    conversation = await ensure_active_conversation(db, user)
    generation_id = generation_id or uuid.uuid4().hex
    logger.info("[GEN %s] conversation ready conversation=%s", _gid(generation_id), conversation.conversation_id)
    _console(f"[GEN {_gid(generation_id)}] stage=conversation_ready conversation={conversation.conversation_id[:8]}")
    redis_entities = await conversation_memory.get_entities(conversation.conversation_id)
    if redis_entities is not None:
        remembered_entities = redis_entities
    else:
        try:
            remembered_entities = json.loads(conversation.collected_entities_json or "{}")
            if not isinstance(remembered_entities, dict):
                remembered_entities = {}
        except (TypeError, json.JSONDecodeError):
            remembered_entities = {}
    generation_started = time.monotonic()
    first_token_ms: float | None = None
    now = utcnow()
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
    logger.info("[GEN %s] persisted status=PENDING", _gid(generation_id))
    _console(f"[GEN {_gid(generation_id)}] status=PENDING")

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
        logger.info("[GEN %s] status=STREAMING history_loading", _gid(generation_id))
        _console(f"[GEN {_gid(generation_id)}] status=STREAMING stage=history_loading")

        async def load_database_history() -> list[dict]:
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
            loaded: list[dict] = []
            remaining_history_chars = max(0, settings.conversation_history_chars)
            for item in reversed(history_rows):
                if remaining_history_chars <= 0:
                    break
                content = item.content[-remaining_history_chars:]
                loaded.append({"role": item.role, "content": content})
                remaining_history_chars -= len(content)
            loaded.reverse()
            return loaded

        redis_history = await conversation_memory.get_history(conversation.conversation_id)
        if redis_history is not None:
            redis_window = redis_history[-max(1, settings.memory_history_max):]
            database_history = await load_database_history()
            if redis_window == database_history:
                history = redis_window
                history_source = "redis"
            else:
                # Redis is only a cache.  Reconcile it against durable SQL so a
                # stale, partial, or newly enabled cache cannot lose context.
                history = database_history
                await conversation_memory.replace_history(
                    conversation.conversation_id, database_history
                )
                history_source = "database_reconciled_to_redis"
        else:
            history = await load_database_history()
            history_source = "database"
        logger.info("[GEN %s] history ready source=%s messages=%d", _gid(generation_id), history_source, len(history))
        _console(f"[GEN {_gid(generation_id)}] stage=history_ready source={history_source} messages={len(history)}")
        await conversation_memory.append_message(conversation.conversation_id, "user", question)

        reservation_tokens = max(
            1,
            estimate_tokens(question)
            + sum(estimate_tokens(str(item.get("content") or "")) for item in history)
            + max(256, settings.llm_max_tokens),
        )
        try:
            await usage_service.reserve_llm(
                db, int(user.id), generation_id, reservation_tokens, "chat_generation_reservation"
            )
            reservation_active = True
            logger.info("[GEN %s] token reservation=%d", _gid(generation_id), reservation_tokens)
            _console(f"[GEN {_gid(generation_id)}] stage=token_reserved tokens={reservation_tokens}")
        except HTTPException as exc:
            generation.status = "FAILED"
            generation.error = str(exc.detail)
            await db.commit()
            await send_json({"code": exc.status_code, "error": str(exc.detail), "generationId": generation_id})
            return

        content = ""
        last_checkpoint_at = time.monotonic()
        chars_since_checkpoint = 0

        async def emit_chunk(chunk: str) -> None:
            nonlocal content, last_checkpoint_at, chars_since_checkpoint, first_token_ms
            chunk = redact_text(chunk)
            if not chunk:
                return
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
            # The target Agent graph is the only conversation execution path.
            logger.info("[GEN %s] entering agent workflow", _gid(generation_id))
            _console(f"[GEN {_gid(generation_id)}] stage=agent_workflow")
            # The model sees tool schemas and chooses tool calls itself. Calls emitted
            # in the same turn are executed concurrently by AgentRuntime.
            try:
                agent_content, refs = await asyncio.wait_for(
                    agent_runtime.run(
                        user=user,
                        question=question,
                        history=history,
                        conversation_id=conversation.conversation_id,
                        entity_memory=remembered_entities,
                        generation_id=generation_id,
                        send_json=send_json,
                        on_chunk=emit_chunk,
                    ),
                    timeout=max(1.0, settings.agent_generation_timeout_seconds),
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"agent generation timed out after {settings.agent_generation_timeout_seconds:g}s"
                ) from exc
            # Normally emit_chunk has already built the same content. Keep the runtime
            # result authoritative if a provider emitted an unusual empty stream.
            if not content and agent_content:
                content = redact_text(agent_content)
        # Settle the durable reservation before marking the generation complete. This
        # prevents a successful provider call from being lost when the process crashes
        # before the old post-response charge step.
        fallback_tokens = estimate_tokens(question) + sum(estimate_tokens(str(x.get("content") or "")) for x in history) + estimate_tokens(content)
        charged_tokens = usage_meter.total_tokens or fallback_tokens
        accounting_mode = "provider_usage" if usage_meter.total_tokens else "estimated_usage"
        if reservation_active:
            charged_tokens = await usage_service.settle_llm(
                db, generation_id, charged_tokens, "chat_generation"
            )
            reservation_active = False
        else:
            charged_tokens = await usage_service.charge_llm(
                db, int(user.id), charged_tokens, "chat_generation", f"{generation_id}:{accounting_mode}"
            )
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
        conversation.last_message_at = utcnow()
        await db.commit()
        await conversation_memory.append_message(conversation.conversation_id, "assistant", content)
        logger.info("[GEN %s] completed chars=%d refs=%d", _gid(generation_id), len(content), len(refs))
        _console(f"[GEN {_gid(generation_id)}] status=COMPLETED chars={len(content)} refs={len(refs)}")
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
        logger.warning("[GEN %s] cancelled", _gid(generation_id))
        _console(f"[GEN {_gid(generation_id)}] status=CANCELLED")
        await db.rollback()
        if reservation_active:
            await usage_service.release_llm(db, generation_id, "cancelled_generation")
            reservation_active = False
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
        logger.exception("[GEN %s] failed error=%s", _gid(generation_id), exc)
        _console(f"[GEN {_gid(generation_id)}] status=FAILED error={exc}")
        await db.rollback()
        if reservation_active:
            await usage_service.release_llm(db, generation_id, "failed_generation")
            reservation_active = False
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
