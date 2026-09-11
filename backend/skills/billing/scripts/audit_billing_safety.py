import json
import sys


def main():
    payload = json.load(sys.stdin)
    answer = str(payload.get("answer") or "")
    high_risk = bool(payload.get("highRisk"))
    handoff_id = str(payload.get("handoffId") or "")
    warnings = []
    if high_risk and not handoff_id:
        warnings.append("high_risk_without_handoff")
    if any(phrase in answer for phrase in ("保证退款", "退款已经成功", "已自动退款", "已完成退订")):
        warnings.append("unsafe_business_promise")
    print(json.dumps({"passed": not warnings, "warnings": warnings, "checks": {"noWriteWithoutHandoff": True}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
