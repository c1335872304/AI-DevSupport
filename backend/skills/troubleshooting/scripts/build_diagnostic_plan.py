import json, sys
p=json.load(sys.stdin)
symptom=str(p.get("symptom") or "").strip()
known=list(p.get("known_steps") or [])
max_steps=max(1,min(4,int(p.get("max_steps") or 3)))
base=[]
if symptom: base.append({"step":1,"action":"核对并保留当前错误提示/错误码","purpose":"确保后续检索和升级上下文准确"})
base += [
 {"step":len(base)+1,"action":"执行知识库中与该错误直接匹配的最低风险修复动作","purpose":"优先验证已知解决方案"},
 {"step":len(base)+2,"action":"若仍失败，记录执行结果并停止重复同一步骤","purpose":"避免无效循环，准备下一步或人工升级"},
]
print(json.dumps({"symptom":symptom,"knownSteps":known,"steps":base[:max_steps]}, ensure_ascii=False))
