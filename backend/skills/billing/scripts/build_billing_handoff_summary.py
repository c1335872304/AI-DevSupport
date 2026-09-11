import json
import sys


def main():
    payload = json.load(sys.stdin)
    question = str(payload.get("question") or "")[:1200]
    entities = payload.get("entities") or {}
    safe_entities = {key: str(entities[key])[:120] for key in ("invoice_id", "transaction_id", "order_id", "month") if entities.get(key)}
    print(json.dumps({"summary": f"客户提出资金或合同相关诉求：{question}", "knownEntities": safe_entities, "excludedSecrets": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
