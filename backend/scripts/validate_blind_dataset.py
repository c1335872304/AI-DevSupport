from __future__ import annotations

"""Validate the 120-case public RAG blind dataset without model calls."""

import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "coverageBucket",
    "caseType",
    "intent",
    "question",
    "expectedFileName",
    "expectedBehavior",
    "mustNotClaim",
    "entityState",
    "surfaceForm",
    "riskLevel",
    "sourceBatch",
}

EXPECTED_BUCKETS = {"P1": 18, "P2": 18, "P3": 16, "P4": 14, "P5": 14, "P6": 14, "P7": 14, "P8": 12}
EXPECTED_SURFACES = {"standard": 54, "colloquial": 20, "technical_log": 16, "mixed": 12, "typo": 8, "long": 10}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def char_trigrams(value: str) -> set[str]:
    text = normalize(value)
    if len(text) < 3:
        return {text} if text else set()
    return {text[index : index + 3] for index in range(len(text) - 2)}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        row["_line"] = line_number
        rows.append(row)
    return rows


def validate(rows: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    reviews: list[dict[str, Any]] = []
    if len(rows) != 120:
        errors.append(f"expected exactly 120 cases, found {len(rows)}")

    ids = Counter(str(row.get("id") or "") for row in rows)
    for case_id, count in ids.items():
        if not case_id:
            errors.append("empty id")
        elif count != 1:
            errors.append(f"duplicate id: {case_id}")

    normalized_questions: dict[str, str] = {}
    for row in rows:
        case_id = str(row.get("id") or f"line-{row['_line']}")
        missing = sorted(field for field in REQUIRED_FIELDS if field not in row)
        if missing:
            errors.append(f"{case_id}: missing fields {', '.join(missing)}")
        if not isinstance(row.get("mustNotClaim"), list) or not row.get("mustNotClaim"):
            errors.append(f"{case_id}: mustNotClaim must be a non-empty list")
        question = str(row.get("question") or "").strip()
        if not question:
            errors.append(f"{case_id}: question is empty")
            continue
        normalized = normalize(question)
        previous = normalized_questions.get(normalized)
        if previous:
            errors.append(f"duplicate normalized question: {previous} and {case_id}")
        normalized_questions[normalized] = case_id

    bucket_counts = Counter(str(row.get("coverageBucket") or "") for row in rows)
    surface_counts = Counter(str(row.get("surfaceForm") or "") for row in rows)
    if dict(sorted(bucket_counts.items())) != dict(sorted(EXPECTED_BUCKETS.items())):
        errors.append(f"coverageBucket counts mismatch: {dict(sorted(bucket_counts.items()))}")
    if dict(sorted(surface_counts.items())) != dict(sorted(EXPECTED_SURFACES.items())):
        errors.append(f"surfaceForm counts mismatch: {dict(sorted(surface_counts.items()))}")

    behavior_counts = Counter(
        (str(row.get("intent") or ""), str(row.get("expectedFileName") or ""), str(row.get("expectedBehavior") or ""), str(row.get("entityState") or ""))
        for row in rows
    )
    for signature, count in behavior_counts.items():
        if count > 2:
            errors.append(f"more than two cases share intent/file/behavior/entity state: {signature}")

    trigram_sets = {str(row.get("id")): char_trigrams(str(row.get("question") or "")) for row in rows}
    by_id = {str(row.get("id")): row for row in rows}
    for left_id, right_id in combinations(sorted(by_id), 2):
        score = jaccard(trigram_sets[left_id], trigram_sets[right_id])
        if score >= 0.90:
            errors.append(f"near-duplicate trigram similarity {score:.3f}: {left_id}, {right_id}")
        elif score >= 0.78:
            reviews.append({"left": left_id, "right": right_id, "trigramJaccard": round(score, 3)})
    return errors, reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public 120-case RAG blind dataset without calling embedding or LLM providers.")
    parser.add_argument("dataset", nargs="?", default="eval/advanced_rag_blind_public_120.jsonl")
    parser.add_argument("--output", help="Optional JSON result path")
    args = parser.parse_args()
    rows = load_rows(Path(args.dataset))
    errors, reviews = validate(rows)
    result = {
        "dataset": str(args.dataset),
        "caseCount": len(rows),
        "passed": not errors,
        "errors": errors,
        "reviewPairs": reviews,
        "coverageBucketCounts": dict(sorted(Counter(str(row.get("coverageBucket") or "") for row in rows).items())),
        "surfaceFormCounts": dict(sorted(Counter(str(row.get("surfaceForm") or "") for row in rows).items())),
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
