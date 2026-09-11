import json
import sys


def main():
    payload = json.load(sys.stdin)
    entities = payload.get("entities") or {}
    question = str(payload.get("question") or "").lower()
    steps = []
    if entities.get("request_id"):
        steps.append({"tool": "query_call_log", "reason": "先确认本次调用的真实状态"})
    if entities.get("error_code") and not entities.get("request_id"):
        steps.append({"tool": "query_error_code", "reason": "解释已知标准错误码"})
    if entities.get("app_id") and (entities.get("http_status") in {"401", "403"} or "api key" in question):
        steps.append({"tool": "query_api_key_status", "reason": "核实密钥状态"})
    if entities.get("endpoint") and (entities.get("http_status") == "429" or "限流" in question or "qps" in question):
        steps.append({"tool": "query_recent_call_stats", "reason": "核实近期限流分布"})
    if not steps:
        steps.append({"tool": "search_knowledge", "reason": "先查找对应 API 文档或故障说明"})
    print(json.dumps({"steps": steps[:4], "stopAfter": 4, "readOnly": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
