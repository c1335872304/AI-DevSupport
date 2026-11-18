"""Temporary USER identity only; never seed business facts or knowledge."""

import asyncio
import json
import sys
import uuid
from pathlib import Path

STATE = Path("/evaluation/private/identity.json")


async def main(action):
    from sqlalchemy import delete, func, select

    from app.core.security import hash_password
    from app.db.models import (
        AgentRun,
        Base,
        DiagnosisEvidence,
        DiagnosisExecution,
        DiagnosisSession,
        DiagnosisStep,
        DiagnosisTransition,
        DiagnosisTurn,
        FileUpload,
        GenerationState,
        LLMTokenReservation,
        ToolExecution,
        User,
    )
    from app.db.session import SessionLocal, engine

    try:
        async with SessionLocal() as db:
            if action == "prepare":
                assert not STATE.exists()
                frozen = STATE.parent.parent / "frozen-inputs.json"
                quota = (
                    json.loads(frozen.read_text()).get("applicationLlmQuota", 500000)
                    if frozen.exists()
                    else 500000
                )
                password = "EvalA1" + uuid.uuid4().hex[:10]
                user = User(
                    username="rag_eval_" + uuid.uuid4().hex[:6],
                    password=hash_password(password),
                    role="USER",
                    llm_token_balance=quota,
                    embedding_token_balance=10000,
                )
                db.add(user)
                await db.commit()
                STATE.write_text(
                    json.dumps({"userId": user.id, "username": user.username, "password": password}),
                    encoding="utf-8",
                )
                print("Independent evaluation USER prepared; credentials remain private")
                return
            state = json.loads(STATE.read_text())
            user = await db.get(User, state["userId"])
            assert user and user.username == state["username"] and user.username.startswith("rag_eval_")
            owner = str(user.id)
            assert not await db.scalar(
                select(func.count()).select_from(FileUpload).where(FileUpload.user_id == owner)
            )
            assert not await db.scalar(
                select(func.count())
                .select_from(GenerationState)
                .where(GenerationState.user_id == owner, GenerationState.status.in_(["RUNNING", "PENDING"]))
            )
            assert not await db.scalar(
                select(func.count())
                .select_from(LLMTokenReservation)
                .where(LLMTokenReservation.user_id == owner, LLMTokenReservation.status == "RESERVED")
            )
            diagnoses = select(DiagnosisSession.diagnosis_id).where(DiagnosisSession.user_id == owner)
            for model in (
                DiagnosisExecution,
                DiagnosisStep,
                DiagnosisTurn,
                DiagnosisEvidence,
                DiagnosisTransition,
            ):
                await db.execute(delete(model).where(model.diagnosis_id.in_(diagnoses)))
            runs = select(AgentRun.run_id).where(AgentRun.user_id == owner)
            await db.execute(delete(ToolExecution).where(ToolExecution.run_id.in_(runs)))
            for mapper in Base.registry.mappers:
                model = mapper.class_
                if hasattr(model, "user_id"):
                    await db.execute(delete(model).where(model.user_id == owner))
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()
            print("Only the verified evaluation identity and owned traces removed; knowledge untouched")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
