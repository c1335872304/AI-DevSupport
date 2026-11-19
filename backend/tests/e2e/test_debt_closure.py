import asyncio
from datetime import timedelta
import json
import os
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import (Base, ApprovalCheckpoint, ApprovalExecution, RefundApprovalPreview,
                           ProviderAttempt, ProviderReconciliation, SupportHandoff, SupportHandoffAudit, User)


@pytest.fixture(params=['sqlite', 'mysql'])
async def sessions(request, tmp_path):
    url = os.environ.get('DEBT_MYSQL_TEST_URL') if request.param == 'mysql' else 'sqlite+aiosqlite:///' + (tmp_path / 'shared.db').as_posix()
    if not url:
        pytest.skip('Requires isolated MySQL for cross-host debt acceptance')
    assert request.param != 'mysql' or url.endswith('/rag_acceptance')
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def test_approval_recovers_without_local_files_and_reuses_original_decision(sessions, tmp_path, monkeypatch):
    from app.support.refund_preview import advance
    from app.support.approval_execution import run_once
    tag = uuid4().hex
    async with sessions() as db:
        db.add(RefundApprovalPreview(request_id=tag, user_id='1', invoice_id='paid-' + tag,
            request_key=tag, reason='test', decision_id='decision-' + tag, decision='approve',
            decided_by='original-admin', decision_note='Original immutable approval'))
        await db.commit()
        assert await advance(db, tag, tmp_path / 'host-a.sqlite') == 'APPROVED_PREVIEW'
    assert not (tmp_path / 'host-a.sqlite').exists()
    # A separate worker/session has no filesystem state from the first host.
    monkeypatch.setattr(get_settings(), 'refund_sandbox_url', '')
    await asyncio.gather(run_once(sessions=sessions), run_once(sessions=sessions))
    async with sessions() as db:
        row = await db.get(RefundApprovalPreview, tag)
        job = await db.get(ApprovalExecution, tag)
        assert row.decided_by == 'original-admin' and row.decision_note == 'Original immutable approval'
        assert job.status == 'COMPLETED' and job.outcome == 'APPROVED_PREVIEW'
        assert await db.scalar(select(ApprovalCheckpoint).where(ApprovalCheckpoint.thread_id == 'refund-preview:' + tag))


async def test_abandoned_approval_lease_is_recovered_and_closure_audited_once(sessions, monkeypatch):
    from app.support.approval_execution import run_once
    tag = uuid4().hex
    async with sessions() as db:
        db.add(SupportHandoff(handoff_id=tag, user_id='1', reason='test', summary='test'))
        db.add(RefundApprovalPreview(request_id=tag, user_id='1', handoff_id=tag, request_key=tag,
            reason='close', decision_id='d-' + tag, decision='approve', decided_by='10', decision_note='Approved'))
        db.add(ApprovalExecution(request_id=tag, status='RUNNING', owner='dead-host',
            lease_until=utcnow() - timedelta(seconds=5), next_attempt_at=utcnow() - timedelta(seconds=5)))
        await db.commit()
    await run_once(sessions=sessions)
    await run_once(sessions=sessions)
    async with sessions() as db:
        assert (await db.get(SupportHandoff, tag)).status == 'CLOSED'
        audits = (await db.scalars(select(SupportHandoffAudit).where(SupportHandoffAudit.handoff_id == tag))).all()
        assert len(audits) == 1 and audits[0].actor_id == '10'
        assert json.loads(audits[0].before_json)['status'] == 'OPEN'
        assert (await db.get(ApprovalExecution, tag)).status == 'COMPLETED'
        from app.support.approval_execution import execute, database_now
        job = await db.get(ApprovalExecution, tag)
        job.status, job.owner, job.lease_until = 'RUNNING', 'new-host', await database_now(db) + timedelta(seconds=60)
        await db.commit()
        request = await db.get(RefundApprovalPreview, tag)
        outcome, _ = await execute(db, request, 'APPROVED_PREVIEW', allow_submit=True, lease_owner='dead-host')
        assert outcome == 'EXECUTION_SUPERSEDED'
        await db.refresh(job)
        assert job.owner == 'new-host' and job.status == 'RUNNING'
        job.status, job.owner, job.lease_until = 'COMPLETED', None, None
        await db.commit()


