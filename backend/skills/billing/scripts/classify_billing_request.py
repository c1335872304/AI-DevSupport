import json
import sys


def main():
    payload = json.load(sys.stdin)
    question = str(payload.get("question") or "")
    lower = question.lower()
    policy_only = any(word in lower for word in ("政策", "规则", "条件", "标准", "能不能退", "是否可以退"))
    high_risk = any(word in lower for word in ("退款", "退费", "退订", "改价", "降套餐", "升套餐", "重复扣费", "支付争议", "chargeback")) and not policy_only
    if high_risk:
        category = "refund_or_dispute"
    elif any(word in lower for word in ("账单", "费用", "扣费", "发票", "invoice")):
        category = "bill"
    elif any(word in lower for word in ("用量", "调用量", "超额")):
        category = "usage"
    elif any(word in lower for word in ("套餐", "配额", "qps", "余额")):
        category = "plan"
    else:
        category = "policy" if policy_only else "unknown"
    print(json.dumps({"category": category, "policyOnly": policy_only, "highRisk": high_risk, "readOnly": not high_risk}, ensure_ascii=False))


if __name__ == "__main__":
    main()
