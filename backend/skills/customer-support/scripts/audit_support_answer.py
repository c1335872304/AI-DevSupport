import json, sys
p=json.load(sys.stdin)
w=[]
if not p.get("issue_understood", True): w.append("客户核心诉求尚未明确")
if p.get("knowledge_needed") and not p.get("knowledge_verified"): w.append("需要知识依据但尚未验证")
if p.get("account_specific") and not p.get("account_verified") and p.get("claims_account_status"): w.append("存在未验证的账户特定事实")
if not p.get("next_step_present", True): w.append("缺少清晰下一步")
if p.get("handoff_needed") and not p.get("handoff_created"): w.append("应升级人工但尚未创建工单")
print(json.dumps({"pass": not w, "warnings": w}, ensure_ascii=False))