async def test_failed_approval_retries_without_losing_decision(sessions, monkeypatch):
    import app.support.approval_execution as service
    tag = uuid4().hex
    async with sessions() as db:
        db.add(RefundApprovalPreview(request_id=tag, user_id='1', invoice_id='paid-' + tag, request_key=tag,
            reason='test', decision_id='d-' + tag, decision='approve', decided_by='10'))
        await db.commit()
    original = service.advance
    async def fail(*args):
        raise OSError('synthetic storage outage')
    monkeypatch.setattr(service, 'advance', fail)
    await service.run_once(sessions=sessions)
    async with sessions() as db:
        job = await db.get(ApprovalExecution, tag)
        assert job.status == 'PENDING' and job.attempts == 1 and job.last_error == 'OSError'
        await db.execute(update(ApprovalExecution).where(ApprovalExecution.request_id == tag)
                         .values(next_attempt_at=utcnow() - timedelta(seconds=1)))
        await db.commit()
    monkeypatch.setattr(service, 'advance', original)
    await service.run_once(sessions=sessions)
    async with sessions() as db:
        assert (await db.get(ApprovalExecution, tag)).status == 'COMPLETED'

    async def unknown(*args, **kwargs):
        return 'REFUND_RECONCILING', None
    monkeypatch.setattr(service, 'reconcile', unknown)
    paused = uuid4().hex
    async with sessions() as db:
        db.add(RefundApprovalPreview(request_id=paused, user_id='1', invoice_id='paid-' + paused,
            request_key=paused, reason='test', decision_id='d-' + paused, decision='approve', decided_by='10'))
        db.add(ApprovalExecution(request_id=paused, attempts=11))
        await db.commit()
    await service.run_once(sessions=sessions)
    async with sessions() as db:
        job = await db.get(ApprovalExecution, paused)
        assert job.status == 'NEEDS_REVIEW' and job.attempts == 12
        from app.api.v1.refund_preview import review_queue, resume
        queue = await review_queue(User(id=10, role='ADMIN'), db, 0, 50)
        item = next(row for row in queue['data'] if row['requestId'] == paused)
        assert item['executionStatus'] == 'NEEDS_REVIEW' and item['executionAttempts'] == 12
        await resume(paused, User(id=11, role='ADMIN'), db)
        assert (await db.get(ApprovalExecution, paused, populate_existing=True)).status == 'PENDING'
        assert (await db.get(RefundApprovalPreview, paused)).decided_by == '10'


async def test_unknown_provider_usage_is_persistent_and_statement_reconciliation_idempotent(sessions):
    from app.accounting.provider_ledger import provider_scope, provider_attempt, reconcile_statement
    tag = uuid4().hex
    with provider_scope('1', tag, sessions=sessions):
        with pytest.raises(TimeoutError):
            async with provider_attempt('LLM', 'test-model', {'secret-prompt': 'never stored'}) as attempt:
                raise TimeoutError('synthetic timeout')
    async with sessions() as db:
        row = await db.get(ProviderAttempt, attempt)
        assert row.status == 'UNKNOWN' and row.total_tokens is None
        assert 'never stored' not in row.request_hash
        statement = {'kind': 'LLM', 'model': 'test-model', 'promptTokens': 15, 'completionTokens': 7,
                     'providerRequestId': 'receipt-' + tag, 'evidenceRef': 'supplier-statement/sha256/' + tag}
        row = await reconcile_statement(db, attempt, statement, '10')
        assert row.status == 'RECONCILED' and row.total_tokens == 22
        await reconcile_statement(db, attempt, statement, '11')
        assert len((await db.scalars(select(ProviderReconciliation).where(ProviderReconciliation.attempt_id == attempt))).all()) == 1
        with pytest.raises(ValueError):
            await reconcile_statement(db, attempt, {**statement, 'promptTokens': 99}, '10')


async def test_partial_provider_usage_survives_error_and_stale_attempts_become_unknown(sessions):
    from app.accounting.provider_ledger import provider_scope, provider_attempt, observe_usage, observe_identity, expire_inflight
    tag = uuid4().hex
    with provider_scope('1', tag, sessions=sessions):
        with pytest.raises(ConnectionError):
            async with provider_attempt('EMBEDDING', 'test-embedding', {}) as identity:
                observe_identity('request-' + tag)
                observe_identity('completion-' + tag)
                observe_usage({'total_tokens': 42}, kind='EMBEDDING', request_id='request-' + tag)
                raise ConnectionError('response body malformed')
    async with sessions() as db:
        row = await db.get(ProviderAttempt, identity)
        assert row.status == 'REPORTED' and row.total_tokens == 42
        assert row.provider_request_id == 'request-' + tag
        stale = uuid4().hex
        db.add(ProviderAttempt(attempt_id=stale, kind='LLM', model='m', request_hash='x',
            updated_at=utcnow() - timedelta(hours=1)))
        await db.commit()
        await expire_inflight(db)
        assert (await db.get(ProviderAttempt, stale, populate_existing=True)).status == 'UNKNOWN'


