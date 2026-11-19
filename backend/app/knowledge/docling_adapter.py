"""Bounded subprocess adapter. Never silently falls back after conversion failure."""

import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from pypdf import PdfReader
from app.core.config import get_settings

DOCLING_VERSION = "2.58.0"


def artifacts_directory():
    configured = get_settings().docling_artifacts_path
    if configured:
        return Path(configured)
    cached = Path(__file__).resolve().parents[2] / "data/models/docling"
    return cached if (cached / "manifest.json").is_file() else None


def convert_document(filename, data):
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    if len(data) > settings.document_parse_max_bytes:
        raise ValueError("PARSE_LIMIT: document exceeds byte limit")
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("PARSE_TYPE: invalid PDF signature")
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("PARSE_ENCRYPTED: encrypted PDF is unsupported")
        if len(reader.pages) > settings.document_parse_max_pages:
            raise ValueError("PARSE_LIMIT: too many PDF pages")
        if not any((p.extract_text() or "").strip() for p in reader.pages):
            raise ValueError("OCR_REQUIRED: scanned or empty PDF is outside the first release")
    elif suffix == ".docx":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("PARSE_TYPE: not a Word OOXML document")
            if sum(i.file_size for i in archive.infolist()) > settings.document_parse_max_bytes * 10:
                raise ValueError("PARSE_LIMIT: decompressed DOCX exceeds limit")
    root = Path(__file__).resolve().parents[2]
    bundled = root / ".venv-docling" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = settings.docling_python or (str(bundled) if bundled.is_file() else sys.executable)
    worker = Path(__file__).with_name("docling_worker.py")
    env = os.environ.copy()
    env["DOCLING_MAX_MEMORY_MB"] = str(settings.document_parse_max_memory_mb)
    artifacts = artifacts_directory()
    if suffix == ".pdf" and artifacts is None:
        raise RuntimeError("PARSE_MODELS_MISSING: prefetch pinned Docling models before PDF parsing")
    if artifacts:
        env["DOCLING_ARTIFACTS_PATH"] = str(artifacts.resolve())
        env["HF_HUB_OFFLINE"] = "1"
    # Conversion does not need the application's provider credentials.
    for key in list(env):
        if any(secret in key.upper() for secret in ("API_KEY", "SECRET", "PASSWORD", "TOKEN")):
            env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="rag-parse-") as directory:
        source = Path(directory) / ("input" + suffix)
        output = Path(directory) / "result.json"
        source.write_bytes(data)
        try:
            result = subprocess.run(
                [python, str(worker), str(source), str(output)],
                env=env,
                capture_output=True,
                timeout=settings.document_parse_timeout_seconds,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("PARSE_TIMEOUT: Docling exceeded configured time limit") from exc
        if result.returncode == 137:
            raise RuntimeError("PARSE_RESOURCE: Docling memory budget exceeded")
        if result.returncode or not output.is_file():
            # Preserve useful diagnostics without embedding source text in application logs.
            diagnostic = result.stderr.decode("utf-8", errors="replace")[-1500:]
            raise RuntimeError("PARSE_BACKEND: Docling conversion failed: " + diagnostic)
        parsed = json.loads(output.read_text(encoding="utf-8"))
    if not parsed.get("blocks"):
        raise ValueError("PARSE_EMPTY: no usable Docling content")
    return parsed
