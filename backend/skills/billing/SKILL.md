---
name: billing
description: 账单、套餐、用量、支付和退款诉求的专业工作流；只读核实业务事实，高风险资金或合同诉求必须交给人工。
triggers: ["账单", "费用", "扣费", "用量", "调用量", "套餐", "配额", "余额", "发票", "invoice", "billing", "退款", "退费", "退订", "支付争议", "重复扣费", "chargeback"]
negative_triggers: ["已经解决", "只问 API 错误"]
allowed_tools: ["query_plan", "query_usage", "query_bill", "search_knowledge", "get_support_handoff", "create_support_handoff", "read_skill_reference", "run_skill_script"]
references: ["references/billing-readonly-boundary.md", "references/refund-handoff-policy.md"]
scripts: ["classify_billing_request", "build_billing_handoff_summary", "audit_billing_safety"]
evals: ["eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl"]
quality_gate: audit_billing_safety
priority: 85
---
# Billing

## 目标
准确区分公开计费规则和客户账户事实。这个 Skill 可以查询套餐、用量和账单，但不自动退款、不改价、不升降套餐、不取消订阅。

## 工作流
1. 先判断用户是在问公开规则，还是在核实自己的账单、扣费、用量或套餐状态；优先沿用历史实体中的 month、invoice_id、transaction_id。
2. 本地模式下套餐/配额使用 `query_plan`，用量使用 `query_usage`，账单/扣费使用 `query_bill`。启用 Billing MCP 时，只能从本轮 `list_tools` 实际发现并注入的 `mcp__billing__*` 只读 Tool 中选择；根据名称、描述和 JSON Schema 判断用途，不要猜测未发现的 Tool。互不依赖的只读查询可以并行。
3. 退款申请、退费争议、重复扣费、支付争议、退订和套餐变更属于高风险诉求：不承诺退款，不修改业务数据，必须调用 `create_support_handoff` 转人工。
4. 只问退款政策时可以先调用 `search_knowledge`，但不要因为政策问题自动创建工单；如果用户从政策咨询转为实际退款申请，再进入人工流程。
5. 工单只有在 Tool 返回 SUCCESS 且有 handoffId 后才能告诉用户已创建；失败时明确说暂未成功。

需要判断账户事实边界时读取 [references/billing-readonly-boundary.md](references/billing-readonly-boundary.md)；需要处理退款或争议时读取 [references/refund-handoff-policy.md](references/refund-handoff-policy.md)。最终输出前运行 `audit_billing_safety`。

## 输出契约
- 区分“政策说明”“只读查询结果”和“人工处理结果”。
- 没有真实业务 Tool 结果时，不能确认用户的金额、扣费、退款状态或套餐状态。
- 不在回答中泄露支付凭据、完整卡号、Token 或其他账户敏感信息。
- 高风险诉求优先完成转人工，不让无关排查阻塞转接。
