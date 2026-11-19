import copy
import json

from app.agent.document_context import pack_document_context, relabel_evidence


def record(ref, name, chunk=0, version="v1", text="Base URL必须匹配同一地域。"):
    source = {
        "referenceNumber": ref,
        "fileName": name,
        "fileMd5": name,
        "indexVersion": version,
        "chunkId": chunk,
        "citationId": f"signed-{name}-{ref}",
    }
    return {"source": source, "text": text}


def pack(records, question="Qwen Base URL如何配置？"):
    return pack_document_context(question, {"knowledgeExcerpts": records}, [r["source"] for r in records])


def test_equal_selected_sources_have_identical_prompts_despite_rank_ref_and_signature_changes():
    original = [record(1, "z.md", 2), record(2, "a.md", 10), record(3, "a.md", 2)]
    shuffled = copy.deepcopy([original[2], original[0], original[1]])
    for number, item in enumerate(shuffled, 1):
        item["source"]["referenceNumber"] = number
        item["source"]["citationId"] = f"refreshed-{number}"
    first, second = pack(original), pack(shuffled)
    assert first.bounded and second.bounded
    assert first.messages == second.messages
    assert first.metrics["documentPrefixSha256"] == second.metrics["documentPrefixSha256"]
    assert [(r["fileName"], r["chunkId"]) for r in first.references] == [
        ("a.md", 2),
        ("a.md", 10),
        ("z.md", 2),
    ]
    assert first.reference_remap == {3: 1, 2: 2, 1: 3}
    assert all("refreshed" not in m["content"] and "signed-" not in m["content"] for m in second.messages)


def test_documents_precede_question_and_changing_only_question_keeps_full_document_prefix():
    records = [record(1, "a.md"), record(2, "b.md")]
    first = pack(records, "Qwen Base URL如何配置？")
    second = pack(records, "Qwen API Key怎样设置？")
    payload = json.loads(first.messages[1]["content"])
    assert list(payload) == ["sources", "excerpts", "question"]
    assert first.messages[0] == second.messages[0]
    assert first.metrics["documentPrefixSha256"] == second.metrics["documentPrefixSha256"]
    prefix_size = first.metrics["documentPrefixBytes"]
    assert (
        first.messages[1]["content"].encode()[:prefix_size]
        == second.messages[1]["content"].encode()[:prefix_size]
    )


def test_canonicalization_never_changes_which_primary_excerpt_is_fully_selected():
    primary = record(1, "z.md", text="主段一。\n\n独特尾段。\n\n第三主段。")
    secondary = record(2, "a.md")
    result = pack([primary, secondary])
    assert result.bounded
    content = result.messages[1]["content"]
    assert all(part in content for part in ["主段一", "独特尾段", "第三主段"])
    assert result.references[0]["fileName"] == "a.md"


def test_final_evidence_and_signed_citation_mapping_are_relabelled_together_without_mutation():
    records = [record(1, "z.md"), record(2, "a.md")]
    evidence = {
        "knowledgeExcerpts": records,
        "citations": [r["source"] for r in records],
        "verifiedFacts": [],
        "unresolvedItems": [],
    }
    saved = copy.deepcopy(evidence)
    result = pack(records)
    relabelled = relabel_evidence(evidence, result.references, result.reference_remap)
    assert evidence == saved
    mapping = {r["referenceNumber"]: r for r in relabelled["citations"]}
    for excerpt in relabelled["knowledgeExcerpts"]:
        assert excerpt["source"]["citationId"] == mapping[excerpt["source"]["referenceNumber"]]["citationId"]
        assert excerpt["source"]["fileName"] == mapping[excerpt["source"]["referenceNumber"]]["fileName"]
    assert result.references[0]["citationId"] == records[1]["source"]["citationId"]


def test_version_change_changes_document_prefix_and_never_merges_versions():
    records = [record(1, "a.md", version="v1"), record(2, "a.md", version="v2")]
    result = pack(records)
    assert len(result.references) == 2
    assert len(json.loads(result.messages[1]["content"])["excerpts"]) == 2
    # Different evidence sets are allowed to have different contiguous numbers.
    only_v2 = pack([records[1]])
    assert only_v2.references[0]["referenceNumber"] == 1
    assert only_v2.metrics["documentPrefixSha256"] != result.metrics["documentPrefixSha256"]


def test_identical_identity_with_ambiguous_citations_uses_original_contract():
    first, second = record(1, "a.md"), record(2, "a.md")
    result = pack([first, second])
    assert not result.bounded and result.metrics["fallback"] == "ambiguous_source_identity"
    assert result.references == [first["source"], second["source"]]


def test_overlap_merge_is_stable_when_the_selected_source_order_is_reversed():
    overlap = "Base URL必须匹配地域。" * 10
    records = [record(1, "a.md", 0, text="前文。" + overlap), record(2, "a.md", 1, text=overlap + "后文。")]
    a, b = pack(records), pack(list(reversed(records)))
    assert a.messages == b.messages
    assert "前文。" + overlap + "后文。" in json.loads(a.messages[1]["content"])["excerpts"][0]["text"]
