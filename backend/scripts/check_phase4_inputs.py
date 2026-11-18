"""Fail on accidental evaluation-label drift. No network, model or DB access."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "eval/phase4/manifest.json").read_text(encoding="utf-8"))
    for item in manifest["inputs"]:
        content = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["sha256"], item["path"]
    episodes = [
        json.loads(line)
        for line in (ROOT / "eval/phase4/diagnosis.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    ids = [row["id"] for row in episodes]
    assert len(ids) == len(set(ids)) == 24
    assert {row["split"] for row in episodes} == {"development", "holdout"}
    assert all(
        row["expected"]["status"]
        in {"WAITING_USER_ACTION", "WAITING_RECHECK", "COLLECTING", "RESOLVED", "HANDED_OFF"}
        for row in episodes
    )
    print(f"Frozen evaluation inputs verified: {len(manifest['inputs'])} datasets, 24 episodes")


if __name__ == "__main__":
    main()
