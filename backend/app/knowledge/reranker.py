from __future__ import annotations

import math
import re
from collections import Counter

from app.core.config import get_settings


class RerankerService:
    """Lightweight zero-dependency reranker.

    It deliberately does not require a second model/API. Retrieval score is combined with
    lexical coverage, phrase evidence and source diversity. This gives both DB and
    Elasticsearch backends the same post-retrieval behaviour and provides a clean place to
    plug in a cross-encoder later.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _terms(text: str) -> Counter[str]:
        lowered = text.lower()
        compact = re.sub(r"\s+", "", lowered)
        chinese = re.findall(r"[\u4e00-\u9fff]+", compact)
        bigrams: list[str] = []
        for token in chinese:
            if len(token) == 1:
                bigrams.append(token)
            else:
                bigrams.extend(token[i : i + 2] for i in range(len(token) - 1))
        ascii_terms = re.findall(r"[a-z0-9_]+", lowered)
        return Counter(bigrams + ascii_terms)

    @classmethod
    def lexical_similarity(cls, query: str, text: str) -> float:
        q = cls._terms(query)
        d = cls._terms(text)
        if not q or not d:
            return 0.0
        overlap = sum(min(q[k], d[k]) for k in q.keys() & d.keys())
        denom = math.sqrt(sum(q.values()) * sum(d.values()))
        return overlap / denom if denom else 0.0

    @classmethod
    def coverage(cls, query: str, text: str) -> float:
        q = cls._terms(query)
        if not q:
            return 0.0
        d = cls._terms(text)
        return len(q.keys() & d.keys()) / len(q)

    @staticmethod
    def _normalize_retrieval(values: list[float]) -> list[float]:
        if not values:
            return []
        # Divide by the best positive score rather than min-max scaling. Min-max would turn
        # a tiny gap such as 0.91 vs 0.89 into 1.0 vs 0.0 and make reranking unable to
        # correct near-ties. Relative normalization preserves the original margin.
        best = max(values)
        if best > 0:
            return [max(0.0, value) / best for value in values]
        lo, hi = min(values), max(values)
        if math.isclose(lo, hi):
            return [0.0 for _ in values]
        return [(value - lo) / (hi - lo) for value in values]

    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        if not candidates or top_k <= 0:
            return []

        retrieval_scores = [float(item.get("score") or 0.0) for item in candidates]
        normalized_retrieval = self._normalize_retrieval(retrieval_scores)
        normalized_query = re.sub(r"\s+", "", query.lower())

        scored: list[dict] = []
        for item, retrieval_score, retrieval_norm in zip(candidates, retrieval_scores, normalized_retrieval):
            text = str(item.get("textContent") or "")
            anchor = str(item.get("anchorText") or "")
            lexical = self.lexical_similarity(query, text)
            coverage = self.coverage(query, text)
            compact_text = re.sub(r"\s+", "", text.lower())
            exact = 1.0 if normalized_query and len(normalized_query) >= 4 and normalized_query in compact_text else 0.0
            anchor_bonus = min(1.0, self.coverage(query, anchor)) if anchor else 0.0
            rerank_score = (
                0.52 * retrieval_norm
                + 0.22 * lexical
                + 0.18 * coverage
                + 0.05 * exact
                + 0.03 * anchor_bonus
            )
            enriched = dict(item)
            enriched["retrievalScore"] = retrieval_score
            enriched["rerankScore"] = round(rerank_score, 6)
            enriched["score"] = round(rerank_score, 6)
            scored.append(enriched)

        scored.sort(key=lambda item: (item["rerankScore"], item.get("retrievalScore", 0.0)), reverse=True)

        # Prevent one document from monopolising the context window while keeping ranking
        # deterministic. If the cap blocks too many items, fill remaining slots afterwards.
        max_per_file = max(1, self.settings.rag_max_results_per_file)
        selected: list[dict] = []
        per_file: Counter[str] = Counter()
        deferred: list[dict] = []
        for item in scored:
            key = f"{item.get('ownerUserId', '')}:{item.get('fileMd5', '')}"
            if per_file[key] >= max_per_file:
                deferred.append(item)
                continue
            selected.append(item)
            per_file[key] += 1
            if len(selected) >= top_k:
                return selected
        for item in deferred:
            selected.append(item)
            if len(selected) >= top_k:
                break
        return selected


reranker_service = RerankerService()
