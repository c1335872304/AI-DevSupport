"""Authoritative conversation-scoped context and bounded turn assembly."""

from __future__ import annotations

import asyncio
import json
import hashlib
import re
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.accounting.usage import estimate_tokens
from app.agent.entities import extract_entities, topic_changed
from app.agent.memory import conversation_memory
from app.core.redaction import redact_text
from app.core.content_safety import detect_prompt_injection
from app.db.models import ConversationContextState, ConversationMessage
from app.knowledge.product_scope import named_products
from app.support.billing import requested_billing_month

_ANCHORS = ("request_id", "ticket_id", "invoice_id", "order_id", "transaction_id", "webhook_event_id", "app_id")
_FOLLOW = re.compile(r"继续|接着|刚才的请求|(?:这|那|原来)个请求|上面那个|第一次|最初|说错|更正|还是失败|仍然.{0,4}(?:失败|报错)")
_RECALL = re.compile(r"刚才|之前|第一[次轮]|最初|上面|说错|(?:那个|这个)请求")
_VERSION = re.compile(r"(?i)(?:API\s*版本|接口版本|当前版本|版本)\s*[:：为是]?\s*(v\d+(?:\.\d+){0,2})\b")
_REQUEST = re.compile(r"(?<![\w-])req_[A-Za-z0-9][A-Za-z0-9_-]{0,59}(?![\w-])", re.ASCII | re.I)
_ATTEMPT = re.compile(r"已(?:尝试|重试|修改|重启|调整)|试过|还是失败|仍然报错")
_REGION = re.compile(r"(?:地域|区域)\s*[:：为是]?\s*(北京|上海|杭州|香港|新加坡|美国|欧洲)")
_MAX_SCOPES = 12
_REPLAY_LIMIT = 100
_RECALL_CHARS = 1000
_PROGRESS_QUERY = re.compile(r"进展|排障过程|哪些步骤|试过什么|哪些.{0,8}(?:试过|尝试)|下一步|待查")
_PROGRESS_MARKERS = {
    "pending": re.compile(r"还没(?:检查|验证|查)|还需(?:检查|验证|核对)|待查|待验证"),
    "feedback": re.compile(r"回退|恢复后|仍然报错|还是失败|不再报错|(?:验证|重试)结果"),
    "attempt": _ATTEMPT,
}


@dataclass
class TurnContext:
    history: list[dict]
    entities: dict[str, str]
    sources: dict[str, str]
    continuing: bool
    ambiguous: bool
    recall: list[dict]
    metadata: dict
    progress: list[dict] | None = None


def compare_context_selection(active, candidate, question):
    """Compare selection only. The shadow does not plan or execute tools."""
    affected = {key for key in set(active) | set(candidate.entities) if active.get(key) != candidate.entities.get(key)}
    return {
        "differences": len(affected),
        "scopeDifferent": any(key in affected for key in (*_ANCHORS, "month")),
        "candidateContinued": candidate.continuing,
        "candidateAmbiguous": candidate.ambiguous,
        "candidateHistoryMessages": len(candidate.history),
        "candidateRecalledMessages": len(candidate.recall),
        "candidateProgressMessages": len(candidate.progress or []),
        "candidateAssemblyMs": candidate.metadata.get("assemblyMs", 0),
        "candidateNeedsCurrentRead": bool(candidate.entities and re.search(
            r"当前|现在|最新|剩余|实时|重新查", question,
        ) and re.search(r"账单|用量|额度|工单状态|余额", question)),
    }


def _record_progress(scope, message_id, question):
    markers = [kind for kind, pattern in _PROGRESS_MARKERS.items() if pattern.search(question)]
    if not markers:
        return
    facts = scope.setdefault("progress", {})
    signature = hashlib.sha256(" ".join(question.split()).encode()).hexdigest()
    for kind in markers:
        previous = facts.get(kind, [])
        if any(item["signature"] == signature for item in previous):
            continue
        limit = 4 if kind == "attempt" else 2
        facts[kind] = [*previous, {"messageId": message_id, "signature": signature}][-limit:]


