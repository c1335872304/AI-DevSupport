---
name: escalation
description: 当客户明确要求人工、投诉/争议升级、重复排障失败或 AI 缺少必要权限时，整理上下文并创建真实人工客服工单。
triggers: ["人工客服", "转人工", "人工处理", "找人工", "投诉", "升级处理", "客服经理", "人工介入", "还是不行", "仍然不行", "已经试过了", "human agent", "representative", "escalate", "complaint", "降套餐", "降级套餐", "改价", "退差价", "退订", "取消套餐", "套餐变更"]
negative_triggers: ["不用人工", "不要转人工", "已经解决"]
allowed_tools: ["create_support_handoff", "get_support_handoff", "search_knowledge", "query_plan", "query_usage", "query_bill", "query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code", "read_skill_reference", "run_skill_script"]
references: ["references/handoff-policy.md", "references/priority-rules.md", "references/handoff-summary-format.md"]
scripts: ["assess_escalation", "build_handoff_summary", "audit_handoff"]
evals: ["eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl"]
quality_gate: audit_handoff
priority: 60
---
# Escalation

## 目标
在 AI 无法可靠继续解决，或客户明确要求人工时，**快速、完整、可追踪地转交真人客服**。升级不是失败，而是客服闭环的一部分。

## 工作流
### Phase 0 — 判断是否应该升级
可运行 `assess_escalation`。以下情况优先升级：
- 客户明确要求人工或投诉；
- 支付/退款争议需要人工核验；
- 账户安全、权限或后台操作超出当前 Tool 能力；
- 同一故障已尝试多轮仍未解决；
- 关键事实无法验证，继续回答会增加误导风险。

### Phase 1 — 整理交接上下文
运行 `build_handoff_summary`，至少包含：
- 客户当前诉求；
- 已确认事实；
- 已尝试步骤及结果；
- 尚未解决的问题；
- 需要人工处理的原因。
不要把密码、验证码、Token、完整支付凭据写入工单。

### Phase 2 — 创建真实工单
调用 `create_support_handoff`。只有 Tool 返回 `SUCCESS` 和 `handoffId` 后，才可以告诉客户“已创建人工工单”。

如果 Tool 失败，必须明确说“暂未成功创建”，不能假装已经转人工。

### Phase 3 — Handoff Quality Gate
运行 `audit_handoff`，确认应该升级时已经创建工单、摘要包含必要字段且没有敏感凭据。

## 输出契约
- 客户明确要求人工时，不继续用多轮排障阻止转接。
- 成功创建后告诉客户 `handoffId` 和当前状态。
- 不承诺人工处理时长、退款结果或赔偿结果，除非系统明确提供。
- 工单失败时给出事实状态，并保留用户问题，不伪造成功。
