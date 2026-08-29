import json, sys
p=json.load(sys.stdin)
text=str(p.get("text") or p.get("question") or "").lower()
explicit=bool(p.get("explicit_handoff")) or any(w in text for w in ["人工客服","转人工","找人工","投诉","human agent","representative","escalate"])
failed=int(p.get("failed_rounds") or 0)
payment=bool(p.get("payment_dispute")) or any(w in text for w in ["重复扣费","未授权扣费","退款争议","支付争议"])
security=bool(p.get("security_risk"))
capability=bool(p.get("missing_capability"))
should=explicit or failed>=2 or payment or security or capability
priority="URGENT" if security else ("HIGH" if payment or failed>=2 or "投诉" in text else "NORMAL")
reasons=[]
if explicit: reasons.append("customer_requested_human")
if failed>=2: reasons.append("repeated_troubleshooting_failed")
if payment: reasons.append("payment_or_refund_dispute")
if security: reasons.append("security_risk")
if capability: reasons.append("missing_required_capability")
print(json.dumps({"shouldEscalate":should,"priority":priority,"reasons":reasons}, ensure_ascii=False))
