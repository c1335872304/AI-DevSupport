"""Remove exact shipped fictional documents from the local demo, with a backup.

Intentionally limited to SQLite, local storage and database retrieval. Other
deployments need their own index cleanup rather than silently leaving ES rows.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from sqlalchemy.engine import make_url
    from app.core.config import get_settings

    settings = get_settings()
    url = make_url(settings.database_url)
    if (url.get_backend_name(), settings.storage_backend, settings.search_backend) != ("sqlite", "local", "database"):
        raise RuntimeError("This cleanup supports only the local SQLite/database demo")
    source = Path(url.database).resolve()
    if not source.is_file() or not source.is_relative_to(ROOT):
        raise RuntimeError("Expected an existing database inside backend")
    storage = settings.storage_path.resolve()
    if not storage.is_relative_to(ROOT):
        raise RuntimeError("Expected local storage inside backend")
    legacy = json.loads((ROOT / "demo_knowledge/manifest.json").read_text(encoding="utf-8"))
    official = json.loads((ROOT / "vendor_knowledge/manifest.json").read_text(encoding="utf-8"))
    backup_dir = ROOT / "data/backups" / f"legacy-removal-{uuid.uuid4().hex}"
    backup_dir.mkdir(parents=True)
    report = {"backup": str(backup_dir.relative_to(ROOT)), "removed": [], "deletedRows": {}}
    with sqlite3.connect(source) as db:
        db.row_factory = sqlite3.Row
        with sqlite3.connect(backup_dir / "database.sqlite") as backup:
            db.backup(backup)
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT count(*) FROM processing_jobs WHERE status IN ('RUNNING', 'PENDING')").fetchone()[0]:
            raise RuntimeError("Indexing jobs must finish before cleanup")
        owner = db.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if not owner:
            raise RuntimeError("Admin demo owner not found")
        owner_id = str(owner[0])
        before = [tuple(row) for row in db.execute("SELECT id, file_md5, active_vector_version FROM file_upload WHERE user_id = ? ORDER BY id", (owner_id,))]
        targets = []
        for item in legacy["documents"]:
            name = item["file"]
            raw = (ROOT / "demo_knowledge" / name).read_bytes()
            digest = hashlib.md5(raw).hexdigest()
            row = db.execute("SELECT * FROM file_upload WHERE user_id = ? AND file_name = ? AND file_md5 = ?", (owner_id, name, digest)).fetchone()
            if row is None:
                continue
            path = (storage / row["storage_key"]).resolve()
            if not path.is_relative_to(storage) or path.read_bytes() != raw:
                raise RuntimeError(f"Stored source does not match shipped legacy file: {name}")
            (backup_dir / name).write_bytes(raw)
            targets.append((row, path))
        removed_ids = {row["id"] for row, _ in targets}
        for row, _ in targets:
            for table in ("document_vectors", "document_parent_chunks", "chunk_info"):
                deleted = db.execute(f"DELETE FROM {table} WHERE user_id = ? AND file_md5 = ?", (owner_id, row["file_md5"])).rowcount
                report["deletedRows"][table] = report["deletedRows"].get(table, 0) + deleted
            db.execute("DELETE FROM processing_jobs WHERE file_id = ?", (row["id"],))
            db.execute("DELETE FROM file_upload WHERE id = ? AND user_id = ?", (row["id"], owner_id))
            report["removed"].append({"file": row["file_name"], "md5": row["file_md5"]})
        after = [tuple(row) for row in db.execute("SELECT id, file_md5, active_vector_version FROM file_upload WHERE user_id = ? ORDER BY id", (owner_id,))]
        assert after == [row for row in before if row[0] not in removed_ids], "Unrelated files changed"
        remaining = list(db.execute("SELECT file_name, file_md5, process_status FROM file_upload WHERE user_id = ?", (owner_id,)))
        expected = {(item["file"], hashlib.md5((ROOT / "vendor_knowledge" / item["file"]).read_bytes()).hexdigest()) for item in official["documents"]}
        assert {(row[0], row[1]) for row in remaining} == expected, "Expected precisely the official corpus"
        assert all(row[2] == "COMPLETED" for row in remaining)
        vectors = list(db.execute("SELECT model_version, vector_json FROM document_vectors WHERE user_id = ?", (owner_id,)))
        assert len(vectors) == 5888
        assert all(row[0] == "text-embedding-v4" and len(json.loads(row[1])) == 256 for row in vectors)
        db.commit()
        for _, path in targets:
            path.unlink()
        report.update({"remainingDocuments": len(remaining), "remainingVectors": len(vectors), "model": "text-embedding-v4", "dimension": 256})
    output = ROOT / "eval/legacy-removal-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
