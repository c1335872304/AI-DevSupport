import json, sys
p=json.load(sys.stdin)
def clean(v): return str(v or "").strip()[:1200]
out={
 "customerGoal":clean(p.get("customer_goal")),
 "confirmedFacts":clean(p.get("confirmed_facts")),
 "attemptedSteps":clean(p.get("attempted_steps")),
 "unresolvedIssue":clean(p.get("unresolved_issue")),
 "escalationReason":clean(p.get("escalation_reason")),
}
summary="；".join(f"{k}: {v}" for k,v in out.items() if v)
print(json.dumps({"summary":summary[:4000],"fields":out}, ensure_ascii=False))
