"""Download a curated, official-only API documentation corpus for local RAG.

No model calls, database writes, credential loading, or unrestricted crawling.
Native Markdown is retained; HTML pages are converted from the article body.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "vendor_knowledge"
SCOPES = {
    "gpt": ("developers.openai.com", "/api/", "OpenAI", "OpenAI API"),
    "qwen": ("help.aliyun.com", "/zh/model-studio/", "Alibaba Cloud", "Qwen API"),
    "deepseek": ("api-docs.deepseek.com", "/", "DeepSeek", "DeepSeek API"),
}


def check_url(url: str, provider: str) -> None:
    host, prefix, _, _ = SCOPES[provider]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != host or not parsed.path.startswith(prefix):
        raise ValueError(f"URL outside official source scope: {url}")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and custom ports are not allowed in source URLs")


def article_markdown(raw: str, url: str) -> tuple[str, str]:
    soup = BeautifulSoup(raw, "html.parser")
    article = soup.select_one(".theme-doc-markdown") or soup.select_one("article")
    if article is None:
        raise ValueError("No document article found; refusing navigation-only page")
    title_tag = article.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""
    if not title:
        raise ValueError("Article has no title")
    for tag in article.select("script,style,nav,button,.hash-link,.theme-edit-this-page"):
        tag.decompose()
    for tag in list(article.find_all("pre")):
        code = tag.find("code") or tag
        classes = " ".join(code.get("class", []))
        language = re.search(r"language-([\w+-]+)", classes)
        text = code.get_text("", strip=False)
        # Code may itself contain triple fences.
        fence = "`" * max(3, max((len(m[0]) + 1 for m in re.finditer(r"`{3,}", text)), default=3))
        tag.replace_with(f"\n\n{fence}{language[1] if language else ''}\n{text}\n{fence}\n\n")
    for tag in list(article.find_all("table")):
        rows = [[cell.get_text(" ", strip=True).replace("|", "\\|").replace("\n", " ")
                 for cell in row.find_all(["th", "td"], recursive=False)] for row in tag.find_all("tr")]
        rows = [row for row in rows if row]
        if rows:
            width = max(map(len, rows))
            rows = [row + [""] * (width - len(row)) for row in rows]
            lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
            lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
            tag.replace_with("\n\n" + "\n".join(lines) + "\n\n")
    for tag in list(article.find_all("a", href=True)):
        text = tag.get_text(" ", strip=True)
        link = urljoin(url, tag["href"])
        tag.replace_with(f"[{text}]({link})" if text else "")
    for tag in list(article.find_all("code")):
        tag.replace_with("`" + tag.get_text() + "`")
    for tag in list(article.find_all(re.compile(r"^h[1-6]$"))):
        tag.replace_with("\n\n" + "#" * int(tag.name[1]) + " " + tag.get_text(" ", strip=True) + "\n\n")
    for tag in list(article.find_all("li")):
        tag.insert_before("\n- ")
        tag.append("\n")
    for tag in list(article.find_all(["p", "section", "blockquote"])):
        tag.insert_before("\n\n")
        tag.append("\n\n")
    for tag in list(article.find_all("br")):
        tag.replace_with("\n")
    body = article.get_text("", strip=False)
    return title, re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", body).strip()


async def fetch(client: httpx.AsyncClient, url: str, provider: str) -> httpx.Response:
    for _ in range(6):
        check_url(url, provider)
        response = await client.get(url)
        if response.is_redirect:
            url = urljoin(url, response.headers["location"])
            continue
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            raise ValueError("Documentation response exceeds 8 MB")
        return response
    raise ValueError("Too many source redirects")


async def collect(catalog_path: Path, output: Path, checked_at: str) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    sources = catalog["sources"]
    identifiers = [item["id"] for item in sources]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate source IDs")
    for item in sources:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]+", item["id"]):
            raise ValueError("Invalid source ID")
        check_url(item["url"], item["provider"])
        check_url(item.get("downloadUrl", item["url"]), item["provider"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw").mkdir(exist_ok=True)
    semaphore = asyncio.Semaphore(3)
    documents, failures = [], []
    async with httpx.AsyncClient(timeout=45, follow_redirects=False,
                                 headers={"User-Agent": "API-Assistant-Demo-Docs/1.0"}) as client:
        async def one(item: dict) -> None:
            async with semaphore:
                try:
                    response = await fetch(client, item.get("downloadUrl", item["url"]), item["provider"])
                    content_type = response.headers.get("content-type", "")
                    native = "markdown" in content_type
                    if native:
                        body = response.text.strip()
                        title_match = re.search(r"(?m)^#\s+(.+)$", body)
                        if not title_match or "<!doctype html" in body[:200].lower():
                            raise ValueError("Native Markdown title missing or HTML error page returned")
                        title = title_match[1].strip()
                    else:
                        if item["provider"] != "deepseek":
                            raise ValueError("Expected official Markdown; HTML fallback is not accepted")
                        title, body = article_markdown(response.text, str(response.url))
                    if len(body) < item.get("minChars", 200):
                        raise ValueError(f"Document body too short: {len(body)} characters")
                    if item.get("expectedTitle") and not re.search(item["expectedTitle"], title, re.I):
                        raise ValueError(f"Unexpected title for source {item['id']}: {title}")
                    provider = item["provider"]
                    _, _, vendor, product = SCOPES[provider]
                    header = (f"# {item['label']}\n\n"
                              f"厂商：{vendor}；产品范围：{product}；核对日期：{checked_at}。\n"
                              f"官方来源：[{title}]({item['url']})。\n"
                              "内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。\n"
                              "资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。\n\n---\n\n")
                    payload = (header + body + "\n").encode("utf-8")
                    filename = item["id"] + ".md"
                    raw_name = item["id"] + (".md" if native else ".html")
                    (output / "raw" / raw_name).write_bytes(response.content)
                    (output / filename).write_bytes(payload)
                    documents.append({"file": filename, "vendor": vendor, "provider": provider,
                                      "sourceUrl": item["url"], "downloadUrl": str(response.url),
                                      "checkedAt": checked_at, "contentType": "official_body_snapshot",
                                      "extraction": "native_markdown" if native else "html_article_to_markdown",
                                      "sourceTitle": title, "rawFile": "raw/" + raw_name,
                                      "rawSha256": hashlib.sha256(response.content).hexdigest(),
                                      "bodySha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                                      "sha256": hashlib.sha256(payload).hexdigest(),
                                      "bodyChars": len(body), "bytes": len(payload),
                                      "metadata": {"product": product, "category": item["category"],
                                                   "channel": "api", "version": "snapshot-" + checked_at},
                                      "sampleQuestions": item.get("sampleQuestions", [])})
                    print(json.dumps({"id": item["id"], "status": "ok", "bodyChars": len(body)}, ensure_ascii=True), flush=True)
                except Exception as exc:
                    failures.append({"id": item["id"], "url": item["url"], "error": str(exc)[:500]})
                    print(json.dumps({"id": item["id"], "status": "failed", "error": str(exc)[:200]}, ensure_ascii=True), flush=True)
        await asyncio.gather(*(one(item) for item in sources))
    documents.sort(key=lambda item: identifiers.index(item["file"][:-3]))
    hashes: dict[str, str] = {}
    for document in documents:
        prior = hashes.get(document["bodySha256"])
        if prior:
            failures.append({"id": document["file"], "error": f"Duplicate body of {prior}; inspect fallback redirects"})
        hashes[document["bodySha256"]] = document["file"]
    report = {"checkedAt": checked_at, "requested": len(sources), "collected": len(documents),
              "totalBodyChars": sum(item["bodyChars"] for item in documents),
              "failures": failures,
              "byProvider": {key: {"documents": sum(item["provider"] == key for item in documents),
                                    "bodyChars": sum(item["bodyChars"] for item in documents if item["provider"] == key)}
                             for key in SCOPES}}
    (output / "collection-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not failures:
        manifest = {"version": 2, "description": "Official body snapshots for GPT/OpenAI, Qwen and DeepSeek; not summaries.",
                    "checkedAt": checked_at, "evaluationDataset": "eval/vendor_full_rag.jsonl", "documents": documents}
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output / "manifest.json")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_DIR / "sources.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--checked-at", required=True, help="Date of the actual source review, YYYY-MM-DD")
    args = parser.parse_args()
    from datetime import date
    date.fromisoformat(args.checked_at)
    report = asyncio.run(collect(args.catalog, args.output_dir, args.checked_at))
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(1 if report["failures"] else 0)
