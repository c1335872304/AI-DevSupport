from __future__ import annotations

import json
from pathlib import Path

from app.knowledge.parser import parser_service

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = BACKEND_ROOT / "demo_knowledge"
EVAL_PATH = BACKEND_ROOT / "eval" / "demo_knowledge_rag.jsonl"


def test_demo_knowledge_manifest_is_complete_and_searchable():
    manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    names = [item["file"] for item in manifest["documents"]]
    assert names == [
        "api-getting-started.md",
        "authentication.md",
        "rate-limit.md",
        "billing-policy.md",
        "refund-policy.md",
        "error-codes.md",
        "troubleshooting-faq.md",
    ]

    for name in names:
        path = DEMO_DIR / name
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# ")
        assert len(text) >= 500
        parents, children = parser_service.hierarchical_chunk(parser_service.parse(name, path.read_bytes()))
        assert parents
        assert children
        assert all(child.text.strip() for child in children)


def test_demo_rag_eval_targets_only_shipped_documents():
    manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    shipped = {item["file"] for item in manifest["documents"]}
    rows = [
        json.loads(line)
        for line in EVAL_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert len(rows) >= 10
    assert {row["expectedFileName"] for row in rows} <= shipped
    assert all(str(row.get("question") or "").strip() for row in rows)


def test_demo_knowledge_keeps_policy_and_customer_state_separate():
    refund = (DEMO_DIR / "refund-policy.md").read_text(encoding="utf-8")
    billing = (DEMO_DIR / "billing-policy.md").read_text(encoding="utf-8")
    assert "不能推断" in refund
    assert "业务 Tool/MCP" in refund
    assert "query_plan" in billing
    assert "query_usage" in billing
    assert "query_bill" in billing
