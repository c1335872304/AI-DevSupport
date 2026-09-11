from __future__ import annotations

import pytest

from app.knowledge.parser import ParsedBlock, parser_service
from app.evaluation.rag import EvalExpectation, aggregate_metrics, evaluate_ranking
from app.knowledge.reranker import reranker_service


def test_parent_child_chunking_links_children_and_merges_tiny_tail():
    old_parent = parser_service.settings.parent_chunk_size
    old_child = parser_service.settings.chunk_size
    old_overlap = parser_service.settings.chunk_overlap
    old_min = parser_service.settings.min_chunk_size
    try:
        parser_service.settings.parent_chunk_size = 300
        parser_service.settings.chunk_size = 100
        parser_service.settings.chunk_overlap = 20
        parser_service.settings.min_chunk_size = 40
        parents, children = parser_service.hierarchical_chunk([ParsedBlock("测试内容。" * 120, 7)])
        assert len(parents) >= 2
        assert len(children) > len(parents)
        assert all(child.parent_chunk_id < len(parents) for child in children)
        assert all(child.page_number == 7 for child in children)
        assert all(len(child.text) >= 40 or child is children[-1] for child in children)
    finally:
        parser_service.settings.parent_chunk_size = old_parent
        parser_service.settings.chunk_size = old_child
        parser_service.settings.chunk_overlap = old_overlap
        parser_service.settings.min_chunk_size = old_min


def test_reranker_promotes_query_coverage_over_weak_generic_hit():
    candidates = [
        {"score": 0.91, "fileMd5": "a", "chunkId": 1, "textContent": "Python 是一种常用编程语言。"},
        {"score": 0.89, "fileMd5": "b", "chunkId": 2, "textContent": "Python GIL 会限制 CPU 密集型多线程的并行执行。"},
    ]
    result = reranker_service.rerank("Python GIL 为什么影响 CPU 多线程", candidates, 2)
    assert result[0]["fileMd5"] == "b"
    assert result[0]["rerankScore"] >= result[1]["rerankScore"]


def test_rag_eval_metrics_are_correct():
    results = [
        {"fileMd5": "x", "chunkId": 9},
        {"fileMd5": "a", "chunkId": 2},
        {"fileMd5": "a", "chunkId": 3},
    ]
    metrics = evaluate_ranking(results, EvalExpectation(file_md5="a", chunk_ids=frozenset({2, 3})), 3)
    assert metrics["hit"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["mrr"] == pytest.approx(0.5)
    assert 0.0 < metrics["ndcg"] <= 1.0
    summary = aggregate_metrics([metrics, metrics])
    assert summary["queries"] == 2
    assert summary["mrr"] == pytest.approx(0.5)


def test_file_level_rag_eval_deduplicates_parent_child_hits():
    results = [
        {"fileName": "handbook.md", "chunkId": 1},
        {"fileName": "handbook.md", "chunkId": 2},
        {"fileName": "other.md", "chunkId": 1},
    ]
    metrics = evaluate_ranking(results, EvalExpectation(file_name="handbook.md"), 3)
    assert metrics["hit"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["ndcg"] == pytest.approx(1.0)