async def recover_progress(db, owner, scope, before, budget):
    """Build a small extractive summary from authorized source messages."""
    pointers = {}
    for kind, entries in scope.get("progress", {}).items():
        for entry in entries:
            message_id = entry["messageId"]
            if message_id < before:
                pointers.setdefault(message_id, kind)
    if not pointers or budget <= 0:
        return []
    rows = (await db.scalars(select(ConversationMessage).where(
        *owner, ConversationMessage.role == "user", ConversationMessage.id.in_(pointers),
    ))).all()
    recovered = []
    for row in sorted(rows, key=lambda row: (
        {"pending": 0, "feedback": 1, "attempt": 2}[pointers[row.id]], -row.id,
    )):
        if budget <= 0 or len(recovered) >= 6:
            break
        excerpt = redact_text(row.content)[:min(165, budget)]
        if excerpt and not detect_prompt_injection(excerpt) and not re.search(r"(?:来源|source)\s*#", excerpt, re.I):
            recovered.append({"messageId": row.id, "text": excerpt, "kind": pointers[row.id],
                              "source": "user_report"})
            budget -= len(excerpt)
    return sorted(recovered, key=lambda row: row["messageId"])


def _fields(question):
    values = extract_entities(question)
    # The legacy pattern does not recognize an ID immediately after a Chinese character.
    if match := _REQUEST.search(question):
        values.setdefault("request_id", match.group())
    if match := _VERSION.search(question):
        values["api_version"] = match[1].lower()
    if match := _REGION.search(question):
        values["region"] = match[1]
    products = named_products(question)
    if len(products) == 1:
        values["product"] = products[0]
    if re.search(r"账单|账期|用量|调用量|费用|额度", question):
        if month := requested_billing_month(question):
            values["month"] = month
    return values


def apply_message(state, message):
    """Fold customer assertions only. Business receipts stay in their owning stores."""
    question = redact_text(message.content)
    explicit = _fields(question)
    scopes = state.setdefault("scopes", {})
    active = state.get("active")
    previous = scopes.get(active, {})
    continuing = bool(_FOLLOW.search(question)) and not topic_changed(question)
    requests = set(_REQUEST.findall(question))
    if len(requests) > 1:
        return {}, {}, False, True, None
    if "month" in explicit and not any(name in explicit for name in _ANCHORS) and re.search(
        r"账单|账期|用量|调用量|费用", question
    ):
        identity = f"billing:{explicit['month']}"
    else:
        anchor = next(((name, explicit[name]) for name in _ANCHORS if name in explicit), None)
        # A compatible secondary anchor enriches the active request.
        same_scope = anchor and not topic_changed(question) and (
            previous.get("fields", {}).get(anchor[0], {}).get("value") == anchor[1]
            or (continuing and anchor[0] == "app_id" and
                not previous.get("fields", {}).get("app_id"))
        )
        identity = active if same_scope and active else f"{anchor[0]}:{anchor[1]}" if anchor else None
    if not identity and topic_changed(question):
        state["active"] = None
        return explicit, dict.fromkeys(explicit, "current"), False, False, None
    if not identity and continuing:
        identity = active
    if not identity:
        # Chatter does not erase a case, and does not load it into this turn.
        return explicit, dict.fromkeys(explicit, "current"), False, False, None

    scope = scopes.pop(identity, {"fields": {}, "attempts": []})
    if identity != active or topic_changed(question):
        scope["activatedAtId"] = message.id
    fields = scope["fields"]
    for key, value in explicit.items():
        old = fields.get(key)
        if not old or old["value"] != value:
            fields[key] = {
                "value": value, "source": "user_report", "messageId": message.id,
                "recordedAt": message.created_at.isoformat(),
                **({"supersedesMessageId": old["messageId"]} if old else {}),
            }
    if _ATTEMPT.search(question):
        scope.setdefault("firstAttemptId", message.id)
        scope["attempts"] = [*scope["attempts"], message.id][-8:]
    _record_progress(scope, message.id, question)
    scopes[identity] = scope
    while len(scopes) > _MAX_SCOPES or (len(scopes) > 1 and len(json.dumps(scopes, ensure_ascii=False).encode()) > 48_000):
        scopes.pop(next(iter(scopes)))
    state["active"] = identity
    entities = {key: info["value"] for key, info in fields.items()}
    sources = {key: "current" if key in explicit else "continuation" for key in entities}
    return entities, sources, bool(continuing and identity == active), False, scope


