"""Validate daily manuals and archived Markdown links without network or app startup."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def without_code(text: str) -> str:
    lines = []
    fence = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    if fence is not None:
        raise ValueError("unclosed code fence")
    return "\n".join(lines)


def markdown_anchors(text: str) -> set[str]:
    """Recognize explicit anchors and GitHub-style heading identifiers."""
    content = without_code(text)
    anchors = set(re.findall(r"<(?:a|h[1-6])\b[^>]*\b(?:id|name)=[\"']([^\"']+)[\"']", content, re.IGNORECASE))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", content, re.MULTILINE):
        heading = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", html.unescape(heading))
        slug = re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
        duplicate = counts.get(slug, 0)
        counts[slug] = duplicate + 1
        anchors.add(slug if duplicate == 0 else f"{slug}-{duplicate}")
    return anchors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", action="store_true", help="Allow missing generated backend/data evidence")
    options = parser.parse_args()
    files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), ROOT / "backend/scripts/README.md"]
    failures = []
    daily_count = len(list((ROOT / "docs").glob("*.md")))
    if not 5 <= daily_count <= 8:
        failures.append(f"docs/: expected 5–8 daily manuals, found {daily_count}")
    anchor_cache: dict[Path, set[str]] = {}
    links = 0
    absent_evidence = 0
    for source in files:
        try:
            text = without_code(source.read_text(encoding="utf-8"))
        except ValueError as exc:
            failures.append(f"{source.relative_to(ROOT)}: {exc}")
            continue
        for match in LINK.finditer(text):
            target = match[1].strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc or not (url.path or url.fragment):
                continue
            links += 1
            path = unquote(url.path)
            if not path:
                destination = source
            elif path.startswith("/"):
                destination = ROOT / path.lstrip("/")
            else:
                destination = source.parent / path
            destination = destination.resolve()
            if not destination.exists():
                if options.checkout and destination.resolve().is_relative_to(ROOT / "backend" / "data"):
                    absent_evidence += 1
                    continue
                failures.append(f"{source.relative_to(ROOT)}: missing {target}")
                continue
            if url.fragment and destination.suffix.lower() == ".md":
                if destination not in anchor_cache:
                    anchor_cache[destination] = markdown_anchors(destination.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in anchor_cache[destination]:
                    failures.append(f"{source.relative_to(ROOT)}: missing anchor {target}")
    print(f"Checked {daily_count} daily manuals, {len(files)} Markdown files and {links} local links (including Markdown anchors; no remote validation).")
    if absent_evidence:
        print(f"Skipped {absent_evidence} absent generated evidence links in backend/data.")
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
