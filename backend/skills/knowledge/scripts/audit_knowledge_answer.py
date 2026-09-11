import json
import sys


def main():
    payload = json.load(sys.stdin)
    answer = str(payload.get("answer") or "")
    results = payload.get("results") or []
    requires_evidence = bool(payload.get("requiresEvidence", True))
    warnings = []
    if requires_evidence and results and "来源#" not in answer and "来源" not in answer:
        warnings.append("missing_citation")
    if not results and any(word in answer for word in ("根据知识库", "文档明确", "政策规定")):
        warnings.append("unsupported_knowledge_claim")
    print(json.dumps({"passed": not warnings, "warnings": warnings, "checks": {"traceable": not warnings}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
