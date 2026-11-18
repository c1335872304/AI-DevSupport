import json

from app.agent.document_context import filter_document_absence_claims, pack_document_context


def source(ref, version="v1", document="doc"):
    return {
        "referenceNumber": ref,
        "fileMd5": document,
        "fileName": document + ".md",
        "indexVersion": version,
        "citationId": "SIGNED-SECRET-" + str(ref),
        "chunkId": ref,
    }


def context(*texts, versions=None, documents=None, question="Qwen API Base URL如何配置？", budget=18000):
    refs = [
        source(i + 1, (versions or ["v1"] * len(texts))[i], (documents or ["doc"] * len(texts))[i])
        for i in range(len(texts))
    ]
    evidence = {"knowledgeExcerpts": [{"source": ref, "text": text} for ref, text in zip(refs, texts)]}
    return pack_document_context(question, evidence, refs, budget), refs


def test_signed_metadata_stays_server_side_and_same_version_duplicate_merges():
    text = "Base URL配置应当匹配地域和同一计费方案。"
    packed, refs = context(text, text)
    assert packed.bounded
    prompt = json.dumps(packed.messages, ensure_ascii=False)
    assert "SIGNED-SECRET" not in prompt and "indexVersion" not in prompt and "fileMd5" not in prompt
    assert sum(m["content"].count(text) for m in packed.messages) == 1
    assert packed.references == refs
    assert packed.metrics["deduplicatedBlocks"] > 0


def test_identical_words_do_not_merge_across_versions_or_documents():
    for kwargs in [{"versions": ["v1", "v2"]}, {"documents": ["a", "b"]}]:
        packed, _ = context("Base URL配置必须正确。", "Base URL配置必须正确。", **kwargs)
        assert len(json.loads(packed.messages[1]["content"])["excerpts"]) == 2


def test_qualifier_after_unrelated_section_and_adjacent_explanation_survive():
    packed, _ = context(
        "Base URL配置方法。",
        "无关说明。\n\n另一个话题。\n\n仅限北京地域和同一计费方案。\n\n套餐密钥另有专用地址。",
    )
    assert packed.bounded
    text = packed.messages[1]["content"]
    assert "仅限北京地域和同一计费方案" in text and "套餐密钥另有专用地址" in text


def test_budget_overflow_falls_back_without_cutting_a_requirement():
    packed, refs = context("Base URL必须匹配地域。" * 100, budget=400)
    assert not packed.bounded and not packed.messages and packed.references == refs
    assert packed.metrics["fallback"] == "required_evidence_exceeds_budget"


def test_fenced_example_kept_whole_and_unmatched_document_not_cited():
    code = '```python\n\nurl = "https://example.test/v1"\n\n```'
    packed, _ = context("Base URL配置：\n\n" + code, "遥远的话题。\n\n又一段没有相关内容。")
    assert packed.bounded and code in json.loads(packed.messages[1]["content"])["excerpts"][1]["text"]
    assert [r["referenceNumber"] for r in packed.references] == [1]


def test_substantial_overlap_merges_without_changing_text_or_source_links():
    overlap = "Base URL适用于北京地域，必须匹配同一计费方案。" * 5
    packed, refs = context("前文。" + overlap, overlap + "后文。")
    assert packed.bounded
    payload = json.loads(packed.messages[1]["content"])
    assert len(payload["excerpts"]) == 1
    assert payload["excerpts"][0]["text"] == "前文。" + overlap + "后文。"
    assert payload["excerpts"][0]["refs"] == [1, 2] and packed.references == refs


def test_unknown_citation_does_not_produce_an_untraceable_prompt():
    result = pack_document_context(
        "Qwen配置", {"knowledgeExcerpts": [{"source": source(9), "text": "Base URL配置。"}]}, [source(1)]
    )
    assert not result.bounded and result.metrics["fallback"] == "unmapped_source"


def test_different_code_indentation_is_not_treated_as_duplicate_evidence():
    packed, _ = context(
        "```python\nif enabled:\n    configure()\n```",
        "Base URL示例：\n\n```python\nif enabled:\nconfigure()\n```",
    )
    blocks = json.loads(packed.messages[1]["content"])["excerpts"]
    assert any("    configure()" in b["text"] for b in blocks)
    assert any("\nconfigure()" in b["text"] for b in blocks)


def test_excerpt_guard_removes_global_absence_but_preserves_grounded_rule_and_uncertainty():
    answer = "Base URL必须匹配同一计费方案。文档未说明存在其他方案。当前检索片段不足以确认更多细节。"
    guarded, removed = filter_document_absence_claims(answer)
    assert removed == 1 and "文档未说明" not in guarded
    assert "必须匹配同一计费方案" in guarded and "当前检索片段不足以确认" in guarded


def test_excerpt_guard_preserves_code_and_does_not_leave_an_empty_answer():
    code = '```python\nmessage = "文档未说明"\n```'
    assert filter_document_absence_claims(code) == (code, 0)
    answer, removed = filter_document_absence_claims("The documentation does not provide this parameter.")
    assert removed == 1 and "检索片段不足" in answer


def test_containment_does_not_erase_a_different_negation_or_scope():
    positive = "支持Base URL配置参数。" * 10
    packed, _ = context("不" + positive, positive)
    assert packed.bounded
    blocks = json.loads(packed.messages[1]["content"])["excerpts"]
    assert len(blocks) == 2
    assert blocks[0]["text"].startswith("不支持") and blocks[1]["text"].startswith("支持")
