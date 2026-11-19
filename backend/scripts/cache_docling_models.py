"""Prefetch pinned public Docling artifacts; no runtime 'main' model downloads."""

import hashlib
import json
import os
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "data/models/docling"
MODELS = [
    (
        "ds4sd/docling-layout-heron",
        "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
        ["config.json", "preprocessor_config.json", "model.safetensors"],
    ),
    (
        "ds4sd/docling-models",
        "fc0f2d45e2218ea24bce5045f58a389aed16dc23",
        [
            "model_artifacts/tableformer/accurate/tm_config.json",
            "model_artifacts/tableformer/accurate/tableformer_accurate.safetensors",
        ],
    ),
]


def main():
    rows = []
    with httpx.Client(
        proxy=os.environ.get("MODEL_DOWNLOAD_PROXY") or None,
        trust_env=False,
        follow_redirects=True,
        timeout=120,
    ) as client:
        for repo, revision, files in MODELS:
            for name in files:
                target = ARTIFACTS / repo.replace("/", "--") / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.is_file():
                    print("Downloading " + repo + "/" + name, flush=True)
                    partial = target.with_suffix(target.suffix + ".part")
                    with client.stream(
                        "GET", f"https://huggingface.co/{repo}/resolve/{revision}/{name}"
                    ) as response:
                        response.raise_for_status()
                        with partial.open("wb") as output:
                            for block in response.iter_bytes(1024 * 1024):
                                output.write(block)
                    partial.replace(target)
                checksum = hashlib.sha256(target.read_bytes()).hexdigest()
                rows.append(
                    {
                        "repo": repo,
                        "revision": revision,
                        "file": name,
                        "sha256": checksum,
                        "bytes": target.stat().st_size,
                    }
                )
    (ARTIFACTS / "manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("Pinned artifacts cached at " + str(ARTIFACTS), flush=True)


if __name__ == "__main__":
    main()
