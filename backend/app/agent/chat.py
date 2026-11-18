from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redaction import redact_text
from app.core.time import utcnow
from app.db.models import ConversationMessage, ConversationSession, GenerationState, User
from app.agent.runtime import agent_runtime
from app.agent.generation import generation_runtime
from app.agent.llm import llm_service
from app.agent.memory import conversation_memory
from app.agent.continuation import assemble_turn
from app.knowledge.rag import rag_service
from app.accounting.usage import estimate_tokens, usage_service
from app.accounting.llm_usage import capture_llm_usage

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


async def ensure_active_conversation(db: AsyncSession, user: User, conversation_id: str | None = None) -> ConversationSession:
    if conversation_id is not None:
        conversation = await db.get(ConversationSession, conversation_id)
        if not conversation or conversation.user_id != str(user.id) or conversation.status != "ACTIVE":
            raise HTTPException(404, "Active conversation not found")
        return conversation
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


async def stream_chat(db: AsyncSession, user: User, question: str, send_json, generation_id: str | None = None, conversation_id: str | None = None) -> None:
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
    conversation = await ensure_active_conversation(db, user, conversation_id)
    generation_id = generation_id or uuid.uuid4().hex
    logger.info("[GEN %s] conversation ready conversation=%s", _gid(generation_id), conversation.conversation_id)
    _console(f"[GEN {_gid(generation_id)}] stage=conversation_ready conversation={conversation.conversation_id[:8]}")
    remembered_entities = {}
    if not settings.context_system_enabled:
        redis_entities = await conversation_memory.get_entities(conversation.conversation_id)
        try:
            remembered_entities = redis_entities if redis_entities is not None else json.loads(conversation.collected_entities_json or "{}")
            if not isinstance(remembered_entities, dict):
                remembered_entities = {}
        except (TypeError, json.JSONDecodeError):
            remembered_entities = {}
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

    heartbeat = asyncio.create_task(generation_runtime.heartbeat(generation_id))
    content = ""
    try:
        started = await db.execute(update(GenerationState).where(
            GenerationState.generation_id == generation_id, GenerationState.status == "PENDING",
        ).values(status="STREAMING"))
        if not started.rowcount:
            raise asyncio.CancelledError
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

        turn_context = None
        shadow_context = None
        if settings.context_system_enabled or settings.context_shadow_enabled:
            from app.db.session import SessionLocal

            context_started = time.monotonic()
            if settings.context_system_enabled:
                async with SessionLocal() as context_db:
                    turn_context = await assemble_turn(context_db, user_message, settings)
                turn_context.metadata["assemblyMs"] = round((time.monotonic() - context_started) * 1000, 2)
            else:
                try:
                    async with asyncio.timeout(0.75), SessionLocal() as context_db:
                        shadow_context = await assemble_turn(context_db, user_message, settings)
                    shadow_context.metadata["assemblyMs"] = round((time.monotonic() - context_started) * 1000, 2)
                except Exception as exc:
                    logger.warning("[CONTEXT] shadow unavailable: %s", type(exc).__name__)
                    await send_json({"type": "context_shadow", "generationId": generation_id,
                                     "status": "unavailable"})
        if turn_context:
            history = turn_context.history
            remembered_entities = turn_context.entities if turn_context.continuing else {}
            history_source = turn_context.metadata.get("restoredFrom", "database")
            await send_json({"type": "context_assembled", "generationId": generation_id, **turn_context.metadata})
        else:
            history = await load_database_history()
            history_source = "database"
            await conversation_memory.replace_history(conversation.conversation_id, history)
            await conversation_memory.append_message(conversation.conversation_id, "user", question)
        logger.info("[GEN %s] history ready source=%s messages=%d", _gid(generation_id), history_source, len(history))
        _console(f"[GEN {_gid(generation_id)}] stage=history_ready source={history_source} messages={len(history)}")
        reservation_tokens = max(
            1,
            estimate_tokens(question)
            + sum(estimate_tokens(str(item.get("content") or "")) for item in history)
            + sum(estimate_tokens(item["text"]) for item in (
                [*turn_context.recall, *(turn_context.progress or [])] if turn_context else ()
            ))
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
            await db.execute(update(GenerationState).where(
                GenerationState.generation_id == generation_id,
                GenerationState.status.in_(("PENDING", "STREAMING")),
            ).values(status="FAILED", error=str(exc.detail)))
            await db.commit()
            await send_json({"code": exc.status_code, "error": str(exc.detail), "generationId": generation_id})
            return

        content = ""
        last_checkpoint_at = time.monotonic()
        chars_since_checkpoint = 0

        async def emit_chunk(chunk: str) -> None:
            nonlocal content, last_checkpoint_at, chars_since_checkpoint
            chunk = redact_text(chunk)
            if not chunk:
                return
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
                checkpoint = await db.execute(update(GenerationState).where(
                    GenerationState.generation_id == generation_id, GenerationState.status == "STREAMING",
                ).values(content=content))
                if not checkpoint.rowcount:
                    raise asyncio.CancelledError
                await db.commit()
                chars_since_checkpoint = 0
                last_checkpoint_at = now_monotonic

        with capture_llm_usage() as usage_meter:
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
                        turn_context=turn_context,
                        shadow_context=shadow_context,
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
            # The final gate is authoritative even if it replaced an already
            # approved prefix after citation normalization or evidence expiry.
            content = redact_text(agent_content)
        # Commit the debit, answer and completion together before announcing success.
        fallback_tokens = estimate_tokens(question) + sum(estimate_tokens(str(x.get("content") or "")) for x in history) + estimate_tokens(content)
        charged_tokens = usage_meter.total_tokens or fallback_tokens
        accounting_mode = "provider_usage" if usage_meter.total_tokens else "estimated_usage"
        completed = await db.execute(update(GenerationState).where(
            GenerationState.generation_id == generation_id, GenerationState.status == "STREAMING",
        ).values(status="COMPLETED", content=content,
                 reference_mappings_json=json.dumps(refs, ensure_ascii=False)))
        if not completed.rowcount:
            raise asyncio.CancelledError
        if reservation_active:
            charged_tokens = await usage_service.settle_llm(
                db, generation_id, charged_tokens, "chat_generation", commit=False,
            )
        else:
            charged_tokens = await usage_service.charge_llm(
                db, int(user.id), charged_tokens, "chat_generation", f"{generation_id}:{accounting_mode}"
            )
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
        reservation_active = False
        if not settings.context_system_enabled:
            await conversation_memory.append_message(conversation.conversation_id, "assistant", content)
        logger.info("[GEN %s] completed chars=%d refs=%d", _gid(generation_id), len(content), len(refs))
        _console(f"[GEN {_gid(generation_id)}] status=COMPLETED chars={len(content)} refs={len(refs)}")
        await send_json(
            {
                "type": "completion",
                "status": "finished",
                "generationId": generation_id,
                "conversationId": conversation.conversation_id,
                "referenceMappings": refs,
                "content": content,
            }
        )
    except asyncio.CancelledError:
        logger.warning("[GEN %s] cancelled", _gid(generation_id))
        _console(f"[GEN {_gid(generation_id)}] status=CANCELLED")
        await db.rollback()
        cancelled = await db.execute(update(GenerationState).where(
            GenerationState.generation_id == generation_id,
            GenerationState.status.in_(("PENDING", "STREAMING", "CANCELLED")),
        ).values(status="CANCELLED", content=content, error="Generation cancelled"))
        if cancelled.rowcount:
            if reservation_active:
                await usage_service.release_llm(db, generation_id, "cancelled_generation", commit=False)
            await db.commit()
        raise
    except Exception as exc:
        logger.exception("[GEN %s] failed error=%s", _gid(generation_id), exc)
        _console(f"[GEN {_gid(generation_id)}] status=FAILED error={exc}")
        await db.rollback()
        failed = await db.execute(update(GenerationState).where(
            GenerationState.generation_id == generation_id,
            GenerationState.status.in_(("PENDING", "STREAMING")),
        ).values(status="FAILED", content=content, error=str(exc)))
        if failed.rowcount:
            if reservation_active:
                await usage_service.release_llm(db, generation_id, "failed_generation", commit=False)
            await db.commit()
        try:
            await send_json({"code": 500, "error": "回答生成中断，请重试；已显示的内容尚未构成完整答复。",
                             "generationId": generation_id})
        except Exception:
            pass
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
