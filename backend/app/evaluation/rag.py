from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EvalExpectation:
    file_md5: str | None = None
    file_name: str | None = None
    chunk_ids: frozenset[int] = frozenset()


def is_relevant(result: dict, expected: EvalExpectation) -> bool:
    if expected.file_md5 and result.get("fileMd5") != expected.file_md5:
        return False
    if expected.file_name and result.get("fileName") != expected.file_name:
        return False
    if expected.chunk_ids:
        try:
            return int(result.get("chunkId")) in expected.chunk_ids
        except (TypeError, ValueError):
            return False
    return bool(expected.file_md5 or expected.file_name)


def evaluate_ranking(results: list[dict], expected: EvalExpectation, k: int) -> dict[str, float]:
    ranked = results[: max(0, k)]
    relevant_flags = [is_relevant(item, expected) for item in ranked]
    if not expected.chunk_ids:
        # A file-level expectation represents one relevant document. Parent-child
        # retrieval can legitimately return several children from that same file;
        # count the first matching document once so NDCG remains normalized.
        first_match = next((index for index, flag in enumerate(relevant_flags) if flag), None)
        if first_match is not None:
            relevant_flags = [index == first_match for index in range(len(relevant_flags))]
    first_rank = next((idx for idx, flag in enumerate(relevant_flags, start=1) if flag), None)

    if expected.chunk_ids:
        expected_count = len(expected.chunk_ids)
        retrieved_ids = {
            int(item.get("chunkId"))
            for item, flag in zip(ranked, relevant_flags)
            if flag and item.get("chunkId") is not None
        }
        recall = len(retrieved_ids) / expected_count if expected_count else 0.0
        ideal_relevant = min(expected_count, len(ranked))
    else:
        recall = 1.0 if first_rank is not None else 0.0
        ideal_relevant = 1 if ranked else 0

    dcg = sum((1.0 / math.log2(rank + 1)) for rank, flag in enumerate(relevant_flags, start=1) if flag)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_relevant + 1))
    ndcg = dcg / idcg if idcg else 0.0
    mrr = 1.0 / first_rank if first_rank else 0.0
    hit = 1.0 if first_rank else 0.0
    return {"hit": hit, "recall": recall, "mrr": mrr, "ndcg": ndcg}


def aggregate_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {"queries": 0, "hitRate": 0.0, "recall": 0.0, "mrr": 0.0, "ndcg": 0.0}
    count = len(rows)
    return {
        "queries": count,
        "hitRate": sum(row["hit"] for row in rows) / count,
        "recall": sum(row["recall"] for row in rows) / count,
        "mrr": sum(row["mrr"] for row in rows) / count,
        "ndcg": sum(row["ndcg"] for row in rows) / count,
    }
