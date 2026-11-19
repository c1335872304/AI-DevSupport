from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from openpyxl import load_workbook
from pptx import Presentation

from app.core.config import get_settings


@dataclass
class ParsedBlock:
    text: str
    page_number: int | None = None
    location: dict | None = None


@dataclass
class ParentChunkDraft:
    parent_chunk_id: int
    text: str
    page_number: int | None = None
    location: dict | None = None


@dataclass
class ChildChunkDraft(ParsedBlock):
    parent_chunk_id: int = 0


class DocumentParser:
    def profile(self) -> dict:
        import hashlib
        from app.knowledge.docling_adapter import artifacts_directory
        artifacts = artifacts_directory()
        manifest = artifacts / "manifest.json" if artifacts else None
        return {"adapter": "structured-v3", "docling": "2.58.0", "ocr": False,
                "artifacts_path": str(artifacts) if artifacts else None,
                "model_manifest": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest and manifest.is_file() else None,
                "chunk_size": self.settings.chunk_size, "min_chunk_size": self.settings.min_chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "parent_chunk_size": self.settings.parent_chunk_size}

    def __init__(self) -> None:
        self.settings = get_settings()

    def parse(self, filename: str, data: bytes) -> list[ParsedBlock]:
        suffix = Path(filename).suffix.lower()
        if suffix in {".pdf", ".docx"}:
            return self.parse_with_artifacts(filename, data)[0]
        if suffix in {".xlsx", ".xlsm"}:
            return self._xlsx(data)
        if suffix == ".pptx":
            return self._pptx(data)
        if suffix in {".html", ".htm"}:
            soup = BeautifulSoup(data, "html.parser")
            for tag in soup(["script", "style", "nav"]): tag.decompose()
            return self._markdown(soup.get_text("\n"))
        if suffix == ".md":
            return self._markdown(data.decode("utf-8", errors="strict"))
        if suffix in {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".xml", ".log"}:
            return [ParsedBlock(data.decode("utf-8", errors="ignore"))]
        return [ParsedBlock(data.decode("utf-8", errors="ignore"))]

    @staticmethod
    def _markdown(text):
        blocks, headings, buffer = [], [], []
        fence, kind, offset, start = None, "text", 0, 0
        def flush():
            nonlocal buffer, start
            value = "".join(buffer).strip()
            if value:
                blocks.append(ParsedBlock(value, location={"blockId": f"md:{len(blocks)}", "type": kind,
                    "titlePath": list(headings), "order": len(blocks), "charStart": start, "charEnd": offset}))
            buffer = []
            start = offset
        for line in text.splitlines(keepends=True):
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            heading = re.match(r"^(#{1,6})\s+(.+)", line)
            is_table = line.lstrip().startswith("|")
            if fence:
                buffer.append(line); offset += len(line)
                if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                    flush(); fence = None; kind = "text"
                continue
            if marker:
                flush(); fence = marker[1]; kind = "code"; start = offset
            elif heading:
                flush(); level = len(heading[1]); headings = headings[:level-1] + [heading[2].strip()]
                kind = "text"; start = offset
            elif is_table and kind != "table":
                flush(); kind = "table"; start = offset
            elif not is_table and kind == "table":
                flush(); kind = "text"; start = offset
            buffer.append(line); offset += len(line)
        flush()
        return blocks

    def parse_with_artifacts(self, filename, data):
        if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
            return self.parse(filename, data), None
        from app.knowledge.docling_adapter import convert_document
        result = convert_document(filename, data)
        return [ParsedBlock(b["text"], b.get("page_number"), b.get("location")) for b in result["blocks"]], result

    def chunk(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Backward-compatible child-only chunking API."""
        _, children = self.hierarchical_chunk(blocks)
        return [ParsedBlock(item.text, item.page_number) for item in children]

    def hierarchical_chunk(self, blocks: list[ParsedBlock]) -> tuple[list[ParentChunkDraft], list[ChildChunkDraft]]:
        """Build parent/child chunks without changing the existing vector table schema.

        Parent chunks preserve enough context for answer generation. Child chunks stay small
        and are the only chunks embedded/searched. Parent ids are local to one file and are
        persisted separately with the child-id range they cover.
        """
        parent_size = max(300, self.settings.parent_chunk_size)
        child_size = max(100, self.settings.chunk_size)
        child_overlap = min(max(0, self.settings.chunk_overlap), child_size // 2)
        min_chunk_size = min(max(1, self.settings.min_chunk_size), child_size)

        parents: list[ParentChunkDraft] = []
        children: list[ChildChunkDraft] = []
        parent_id = 0
        for block in blocks:
            text = self._normalize_text(block.text)
            if not text:
                continue
            parent_pieces = self._split_text(text, parent_size, 0, min_chunk_size=min(parent_size // 4, 240))
            for parent_text in parent_pieces:
                current_parent_id = parent_id
                parent_id += 1
                parents.append(ParentChunkDraft(current_parent_id, parent_text, block.page_number, block.location))
                child_pieces = [parent_text] if block.location and block.location.get("type") in {"code", "table"} and len(parent_text) <= parent_size else self._split_text(
                    parent_text,
                    child_size,
                    child_overlap,
                    min_chunk_size=min_chunk_size,
                )
                for child_text in child_pieces:
                    children.append(
                        ChildChunkDraft(
                            text=child_text,
                            page_number=block.page_number,
                            location=block.location,
                            parent_chunk_id=current_parent_id,
                        )
                    )
        return parents, children

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_text(self, text: str, size: int, overlap: int, *, min_chunk_size: int) -> list[str]:
        if len(text) <= size:
            return [text] if text else []

        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                boundary = self._best_boundary(text, start, end, size)
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)
            if end >= len(text):
                break
            next_start = max(start + 1, end - overlap)
            # Skip leading whitespace but never skip past the chosen boundary content.
            while next_start < len(text) and text[next_start].isspace() and next_start < end:
                next_start += 1
            start = next_start

        # Merge a tiny tail into the previous piece when possible. This avoids isolated
        # headings/page fragments becoming low-value retrieval entries.
        if len(pieces) >= 2 and len(pieces[-1]) < min_chunk_size:
            merged = (pieces[-2].rstrip() + "\n" + pieces[-1].lstrip()).strip()
            if len(merged) <= int(size * 1.35):
                pieces[-2:] = [merged]
        return pieces

    @staticmethod
    def _best_boundary(text: str, start: int, end: int, size: int) -> int:
        lower = start + max(1, size // 2)
        if lower >= end:
            return end
        candidates: list[int] = []
        for marker in ("\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", "; ", "，", ", "):
            pos = text.rfind(marker, lower, end)
            if pos >= lower:
                candidates.append(pos + len(marker))
                # Strong structural boundaries win immediately.
                if marker in {"\n\n", "\n", "。", "！", "？", ". ", "! ", "? "}:
                    break
        return max(candidates, default=end)

    @staticmethod
    def _xlsx(data: bytes) -> list[ParsedBlock]:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        blocks: list[ParsedBlock] = []
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append("\t".join("" if v is None else str(v) for v in row))
            blocks.append(ParsedBlock(f"# {ws.title}\n" + "\n".join(rows)))
        return blocks

    @staticmethod
    def _pptx(data: bytes) -> list[ParsedBlock]:
        prs = Presentation(io.BytesIO(data))
        blocks: list[ParsedBlock] = []
        for i, slide in enumerate(prs.slides, start=1):
            texts = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
            blocks.append(ParsedBlock("\n".join(texts), i))
        return blocks


parser_service = DocumentParser()
