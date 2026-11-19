"""Prepare/clean only uniquely owned acceptance data in the deployed Docker Demo."""

import argparse
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
STATE = Path("/tmp/docker_demo_acceptance.json")


async def prepare():
    from app.core.security import hash_password
    from app.core.time import utcnow
    from app.db.models import User, ConversationSession, SupportApplication, SupportApiCallLog, SupportRequestObservation, SupportApiKey, SupportPlan, SupportSubscription, SupportUsageRecord, SupportInvoice
    from app.db.session import SessionLocal
    from app.diagnosis.service import begin_turn
    from app.diagnosis.execution import run_turn
    from app.tools.registry import tool_registry
    tag = uuid.uuid4().hex[:10]
    password = "DemoA1"+uuid.uuid4().hex[:10]
    async with SessionLocal() as db:
        user = User(username="dockeraccept_"+tag[:3], password=hash_password(password), role="USER", llm_token_balance=20000, embedding_token_balance=20000)
        foreign = User(username="dockeraccept_o"+tag[:2], password=hash_password(password), role="USER")
        db.add_all([user, foreign]); await db.flush()
        app = "app_accept_"+tag
        plan = "plan_accept_"+tag
        db.add_all([SupportApplication(id=app, user_id=str(user.id), name="Temporary Docker acceptance"),
            SupportApiKey(id="key_accept_"+tag, user_id=str(user.id), app_id=app, key_masked="demo-***", status="ACTIVE"),
            SupportPlan(id=plan, name="Acceptance plan", qps_limit=10, monthly_quota=1000, base_price=10, overage_price_per_call=.01),
            SupportSubscription(user_id=str(user.id), plan_id=plan, status="ACTIVE"),
            SupportUsageRecord(user_id=str(user.id), month="2026-10", call_count=1200, overage_count=200),
            SupportInvoice(id="inv_accept_"+tag, user_id=str(user.id), month="2026-10", amount=12, status="ISSUED", items_json='{"base":10,"overage":2}')])
        await db.commit()
    cases = []
    for label, code, obs in (("401",401,{"authPresent":True,"authSchemeValid":True,"keyStateAtCall":"EXPIRED"}), ("429",429,{"limiterKind":"RATE","rateObserved":11,"rateLimit":10}), ("human",429,{"limiterKind":"QUOTA","quotaRemaining":0})):
        old, new = f"req_accept_{tag}_{label}_old", f"req_accept_{tag}_{label}_new"
        conversation, generation = f"accept_{tag}_{label}", f"accept_{tag}_{label}_g1"
        async with SessionLocal() as db:
            db.add(ConversationSession(conversation_id=conversation, user_id=str(user.id), title="Docker验收 "+label))
            db.add(SupportApiCallLog(request_id=old, user_id=str(user.id), app_id=app, endpoint="/v1/chat", http_status=code, created_at=utcnow()-timedelta(minutes=10)))
            db.add(SupportRequestObservation(request_id=old, user_id=str(user.id), service_id="demo-api", rule_version="2026-10-v1", observations_json=json.dumps(obs)))
            await db.commit()
        question = f"请求 {old} 返回{code}，请核查" + ("并转人工客服" if label == "human" else "")
        case = await begin_turn(user_id=str(user.id), conversation_id=conversation, generation_id=generation, question=question, entities={"request_id":old}, sources={"request_id":"current"}, diagnostic=True)
        await run_turn(generation, user, tool_registry, finalize=True)
        async with SessionLocal() as db:
            db.add(SupportApiCallLog(request_id=new, user_id=str(user.id), app_id=app, endpoint="/v1/chat", http_status=429 if label == "429" else 200, created_at=utcnow()))
            if label == "429":
                db.add(SupportRequestObservation(request_id=new, user_id=str(user.id), service_id="demo-api", rule_version="2026-10-v1", observations_json='{"limiterKind":"QUOTA","quotaRemaining":0}'))
            await db.commit()
        cases.append({"label":label,"diagnosisId":case,"generationId":generation,"newRequestId":new,"oldRequestId":old})
    state = {"userId":user.id,"foreignId":foreign.id,"username":user.username,"foreignUsername":foreign.username,"password":password,"planId":plan,"cases":cases}
    STATE.write_text(json.dumps(state,indent=2),encoding="utf-8")
    STATE.chmod(0o600)
    print("Temporary acceptance identities and three diagnostic cases prepared; credentials remain in private fixture file")


