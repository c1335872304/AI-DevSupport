from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.evaluation.customer_service import validate_customer_service_case

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "eval/customer_service/benchmark_extended.jsonl"


def test_extended_customer_service_benchmark_has_120_valid_cases():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 120
    assert len({row["id"] for row in rows}) == 120
    assert all(validate_customer_service_case(row)["pass"] for row in rows)
    assert len({row["baseCaseId"] for row in rows}) == 24
    difficulties = Counter(row["difficulty"] for row in rows)
    assert difficulties["hard"] >= 20
    assert difficulties["medium"] >= 20
    assert difficulties["easy"] >= 5
