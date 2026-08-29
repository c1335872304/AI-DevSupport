import json, sys, re
p=json.load(sys.stdin); w=[]
if p.get("should_escalate") and not p.get("handoff_created"): w.append("应升级但工单尚未成功创建")
summary=str(p.get("summary") or "")
if p.get("should_escalate") and len(summary.strip())<20: w.append("工单摘要过短")
if re.search(r"(?:password|密码|验证码|api[_ -]?key|token)\s*[:=]\s*\S+", summary, re.I): w.append("摘要疑似包含敏感凭据")
print(json.dumps({"pass":not w,"warnings":w}, ensure_ascii=False))
