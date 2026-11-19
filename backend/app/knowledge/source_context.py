"""Restore source qualifiers from the same persisted document revision.

Legacy chunks split JSX tabs and HTML tables away from their region and unit
headers. Read the ordered parents, never a mutable upload or another revision.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db.models import DocumentParentChunk

_TOKENS = re.compile(
    r'(?P<tab><Tab\b[^>]*\btitle=["\'](?P<title>[^"\']+)["\'][^>]*>)'
    r'|(?P<endtab></Tab\s*>)|(?P<table><table\b[^>]*>)'
    r'|(?P<header><thead\b[^>]*>[\s\S]*?</thead\s*>)|(?P<endtable></table\s*>)'
    r'|(?P<heading>^#{1,6}\s+[^\n]+)', re.M,
)


def parent_contexts(parents) -> dict[int, str]:
    """Repeat inherited tab, heading and table headers at each parent boundary."""
    rows = sorted(parents, key=lambda row: row.parent_chunk_id)
    text, spans = "", []
    for row in rows:
        spans.append((row, len(text)))
        text += row.text_content + "\n\n"
    # Code examples are evidence, not structural tab/heading declarations.
    structural = re.sub(r'(?m)^\s*(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\s*\1[^\n]*$',
                        lambda match: re.sub(r'[^\n]', ' ', match[0]), text)
    tokens = iter(_TOKENS.finditer(structural))
    current = next(tokens, None)
    tabs, headings, header = [], [], ""
    contexts = {}
    provenance = next((line.strip() for line in structural.splitlines()[:12]
                       if '核对日期' in line and len(line) <= 256), '')
    for row, start in spans:
        while current is not None and current.end() <= start:
            if current.group('tab'):
                tabs.append(current.group('title'))
            elif current.group('endtab'):
                if tabs:
                    tabs.pop()
            elif current.group('heading'):
                level, title = current[0].split(maxsplit=1)
                headings = headings[:len(level) - 1] + [title]
            elif current.group('header'):
                soup = BeautifulSoup(current[0], 'html.parser')
                header = ' | '.join(cell.get_text(' ', strip=True) for cell in soup.find_all(['th', 'td']))
            elif current.group('table') or current.group('endtable'):
                header = ""
            current = next(tokens, None)
        prefix = []
        if provenance:
            prefix.append(provenance)
        if tabs:
            prefix.append('原文适用范围：' + ' / '.join(tabs))
        if headings and (tabs or header):
            prefix.append('原文章节：' + ' / '.join(headings))
        if header:
            prefix.append('原文表头（含单位）：' + header)
        contexts[row.parent_chunk_id] = '\n'.join([*prefix, row.text_content])
    return contexts


async def load_parent_contexts(db, owner: str, file_md5: str, version: str):
    rows = list((await db.scalars(select(DocumentParentChunk).where(
        DocumentParentChunk.user_id == owner,
        DocumentParentChunk.file_md5 == file_md5,
        DocumentParentChunk.vector_version == version,
    ).order_by(DocumentParentChunk.parent_chunk_id))).all())
    return rows, parent_contexts(rows)