async def cleanup():
    from sqlalchemy import delete, select
    from app.db.models import Base, User, FileUpload, DiagnosisSession, AgentRun, ProcessingJob, IndexBuild, SupportPlan, IndexOutbox, EmbeddingAttempt, DocumentRevision, DiagnosisExecution, DiagnosisStep, DiagnosisTurn, DiagnosisEvidence, DiagnosisTransition, ToolExecution
    from app.db.session import SessionLocal
    from app.documents.lifecycle import tombstone_document, collect_garbage
    state = json.loads(STATE.read_text(encoding="utf-8"))
    ids = [state["userId"],state["foreignId"]]
    owners = [str(i) for i in ids]
    async with SessionLocal() as db:
        users = list((await db.scalars(select(User).where(User.id.in_(ids)))).all())
        assert len(users) == 2 and all(u.username.startswith("dockeraccept_") for u in users)
        files = list((await db.scalars(select(FileUpload).where(FileUpload.user_id.in_(owners)))).all())
        file_ids = [f.id for f in files]
        cases = list((await db.scalars(select(DiagnosisSession.diagnosis_id).where(DiagnosisSession.user_id.in_(owners)))).all())
        runs = list((await db.scalars(select(AgentRun.run_id).where(AgentRun.user_id.in_(owners)))).all())
        for file in files:
            if file.deleted_at is None:
                await tombstone_document(db,file.id)
        await db.commit()
    for file_id in file_ids:
        await collect_garbage(sessions=SessionLocal,document_id=file_id,retention_seconds=0)
    async with SessionLocal() as db:
        jobs = select(ProcessingJob.job_id).where(ProcessingJob.file_id.in_(file_ids))
        builds = select(IndexBuild.build_id).where(IndexBuild.file_id.in_(file_ids))
        await db.execute(delete(IndexOutbox).where(IndexOutbox.job_id.in_(jobs)))
        await db.execute(delete(EmbeddingAttempt).where(EmbeddingAttempt.build_id.in_(builds)))
        for model in (DocumentRevision,IndexBuild,ProcessingJob):
            await db.execute(delete(model).where(model.file_id.in_(file_ids)))
        for model in (DiagnosisExecution,DiagnosisStep,DiagnosisTurn,DiagnosisEvidence,DiagnosisTransition):
            await db.execute(delete(model).where(model.diagnosis_id.in_(cases)))
        await db.execute(delete(ToolExecution).where(ToolExecution.run_id.in_(runs)))
        for mapper in Base.registry.mappers:
            model = mapper.class_
            if hasattr(model,"user_id"):
                await db.execute(delete(model).where(model.user_id.in_(owners)))
        assert state["planId"].startswith("plan_accept_")
        await db.execute(delete(SupportPlan).where(SupportPlan.id == state["planId"]))
        await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()
    print("Only the two verified temporary acceptance identities and their owned artifacts were cleaned")


async def grant_fixture_upload_quota():
    from app.db.models import User
    from app.db.session import SessionLocal
    state = json.loads(STATE.read_text())
    async with SessionLocal() as db:
        user = await db.get(User,state["userId"])
        assert user and user.username == state["username"] and user.username.startswith("dockeraccept_")
        # DOCX ZIP byte-size preflight needs ~9k balance; actual parsed text is tiny.
        user.embedding_token_balance = max(int(user.embedding_token_balance),20000)
        await db.commit()
    print("Temporary acceptance identity upload preflight quota set; no provider call")


async def main(action):
    from app.db.session import engine
    from app.knowledge.elasticsearch import elasticsearch_service
    try:
        await {"prepare":prepare,"cleanup":cleanup,"grant-upload-quota":grant_fixture_upload_quota}[action]()
    finally:
        if elasticsearch_service.client:
            await elasticsearch_service.client.close()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","cleanup","grant-upload-quota"])
    asyncio.run(main(parser.parse_args().action))
