from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from scripts.collect_vendor_knowledge import article_markdown, check_url, fetch
from scripts.seed_demo_knowledge import load_manifest


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "vendor_knowledge"


def test_full_corpus_has_only_requested_providers_and_verified_originals():
    manifest = load_manifest(CORPUS / "manifest.json")
    documents = manifest["documents"]
    assert Counter(item["provider"] for item in documents) == {"deepseek": 20, "qwen": 20, "gpt": 20}
    assert len({item["bodySha256"] for item in documents}) == len(documents)
    assert sum(item["bodyChars"] for item in documents) > 2_000_000
    for item in documents:
        check_url(item["sourceUrl"], item["provider"])
        check_url(item["downloadUrl"], item["provider"])
        raw = (CORPUS / item["rawFile"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["rawSha256"]
        assert item["contentType"] == "official_body_snapshot"
        stored = (CORPUS / item["file"]).read_text(encoding="utf-8")
        body = stored.split("\n---\n\n", 1)[1].strip()
        assert hashlib.sha256(body.encode("utf-8")).hexdigest() == item["bodySha256"]
        if item["extraction"] == "native_markdown":
            assert body == raw.decode("utf-8").strip()


def test_article_conversion_keeps_code_headings_tables_and_absolute_links():
    html = '''<nav>unwanted navigation</nav><article><div class="theme-doc-markdown">
    <h1>Tool calls<a class="hash-link">#</a></h1><h2>Example</h2>
    <pre><code class="language-python">if True:\n    print("ok")</code></pre>
    <table><tr><th>Field</th><th>Type</th></tr><tr><td>tools</td><td>array</td></tr></table>
    <p>Read <a href="/guides/tool_calls">guide</a>.</p></div></article>'''
    title, body = article_markdown(html, "https://api-docs.deepseek.com/api/example")
    assert title.startswith("Tool calls")
    assert "unwanted navigation" not in body
    assert "## Example" in body
    assert '```python\nif True:\n    print("ok")\n```' in body
    assert "| tools | array |" in body
    assert "[guide](https://api-docs.deepseek.com/guides/tool_calls)" in body
    with pytest.raises(ValueError, match="No document article"):
        article_markdown("<nav>home</nav>", "https://api-docs.deepseek.com/")


@pytest.mark.asyncio
async def test_collector_refuses_redirects_outside_vendor_scope():
    visited = []

    def handler(request):
        visited.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.com/not-official"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="outside official source scope"):
            await fetch(client, "https://developers.openai.com/api/docs/quickstart.md", "gpt")
    assert len(visited) == 1


def test_full_corpus_eval_cases_reference_selected_documents():
    manifest = load_manifest(CORPUS / "manifest.json")
    shipped = {item["file"] for item in manifest["documents"]}
    cases = [json.loads(line) for line in (ROOT / manifest["evaluationDataset"]).read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 120
    assert {case["expectedFileName"] for case in cases} == shipped
    assert Counter(case["caseType"] for case in cases) == {"filtered_smoke": 60, "unfiltered_query": 60}
    assert all(case["filters"]["product"] for case in cases if case["caseType"] == "filtered_smoke")
    assert all("filters" not in case for case in cases if case["caseType"] == "unfiltered_query")
