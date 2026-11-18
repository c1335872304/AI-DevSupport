"""Rehearse phase-2 schema upgrade/rollback on a copy; optionally apply after backup."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from verify_phase1_migration import fingerprint

ROOT = Path(__file__).resolve().parents[1]


def migrate(path, *steps):
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///" + path.as_posix()
    for step in steps:
        subprocess.run([sys.executable, "-m", "alembic", *step], cwd=ROOT, env=env, check=True)


def backup(source, target):
    with sqlite3.connect(source) as db, sqlite3.connect(target) as copy:
        db.backup(copy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Back up and migrate the local application SQLite after rehearsal",
    )
    args = parser.parse_args()
    source = ROOT / "data/paismart.db"
    before = fingerprint(source)
    config = hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest()
    checkpoint = ROOT / "data/checkpoints"
    copy = checkpoint / f"phase2-migration-{uuid.uuid4().hex}.sqlite"
    backup(source, copy)
    migrate(copy, ("upgrade", "head"), ("downgrade", "0013_source_document_revisions"), ("upgrade", "head"))
    assert fingerprint(copy) == before
    report = {
        "passed": True,
        "copy": str(copy.relative_to(ROOT)),
        "applied": args.apply,
        "before": before,
        "rehearsalAfter": fingerprint(copy),
    }
    if args.apply:
        saved = checkpoint / f"before-phase2-application-{uuid.uuid4().hex}.sqlite"
        backup(source, saved)
        migrate(source, ("upgrade", "head"))
        assert fingerprint(source) == before
        report["backup"] = str(saved.relative_to(ROOT))
    assert hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest() == config
    report.update({"configurationUnchanged": True, "after": fingerprint(source)})
    (checkpoint / "phase2-migration-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
