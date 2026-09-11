import json
import re
import sys


def main():
    payload = json.load(sys.stdin)
    question = re.sub(r"\s+", " ", str(payload.get("question") or "").strip())
    entities = payload.get("entities") or {}
    suffix = " ".join(str(entities[key]) for key in ("error_code", "endpoint", "app_id", "month") if entities.get(key))
    query = (question + (" " + suffix if suffix else ""))[:1000]
    print(json.dumps({"query": query, "filters": {}, "topK": int(payload.get("topK") or 6)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
