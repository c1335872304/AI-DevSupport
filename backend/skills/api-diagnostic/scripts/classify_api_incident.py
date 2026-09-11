import json
import re
import sys


def main():
    payload = json.load(sys.stdin)
    question = str(payload.get("question") or "")
    lower = question.lower()
    category = "unknown"
    if any(token in lower for token in ("401", "403", "api key", "密钥", "认证", "鉴权")):
        category = "authentication"
    elif any(token in lower for token in ("429", "限流", "qps", "rate_limit")):
        category = "rate_limit"
    elif any(token in lower for token in ("上传", "413", "文件")):
        category = "upload"
    elif any(token in lower for token in ("连接", "超时", "网络", "timeout")):
        category = "network"
    elif any(token in lower for token in ("api", "接口", "请求", "报错", "error")):
        category = "api"
    print(json.dumps({
        "category": category,
        "hasRequestId": bool(re.search(r"\breq[_-][A-Za-z0-9_-]+\b", question, re.I)),
        "hasEndpoint": bool(re.search(r"/v\d+/[A-Za-z0-9_./-]+", question)),
        "requiresReadOnlyEvidence": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
