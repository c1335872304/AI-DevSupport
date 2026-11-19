"""Apply the rehearsed additive SQLite upgrade while preserving knowledge fingerprints."""

import hashlib
import json
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_phase1_migration import fingerprint


def main():
    from sqlalchemy.engine import make_url
    from app.core.config import get_settings

    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "sqlite":
        raise RuntimeError("Use the deployment migration workflow for non-SQLite applications")
    source = Path(url.database).resolve()
    if not source.is_relative_to(ROOT) or not source.is_file():
        raise RuntimeError("Unexpected application DB path")
    rehearsal = json.loads((ROOT / "data/checkpoints/migration-report.json").read_text())
    if not rehearsal["passed"]:
        raise RuntimeError("Migration rehearsal must pass first")
    before = fingerprint(source)
    if before != rehearsal["before"]:
        raise RuntimeError("Application knowledge changed since rehearsal; recheck before migrating")
    config = ROOT / ".env"
    config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    backup = ROOT / f"data/checkpoints/before-application-upgrade-{uuid.uuid4().hex}.sqlite"
    with sqlite3.connect(source) as db:
        with sqlite3.connect(backup) as out:
            db.backup(out)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
    after = fingerprint(source)
    assert before == after, "Knowledge fingerprint changed"
    assert hashlib.sha256(config.read_bytes()).hexdigest() == config_hash, "Configuration changed"
    report = {
        "passed": True,
        "backup": str(backup.relative_to(ROOT)),
        "before": before,
        "after": after,
        "configurationUnchanged": True,
    }
    (ROOT / "data/checkpoints/application-upgrade-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