async def test_ticket_state_machine_audit_and_stale_edit_guard(sessions):
    from app.support.handoff import update_handoff
    tag = uuid4().hex
    async with sessions() as db:
        row = SupportHandoff(handoff_id=tag, user_id='1', reason='test', summary='test')
        db.add(row)
        await db.commit()
        with pytest.raises(ValueError):
            await update_handoff(db, row, status='CLOSED', actor_id='10')
        await db.rollback()
        row = await db.get(SupportHandoff, tag)
        await update_handoff(db, row, status='IN_PROGRESS', actor_id='support-1', assigned_to='support-1')
        with pytest.raises(ValueError):
            await update_handoff(db, row, status='RESOLVED', actor_id='support-2', expected_status='OPEN')
        await db.rollback()
        row = await db.get(SupportHandoff, tag)
        await update_handoff(db, row, status='RESOLVED', actor_id='support-1', resolution_note='Fixed')
        await update_handoff(db, row, status='CLOSED', actor_id='support-1')
        with pytest.raises(ValueError):
            await update_handoff(db, row, status='OPEN', actor_id='support-2')
        audits = (await db.scalars(select(SupportHandoffAudit).where(SupportHandoffAudit.handoff_id == tag))).all()
        assert len(audits) == 3


async def test_support_role_has_ticket_access_but_cannot_approve_or_reconcile(sessions, monkeypatch):
    from app.api.v1 import support, refund_preview, provider_usage
    from app.core.deps import current_user
    from app.db.session import get_db
    app = FastAPI()
    for router in [support.router, refund_preview.router, provider_usage.router]:
        app.include_router(router)
    async def database():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(get_settings(), 'refund_preview_enabled', True)
    app.dependency_overrides[current_user] = lambda: User(id=1, role='SUPPORT')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/support/admin/handoffs')).status_code == 200
        assert (await client.get('/admin/provider-usage')).status_code == 403
        assert (await client.get('/support/admin/refund-requests')).status_code == 403
        app.dependency_overrides[current_user] = lambda: User(id=1, role='USER')
        assert (await client.get('/support/admin/handoffs')).status_code == 403


async def test_supplier_receipt_cannot_be_counted_again_on_another_attempt(sessions):
    from app.accounting.provider_ledger import reconcile_statement
    first, second = uuid4().hex, uuid4().hex
    async with sessions() as db:
        for identity in [first, second]:
            db.add(ProviderAttempt(attempt_id=identity, kind='LLM', model='m', request_hash='x', status='UNKNOWN'))
        await db.commit()
        statement = {'kind': 'LLM', 'model': 'm', 'promptTokens': 7, 'completionTokens': 3,
                     'providerRequestId': 'receipt-' + first, 'evidenceRef': 'statement/line/' + first}
        await reconcile_statement(db, first, statement, '10')
        with pytest.raises(ValueError, match='receipt already'):
            await reconcile_statement(db, second, statement, '10')
        assert (await db.get(ProviderAttempt, second)).total_tokens is None


async def test_role_assignment_is_audited_and_cannot_remove_last_admin(sessions):
    from app.api.v1.admin import change_user_role, UserRoleUpdate
    from app.db.models import UserRoleAudit
    tag = uuid4().hex
    async with sessions() as db:
        admin = User(username='admin-' + tag, password='x', role='ADMIN')
        user = User(username='staff-' + tag, password='x', role='USER')
        db.add_all([admin, user])
        await db.commit()
        version = user.token_version
        result = await change_user_role(user.id, UserRoleUpdate(role='SUPPORT'), admin, db)
        assert result['data']['role'] == 'SUPPORT' and user.token_version == version + 1
        audit = await db.scalar(select(UserRoleAudit).where(UserRoleAudit.user_id == str(user.id)))
        assert audit.previous_role == 'USER' and audit.new_role == 'SUPPORT'
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await change_user_role(admin.id, UserRoleUpdate(role='USER'), admin, db)
