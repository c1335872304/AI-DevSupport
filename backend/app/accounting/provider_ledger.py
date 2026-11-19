"""Persist each outbound attempt before sending; unknown usage is never zero."""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import timedelta
import hashlib
import json
from uuid import uuid4

from sqlalchemy import select, update

from app.core.time import utcnow
from app.db.models import ProviderAttempt, ProviderReconciliation

_scope = ContextVar('provider_owner', default=None)
_attempt = ContextVar('provider_attempt', default=None)


@contextmanager
def provider_scope(user_id, generation_id=None, *, sessions=None):
    parent = _scope.get() or {}
    token = _scope.set({'user_id': str(user_id), 'generation_id': generation_id or parent.get('generation_id'),
                        'sessions': sessions or parent.get('sessions')})
    try:
        yield
    finally:
        _scope.reset(token)


def observe_usage(usage, *, kind='LLM', request_id=None):
    attempt = _attempt.get()
    if attempt is None:
        return
    if request_id and not attempt.get('provider_request_id'):
        attempt['provider_request_id'] = str(request_id)[:255]
    if not isinstance(usage, dict) or not any(k in usage for k in ['total_tokens', 'prompt_tokens', 'input_tokens']):
        return
    prompt = max(0, int(usage.get('prompt_tokens', usage.get('input_tokens', 0)) or 0))
    completion = max(0, int(usage.get('completion_tokens', usage.get('output_tokens', 0)) or 0))
    total = max(0, int(usage.get('total_tokens', prompt + completion) or 0))
    attempt.update(prompt_tokens=prompt if kind == 'LLM' else total,
                   completion_tokens=completion if kind == 'LLM' else 0, total_tokens=total)


def observe_identity(request_id):
    attempt = _attempt.get()
    # HTTP request identifiers take precedence over completion-body identifiers.
    if attempt is not None and request_id and not attempt.get('provider_request_id'):
        attempt['provider_request_id'] = str(request_id)[:255]


@asynccontextmanager
async def provider_attempt(kind, model, payload):
    scope = _scope.get()
    if not scope:
        yield
        return
    from app.db.session import SessionLocal
    sessions = scope.get('sessions') or SessionLocal
    identity = uuid4().hex
    # Store a fingerprint, never prompts, credentials or response bodies.
    async with sessions() as db:
        db.add(ProviderAttempt(attempt_id=identity, user_id=scope['user_id'],
            generation_id=scope.get('generation_id'), kind=kind, model=model,
            request_hash=hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()))
        await db.commit()
    observed = {}
    token = _attempt.set(observed)
    error = None
    try:
        yield identity
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        _attempt.reset(token)
        async with sessions() as db:
            await db.execute(update(ProviderAttempt).where(ProviderAttempt.attempt_id == identity,
                ProviderAttempt.status.in_(['IN_FLIGHT', 'UNKNOWN'])).values(
                    **observed, status='REPORTED' if 'total_tokens' in observed else 'UNKNOWN', error_code=error))
            await db.commit()


async def expire_inflight(db):
    result = await db.execute(update(ProviderAttempt).where(ProviderAttempt.status == 'IN_FLIGHT',
        ProviderAttempt.updated_at < utcnow() - timedelta(minutes=10)).values(status='UNKNOWN', error_code='OWNER_LOST'))
    await db.commit()
    return result.rowcount


async def reconcile_statement(db, attempt_id, statement, actor_id):
    """Apply an evidenced provider statement once, without silently billing a customer."""
    await db.execute(update(ProviderAttempt).where(ProviderAttempt.attempt_id == attempt_id)
                     .values(updated_at=ProviderAttempt.updated_at))
    row = await db.get(ProviderAttempt, attempt_id, populate_existing=True)
    if not row:
        raise LookupError('Provider attempt not found')
    total = statement['promptTokens'] + statement['completionTokens']
    if row.kind != statement['kind'] or row.model != statement['model']:
        raise ValueError('Statement does not match attempt kind/model')
    provider_id = statement.get('providerRequestId')
    if row.provider_request_id and provider_id != row.provider_request_id:
        raise ValueError('Provider request identity mismatch')
    if row.status == 'IN_FLIGHT':
        raise ValueError('Provider request still in flight')
    canonical = json.dumps({'attemptId': attempt_id, **statement}, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    previous = await db.scalar(select(ProviderReconciliation).where(ProviderReconciliation.attempt_id == attempt_id))
    if previous:
        if previous.statement_hash != digest:
            raise ValueError('Attempt already reconciled with a different statement')
        return row
    if row.total_tokens is not None and (row.total_tokens != total or row.prompt_tokens != statement['promptTokens'] or row.completion_tokens != statement['completionTokens']):
        raise ValueError('Statement contradicts reported provider usage')
    receipt_key = hashlib.sha256((statement['kind'] + ':' + statement['model'] + ':' +
        (provider_id or statement['evidenceRef'])).encode()).hexdigest()
    if await db.scalar(select(ProviderReconciliation).where(ProviderReconciliation.receipt_key == receipt_key)):
        raise ValueError('Provider receipt already assigned to a different attempt')
    before = {'status': row.status, 'totalTokens': row.total_tokens}
    row.status, row.total_tokens = 'RECONCILED', total
    row.prompt_tokens, row.completion_tokens = statement['promptTokens'], statement['completionTokens']
    row.provider_request_id = provider_id or row.provider_request_id
    row.evidence_ref, row.reconciled_by, row.reconciled_at = statement['evidenceRef'], str(actor_id), utcnow()
    db.add(ProviderReconciliation(id=uuid4().hex, attempt_id=attempt_id, actor_id=str(actor_id),
        evidence_ref=statement['evidenceRef'], statement_hash=digest, receipt_key=receipt_key,
        before_json=json.dumps(before), after_json=canonical))
    from sqlalchemy.exc import IntegrityError
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError('Provider receipt was reconciled concurrently') from exc
    return row


async def recovery_loop():
    import asyncio
    import logging
    from app.db.session import SessionLocal
    while True:
        try:
            async with SessionLocal() as db:
                await expire_inflight(db)
        except Exception:
            logging.getLogger(__name__).exception('Provider usage recovery failed')
        await asyncio.sleep(60)
