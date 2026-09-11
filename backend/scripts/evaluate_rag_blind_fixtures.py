from __future__ import annotations

"""Run the fixture-required retrieval and authorization checks for blind RAG."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _result_names(rows: list[dict]) -> list[str]:
    return [str(row.get("fileName") or "") for row in rows]


async def main_async(output: str | None) -> int:
    from sqlalchemy import select

    from app.db.models import User
    from app.db.session import SessionLocal, engine
    from app.knowledge.elasticsearch import elasticsearch_service
    from app.knowledge.rag import rag_service

    checks: list[dict[str, Any]] = []

    async def run_check(
        db,
        user: User,
        check_id: str,
        question: str,
        *,
        expected_name: str | None = None,
        forbidden_names: set[str] | None = None,
        filters: dict | None = None,
        expect_empty: bool = False,
    ) -> None:
        rows = await rag_service.search(
            db,
            user,
            question,
            6,
            metadata_filters=filters,
            include_evaluation_fixtures=True,
        )
        names = _result_names(rows)
        passed = (not rows if expect_empty else (expected_name in names if expected_name else True))
        if forbidden_names and forbidden_names.intersection(names):
            passed = False
        checks.append({
            "id": check_id,
            "passed": passed,
            "expected": expected_name or ("empty" if expect_empty else "no forbidden document"),
            "forbidden": sorted(forbidden_names or ()),
            "returnedFiles": names,
            "metadataFilters": filters or {},
        })

    try:
        async with SessionLocal() as db:
            users = {
                name: await db.scalar(select(User).where(User.username == name))
                for name in ("rag_eval_org_a", "rag_eval_org_b")
            }
            if not all(users.values()):
                raise RuntimeError("fixtures are not seeded; run seed_advanced_rag_fixtures.py first")
            user_a = users["rag_eval_org_a"]
            user_b = users["rag_eval_org_b"]

            # Version/currentness: filters make the requested version explicit;
            # the returned name proves that an old vector cannot masquerade as current.
            await run_check(db, user_a, "fixture-01", "2025 退款申请窗口", expected_name="fixture-refund-policy-v2025.md", filters={"version": "2025.12"})
            await run_check(db, user_a, "fixture-02", "当前 2026 退款申请窗口", expected_name="fixture-refund-policy-v2026.md", filters={"version": "2026.08", "category": "refund"}, forbidden_names={"fixture-refund-policy-v2025.md"})
            await run_check(db, user_a, "fixture-03", "旧版 Professional 基础费用", expected_name="fixture-billing-policy-v2025.md", filters={"version": "2025.12", "plan": "Professional"})
            await run_check(db, user_a, "fixture-04", "遗留客户端 request_id 升级", expected_name="fixture-api-contract-v2025.md", filters={"version": "2025.12", "category": "api_usage"})
            await run_check(db, user_a, "fixture-05", "当前 Professional QPS 规则", expected_name="rate-limit.md", filters={"version": "2026.08", "category": "rate_limit"}, forbidden_names={"fixture-rate-limit-v2025.md"})
            await run_check(db, user_a, "fixture-06", "恶意文档中的跳过权限指令", expected_name="fixture-security-malicious-instructions.md", filters={"category": "security"})

            # Metadata mismatch: only server-side filters are supplied. Empty
            # results show that a client cannot widen a contradictory filter.
            await run_check(db, user_a, "fixture-07", "认证资料", expect_empty=True, filters={"category": "authentication", "region": "CN"})
            await run_check(db, user_a, "fixture-08", "Professional 账单", expect_empty=True, filters={"category": "billing", "plan": "Enterprise"})
            await run_check(db, user_a, "fixture-09", "退款窗口", expect_empty=True, filters={"category": "refund", "channel": "api"})
            await run_check(db, user_a, "fixture-10", "限流规则", expect_empty=True, filters={"category": "not-a-category"})
            await run_check(db, user_a, "fixture-11", "当前退款窗口", expect_empty=True, filters={"category": "refund", "version": "2099.01"})
            await run_check(db, user_a, "fixture-12", "组织 B 私有退款 B-REFUND-ONLY", forbidden_names={"fixture-org-b-private-refund.md"}, filters={"category": "refund", "channel": "billing"})

            # A/B organization isolation and one shared public document.
            await run_check(db, user_a, "fixture-13", "A-REFUND-ONLY", expected_name="fixture-org-a-private-refund.md", forbidden_names={"fixture-org-b-private-refund.md"})
            await run_check(db, user_b, "fixture-14", "B-REFUND-ONLY", expected_name="fixture-org-b-private-refund.md", forbidden_names={"fixture-org-a-private-refund.md"})
            await run_check(db, user_a, "fixture-15", "B-BILLING-ONLY", forbidden_names={"fixture-org-b-private-billing.md"})
            await run_check(db, user_b, "fixture-16", "A-API-ONLY", forbidden_names={"fixture-org-a-private-api.md"})
            await run_check(db, user_a, "fixture-17", "PUBLIC-SECURITY-ONLY", expected_name="fixture-public-security.md")
            await run_check(db, user_b, "fixture-18", "PUBLIC-SECURITY-ONLY", expected_name="fixture-public-security.md")
            await run_check(db, user_b, "fixture-19", "A-REFUND-ONLY", forbidden_names={"fixture-org-a-private-refund.md"})
    finally:
        await elasticsearch_service.close()
        await engine.dispose()

    failures = [item for item in checks if not item["passed"]]
    report = {"checkCount": len(checks), "passed": len(checks) - len(failures), "failed": len(failures), "checks": checks}
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded)
    if output:
        Path(output).write_text(encoded + "\n", encoding="utf-8")
    return 1 if failures else 0


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate isolated blind RAG fixtures")
    parser.add_argument("--output", help="write the JSON report")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(main_async(args.output)))
