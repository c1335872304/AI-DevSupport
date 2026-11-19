"""Protect knowledge/config and archive source without secrets or dependencies."""

import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from verify_phase1_migration import fingerprint

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINTS = ROOT / "backend/data/checkpoints"


def main(checkpoint_name="phase3-delivery", baseline_name="phase3-start"):
    starting = json.loads((CHECKPOINTS / baseline_name / "manifest.json").read_text())
    baseline = fingerprint(CHECKPOINTS / baseline_name / "database.sqlite")
    current = fingerprint(ROOT / "backend/data/paismart.db")
    assert baseline == current
    config_hash = hashlib.sha256((ROOT / "backend/.env").read_bytes()).hexdigest()
    assert config_hash == starting["configSha256"]
    output = CHECKPOINTS / checkpoint_name
    output.mkdir(exist_ok=True)
    with sqlite3.connect(ROOT / "backend/data/paismart.db") as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0015_diagnosis_loop"
        with sqlite3.connect(output / "database.sqlite") as target:
            db.backup(target)
    # Start from the previous audited source list, then include new source files.
    paths = {ROOT / item["path"] for item in starting["files"]}
    # Include manifests and first-party workspace packages, not only app files.
    for relative in (
        "README.md",
        "LICENSE",
        ".gitignore",
        "compose.yaml",
        "backend/.env.example",
        "backend/.env.full.example",
        "backend/.dockerignore",
        "backend/Dockerfile",
        "backend/alembic.ini",
        "backend/pyproject.toml",
        "backend/requirements.txt",
        "backend/requirements-dev.txt",
        "backend/requirements-docling.txt",
        "backend/requirements-docling.lock",
        "backend/uv.lock",
        "backend/run.py",
        "backend/mcp_server.py",
        "backend/billing_mcp_server.py",
        "frontend/.env.example",
        "frontend/.dockerignore",
        "frontend/Dockerfile",
        "frontend/package.json",
        "frontend/pnpm-lock.yaml",
        "frontend/pnpm-workspace.yaml",
        "frontend/index.html",
        "frontend/nginx.conf",
        "frontend/tsconfig.json",
        "frontend/vite.config.ts",
        "frontend/uno.config.ts",
        "frontend/eslint.config.js",
        "frontend/public/favicon.svg",
    ):
        paths.add(ROOT / relative)
    for folder in (
        "backend/app",
        "backend/alembic",
        "backend/tests",
        "backend/scripts",
        "backend/skills",
        "backend/eval",
        "backend/vendor_knowledge",
        "docs",
        "frontend/src",
        "frontend/build",
        "frontend/packages",
        "deploy",
        ".github",
    ):
        for path in (ROOT / folder).rglob("*"):
            if (
                path.is_file()
                and not any(
                    part in {"__pycache__", "node_modules", ".pytest_cache", "dist"} for part in path.parts
                )
                and path.suffix not in {".pyc", ".pyo"}
            ):
                paths.add(path)
    files = []
    with zipfile.ZipFile(output / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            if not path.is_file() or (path.name.startswith(".env") and not path.name.endswith(".example")):
                continue
            relative = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            archive.writestr(relative, content)
            files.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
    report = {
        "passed": True,
        "knowledge": current,
        "configurationUnchanged": True,
        "protectedConfiguration": "backend/.env",
        "configSha256": config_hash,
        "schema": "0015_diagnosis_loop",
        "files": files,
        "providerCallsDuringCheckpoint": 0,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"files", "configSha256"}}))
    print(f"Archived {len(files)} source files; secrets excluded")


if __name__ == "__main__":
    main()
