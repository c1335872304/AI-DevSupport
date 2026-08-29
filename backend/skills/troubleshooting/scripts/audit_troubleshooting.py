import json, sys
p=json.load(sys.stdin); w=[]
steps=int(p.get("step_count") or 0)
if steps>4: w.append("一次给出的排障步骤过多")
if p.get("knowledge_needed") and not p.get("knowledge_verified"): w.append("故障知识尚未验证")
if p.get("unsafe_action"): w.append("包含高风险或不可逆操作")
if int(p.get("failed_rounds") or 0)>=2 and not p.get("handoff_planned"): w.append("重复失败后应考虑人工升级")
if p.get("explicit_handoff") and not p.get("handoff_planned"): w.append("客户已明确要求人工")
print(json.dumps({"pass":not w,"warnings":w}, ensure_ascii=False))
