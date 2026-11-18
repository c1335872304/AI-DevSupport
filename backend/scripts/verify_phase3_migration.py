"""Phase-3 upgrade/rollback rehearsal; --apply backs up before local SQLite upgrade."""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from verify_phase1_migration import fingerprint
from verify_phase2_migration import backup, migrate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = ROOT / "data/paismart.db"
    before = fingerprint(source)
    configuration = hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest()
    checkpoint = ROOT / "data/checkpoints"
    copy = checkpoint / f"phase3-migration-{uuid.uuid4().hex}.sqlite"
    backup(source, copy)
    migrate(copy, ("upgrade", "head"), ("downgrade", "0014_diagnosis_sessions"), ("upgrade", "head"))
    assert fingerprint(copy) == before
    report = {"passed": True, "applied": args.apply, "copy": str(copy.relative_to(ROOT)), "before": before}
    if args.apply:
        saved = checkpoint / f"before-phase3-application-{uuid.uuid4().hex}.sqlite"
        backup(source, saved)
        migrate(source, ("upgrade", "head"))
        report["backup"] = str(saved.relative_to(ROOT))
    assert fingerprint(source) == before
    assert hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest() == configuration
    report.update(after=fingerprint(source), configurationUnchanged=True)
    report_name = "phase3-migration-report.json" if args.apply else "phase3-migration-rehearsal-report.json"
    (checkpoint / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
