"""Run real Docling fixture checks without calling an embedding provider."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.knowledge.parser import parser_service


def main():
    directory = ROOT / "tests/fixtures/docling"
    manifest = json.loads((directory / "manifest.json").read_text())
    output = ROOT / "data/checkpoints/docling"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for case in manifest["cases"]:
        start = time.monotonic()
        row = {"file": case["file"], "passed": False}
        try:
            blocks, artifacts = parser_service.parse_with_artifacts(
                case["file"], (directory / case["file"]).read_bytes()
            )
            text = "\n".join(b.text for b in blocks)
            assert not case.get("error"), "Expected explicit unsupported/error outcome"
            assert all(word in text for word in case["expected"]), "Expected field missing"
            if case.get("page"):
                assert any(b.page_number == case["page"] for b in blocks), "PDF page missing"
            if case.get("table"):
                assert any(b.location["type"] == "table" for b in blocks), "Table structure missing"
            parents, children = parser_service.hierarchical_chunk(blocks)
            assert parents and children and all(c.location for c in children)
            row.update(
                {
                    "passed": True,
                    "blocks": len(blocks),
                    "parents": len(parents),
                    "children": len(children),
                    "submittableUtf8Bytes": sum(len(c.text.encode()) for c in children),
                    "metrics": artifacts.get("metrics", {}),
                }
            )
            (output / (case["file"] + ".json")).write_text(
                json.dumps(artifacts, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            row.update(
                {"error": str(exc)[-1800:], "passed": bool(case.get("error") and case["error"] in str(exc))}
            )
        row["seconds"] = round(time.monotonic() - start, 3)
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        (output / "report.json").write_text(
            json.dumps({"embeddingCalls": 0, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
