---
name: api-diagnostic
description: API 与接口故障诊断专业工作流；适用于 request_id、HTTP 错误码、API Key、限流、上传和接口调用异常，不处理退款或合同变更。
triggers: ["api", "request_id", "request id", "API Key", "api key", "接口", "接口报错", "接口失败", "HTTP 401", "HTTP 403", "HTTP 429", "401", "403", "429", "限流", "QPS", "请求失败", "上传失败"]
negative_triggers: ["已经解决", "不用排查", "只问退款政策"]
allowed_tools: ["query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code", "search_knowledge", "get_support_handoff", "read_skill_reference", "run_skill_script"]
references: ["references/api-evidence-order.md", "references/api-error-safety.md"]
scripts: ["classify_api_incident", "build_api_diagnostic_plan", "audit_api_diagnostic"]
evals: ["eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl"]
quality_gate: audit_api_diagnostic
priority: 80
---
# API Diagnostic

## 目标
把 API 故障转化为有证据、可复现、可停止的最短诊断路径。这个 Skill 只负责诊断和解释，不修改 API Key、套餐、账单或客户数据。

## 工作流
1. 先确认用户要诊断什么，并沿用历史中已经抽取的 request_id、error_code、endpoint、app_id 等实体；已有信息不要重复追问。
2. 有 `request_id` 时，第一步必须调用 `query_call_log`。日志返回的 app_id、error_code、endpoint 和 HTTP 状态是后续查询的输入，必须等待下一轮再使用。
3. 已知错误码但没有 request_id 时，先调用 `query_error_code`；401/API Key 且有 app_id 时调用 `query_api_key_status`；429/限流且有 endpoint 时调用 `query_recent_call_stats`。
4. 互不依赖的只读查询可以并行；有数据依赖的查询必须分轮执行。查询失败时说明失败，不把猜测写成根因。
5. 需要产品规则、错误码含义或配置说明时再调用 `search_knowledge`，并使用真实来源引用。
6. 连续排查没有进展、涉及账户安全，或用户明确要求人工时，停止重复排查并交给 `escalation` 流程。

需要详细判断顺序时读取 [references/api-evidence-order.md](references/api-evidence-order.md)；需要确认安全边界时读取 [references/api-error-safety.md](references/api-error-safety.md)。最终输出前运行 `audit_api_diagnostic`。

## 输出契约
- 先给当前已确认的事实，再给下一步，不编造请求结果。
- 明确区分“日志确认”“知识库说明”和“尚未确认的推测”。
- API Key、Token、Authorization 和完整请求头只能脱敏展示。
- 只声称真实只读 Tool 返回 SUCCESS 后确认过的状态。
- 给出最多 1–4 个最小诊断步骤；达到停止条件时转人工。
