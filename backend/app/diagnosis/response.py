"""Render bounded incident conclusions from program-validated decisions, not guesses."""


def render(decision, facts, handoff):
    if decision.get("superseded"):
        return "本轮诊断已被更新或执行权已过期，请查看最新诊断状态后继续核查。"
    request = decision.get("requestId")
    event = next(
        (
            f
            for f in facts
            if f.get("tool") == "query_call_log" and f.get("found") and f.get("requestId") == request
        ),
        None,
    )
    lines = ["以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。"]
    recheck = decision.get("recheck") or {}
    if recheck.get("status") == "SUCCEEDED":
        lines.append(
            f"复查请求 {recheck['requestId']} 返回 HTTP {recheck['httpStatus']}，已确认该应用和接口的新请求范围内恢复。"
        )
        lines.append("这不代表所有接口或账户整体均已恢复，也不能证明某个处理动作的因果关系。")
    elif recheck.get("status") == "REJECTED":
        lines.append("复查请求的归属、接口或时间未通过关联检查，不能确认本次故障已经恢复。")
    else:
        if event:
            when = (event.get("evidenceContext") or {}).get("calledAt") or "所记录的事件时间"
            lines.append(
                f"请求 {request} 在 {when} 返回 HTTP {event.get('httpStatus')}；该记录只说明当时的事件。"
            )
        else:
            lines.append("当前没有匹配的已核验请求记录，不能确认本次故障原因。")
        supported = [c for c in decision.get("candidates", []) if c["status"] == "SUPPORTED"]
        if supported:
            lines.append("请求时观测支持的候选原因：" + "、".join(c["title"] for c in supported) + "。")
        elif event:
            lines.append(
                "细分原因尚未确定；仅凭 HTTP 状态码或错误码释义不能判断 Key 失效、频率、并发或配额原因。"
            )
        if recheck.get("status") == "STILL_FAILING":
            lines.append("新请求仍然失败，尚未解决；继续依据新事件核查。")
    for item in decision.get("actions", [])[:4]:
        lines.append("建议：" + item["instruction"] + "。")
    lines.append("下一步：" + str(decision.get("nextAction") or "请提供脱敏请求信息。"))
    if handoff.get("success") and handoff.get("handoffId"):
        lines.append("人工工单已创建：" + str(handoff["handoffId"]))
    elif handoff.get("attempted") or decision.get("handoffRequired"):
        lines.append("人工工单尚未确认创建成功，请稍后查询或重试。")
    return "\n\n".join(lines)
