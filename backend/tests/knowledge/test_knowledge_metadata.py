from __future__ import annotations

from datetime import date

from app.knowledge.elasticsearch import ElasticsearchService
from app.knowledge.metadata import normalize_metadata
from app.tools.local.knowledge import SearchKnowledgeTool


def test_normalize_customer_service_metadata():
    value = normalize_metadata({
        "category": ["billing", "refund"],
        "product": " API Platform ",
        "effective_at": "2026-08-01",
        "plan": "Professional",
    })
    assert value["category"] == ["billing", "refund"]
    assert value["product"] == "API Platform"
    assert value["effective_at"] == date(2026, 8, 1)
    assert value["plan"] == "Professional"


def test_elasticsearch_metadata_filter_builds_pre_retrieval_constraints():
    filters = ElasticsearchService._metadata_filter({
        "category": ["authentication", "error_code"],
        "product": "API Platform",
        "channel": "api",
        "effective_at": "2026-08-01",
    })
    assert {"terms": {"category": ["authentication", "error_code"]}} in filters
    assert {"term": {"product": "API Platform"}} in filters
    assert {"term": {"channel": "api"}} in filters
    assert {"range": {"effectiveDate": {"lte": "2026-08-01"}}} in filters


def test_search_knowledge_exposes_metadata_filter_schema_to_llm():
    schema = SearchKnowledgeTool.input_schema
    assert "filters" in schema["properties"]
    props = schema["properties"]["filters"]["properties"]
    assert {"category", "product", "region", "channel", "effective_at", "error_code", "plan"}.issubset(props)
