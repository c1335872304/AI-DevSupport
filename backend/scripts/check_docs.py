"""Validate local Markdown links in README/docs without network or app startup."""

from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", action="store_true", help="Allow missing generated backend/data evidence")
    options = parser.parse_args()
    files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), ROOT / "backend/scripts/README.md"]
    failures = []
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
            if url.scheme or url.netloc or not url.path:
                continue
            links += 1
            path = unquote(url.path)
            destination = (ROOT / path.lstrip("/")) if path.startswith("/") else source.parent / path
            if not destination.exists():
                if options.checkout and destination.resolve().is_relative_to(ROOT / "backend" / "data"):
                    absent_evidence += 1
                    continue
                failures.append(f"{source.relative_to(ROOT)}: missing {target}")
    print(f"Checked {len(files)} Markdown files and {links} local links (targets only; no anchor/remote validation).")
    if absent_evidence:
        print(f"Skipped {absent_evidence} absent generated evidence links in backend/data.")
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