def bounded_history(rows, *, max_messages, max_chars):
    """Keep complete recent turns. Never truncate a message or orphan its answer."""
    turns = []
    for row in rows:
        if row.role == "user":
            turns.append([row])
        elif turns and row.role == "assistant" and row.generation_id == turns[-1][0].generation_id:
            turns[-1].append(row)
    selected = []
    used = 0
    for turn in reversed(turns):
        chars = sum(len(redact_text(row.content)) for row in turn)
        if len(selected) + len(turn) > max_messages or used + chars > max_chars:
            break
        selected[0:0] = turn
        used += chars
    return [{"role": row.role, "content": redact_text(row.content)} for row in selected], {row.id for row in selected}


async def assemble_turn(db, message, settings):
    """Persist a revision fenced by the original user message's monotonic ID."""
    message = SimpleNamespace(**{
        key: getattr(message, key) for key in ("id", "user_id", "conversation_id", "content", "created_at")
    })
    owner = (
        ConversationMessage.conversation_id == message.conversation_id,
        ConversationMessage.user_id == message.user_id,
    )
    key = (
        ConversationContextState.conversation_id == message.conversation_id,
        ConversationContextState.user_id == message.user_id,
    )
    for _ in range(4):
        revision = (await db.execute(select(ConversationContextState.last_message_id).where(*key))).scalar_one_or_none()
        if revision is not None and revision >= message.id:
            # Never expose future state to a delayed generation.
            explicit = _fields(message.content)
            return TurnContext([], explicit, dict.fromkeys(explicit, "current"),
                               False, False, [], {"mode": "superseded"})
        state = None if revision is None else await conversation_memory.get_context_snapshot(
            message.user_id, message.conversation_id, revision,
        )
        cached = state is not None
        if not cached:
            encoded = (await db.execute(select(ConversationContextState.state_json).where(
                *key, ConversationContextState.last_message_id == revision,
            ))).scalar_one_or_none()
            if revision is not None and encoded is None:
                await db.rollback()
                continue
            state = json.loads(encoded) if encoded else {}
        pending = (await db.scalars(select(ConversationMessage).where(
            *owner, ConversationMessage.role == "user", ConversationMessage.id > (revision or 0),
            ConversationMessage.id < message.id,
        ).order_by(ConversationMessage.id.desc()).limit(_REPLAY_LIMIT))).all()
        for prior in reversed(pending):
            apply_message(state, prior)
        entities, sources, continuing, ambiguous, scope = apply_message(state, message)
        encoded = json.dumps(state, ensure_ascii=False)
        try:
            if revision is None:
                db.add(ConversationContextState(conversation_id=message.conversation_id, user_id=message.user_id,
                                                last_message_id=message.id, state_json=encoded))
            else:
                changed = await db.execute(update(ConversationContextState).where(
                    *key, ConversationContextState.last_message_id == revision,
                ).values(last_message_id=message.id, state_json=encoded))
                if changed.rowcount != 1:
                    await db.rollback()
                    continue
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
    else:
        raise RuntimeError("Unable to commit conversation context revision")
    await conversation_memory.put_context_snapshot(message.user_id, message.conversation_id, message.id, state)

    recent = select(ConversationMessage).where(*owner, ConversationMessage.id < message.id)
    if scope:
        recent = recent.where(ConversationMessage.id >= scope["activatedAtId"])
    elif topic_changed(message.content) or ambiguous:
        recent = recent.where(ConversationMessage.id >= message.id)
    rows = (await db.scalars(recent.order_by(ConversationMessage.id.desc())
                            .limit(max(0, settings.conversation_history_messages)))).all()
    recall = []
    max_chars = max(0, settings.conversation_history_chars)
    history, selected_ids = bounded_history(reversed(rows), max_messages=max(0, settings.conversation_history_messages),
                                            max_chars=max_chars)
    if continuing and scope and _RECALL.search(message.content):
        anchors = [item["messageId"] for item in scope["fields"].values()]
        priority = [scope.get("firstAttemptId")] if re.search(r"第一次|最初", message.content) else []
        ids = list(dict.fromkeys([*priority, *anchors, *reversed(scope["attempts"])]))
        ids = [item for item in ids if item and item not in selected_ids and item < message.id][:3]
        if ids:
            original = (await db.scalars(select(ConversationMessage).where(
                *owner, ConversationMessage.id.in_(ids), ConversationMessage.role == "user",
            ))).all()
            remaining = min(_RECALL_CHARS, max_chars)
            by_id = {row.id: row for row in original}
            for row in (by_id[item] for item in ids if item in by_id):
                if remaining <= 0:
                    break
                excerpt = redact_text(row.content)[: min(400, remaining)]
                recall.append({"messageId": row.id, "text": excerpt, "source": "user_report"})
                remaining -= len(excerpt)
        if recall:
            history, _ = bounded_history(reversed(rows), max_messages=max(0, settings.conversation_history_messages - len(recall)),
                                         max_chars=max_chars - sum(len(item["text"]) for item in recall))
    progress = []
    progress_unavailable = False
    if (getattr(settings, "context_progress_enabled", False) and continuing and scope
            and _PROGRESS_QUERY.search(message.content)):
        spare_messages = max(0, settings.conversation_history_messages - len(recall))
        if spare_messages:
            try:
                async with asyncio.timeout(0.5):
                    progress = (await recover_progress(
                        db, owner, scope, message.id,
                        min(800, max(0, max_chars - sum(len(item["text"]) for item in recall))),
                    ))[:spare_messages]
            except (TimeoutError, SQLAlchemyError):
                progress_unavailable = True
            if progress:
                progress_ids = {item["messageId"] for item in progress}
                recall = [item for item in recall if item["messageId"] not in progress_ids]
                progress_gids = {row.generation_id for row in rows if row.id in progress_ids and row.generation_id}
                remaining_rows = [row for row in rows if row.id not in progress_ids and row.generation_id not in progress_gids]
                injected = [*recall, *progress]
                history, _ = bounded_history(reversed(remaining_rows),
                                             max_messages=max(0, settings.conversation_history_messages - len(injected)),
                                             max_chars=max_chars - sum(len(item["text"]) for item in injected))
    metadata = {
        "mode": "scoped", "restoredFrom": "redis_versioned" if cached else "database",
        "historyMessages": len(history), "historyChars": sum(len(item["content"]) for item in history),
        "trimmedMessages": len(rows) - len(history), "recalledMessages": len(recall),
        "recalledChars": sum(len(item["text"]) for item in recall),
        "historyTokensEstimated": sum(estimate_tokens(item["content"]) for item in history)
        + sum(estimate_tokens(item["text"]) for item in [*recall, *progress]),
        "progressMessages": len(progress),
        "progressChars": sum(len(item["text"]) for item in progress),
        "progressUnavailable": progress_unavailable,
        "continued": continuing, "ambiguous": ambiguous,
        "inheritedFields": sum(value == "continuation" for value in sources.values()),
        "retainedCase": bool(state.get("active") and scope is None and not ambiguous),
    }
    return TurnContext(history, entities, sources, continuing, ambiguous, recall, metadata, progress)
