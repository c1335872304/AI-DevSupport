"""Rehearse upgrades/rollback on a copy and fingerprint preserved knowledge."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    with sqlite3.connect(path) as db:
        files = db.execute("SELECT id,file_md5,active_vector_version FROM file_upload ORDER BY id").fetchall()
        vectors = db.execute(
            "SELECT vector_id,file_md5,user_id,chunk_id,vector_version,text_content,vector_json FROM document_vectors ORDER BY vector_id"
        ).fetchall()
        parents = db.execute(
            "SELECT id,file_md5,user_id,vector_version,text_content FROM document_parent_chunks ORDER BY id"
        ).fetchall()
    return {
        "documents": len(files),
        "vectors": len(vectors),
        "parents": len(parents),
        "knowledgeSha256": hashlib.sha256(
            json.dumps([files, vectors, parents], ensure_ascii=False).encode()
        ).hexdigest(),
    }


def main():
    source = ROOT / "data/paismart.db"
    before = fingerprint(source)
    target = ROOT / f"data/checkpoints/migration-{uuid.uuid4().hex}.sqlite"
    with sqlite3.connect(source) as db:
        with sqlite3.connect(target) as backup:
            db.backup(backup)
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///" + target.as_posix()
    for command in [("upgrade", "head"), ("downgrade", "0006_llm_token_reservations"), ("upgrade", "head")]:
        subprocess.run([sys.executable, "-m", "alembic", *command], env=env, cwd=ROOT, check=True)
        assert fingerprint(target) == before
    report = {
        "passed": True,
        "database": "copy only",
        "copy": str(target.relative_to(ROOT)),
        "before": before,
        "after": fingerprint(target),
        "steps": ["upgrade head", "downgrade 0006", "upgrade head"],
    }
    (ROOT / "data/checkpoints/migration-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
