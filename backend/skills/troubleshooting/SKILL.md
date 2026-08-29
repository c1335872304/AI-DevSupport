---
name: troubleshooting
description: 处理登录、上传、支付、连接、页面或功能异常等客服故障；基于症状和知识库形成最小诊断路径，并在重复失败时升级人工。
triggers: ["报错", "错误", "失败", "打不开", "不能用", "无法登录", "登录不上", "上传失败", "支付失败", "连接失败", "收不到验证码", "卡住", "异常", "故障", "401", "429", "request_id", "request id", "api key", "接口", "限流", "qps", "error", "failed", "not working", "cannot", "can't"]
negative_triggers: ["没有报错", "已经解决", "不用排查"]
allowed_tools: ["search_knowledge", "query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code", "read_skill_reference", "run_skill_script", "get_support_handoff"]
references: ["references/troubleshooting-playbook.md", "references/diagnostic-question-policy.md", "references/safe-actions.md", "references/api-diagnostic-playbook.md"]
scripts: ["classify_failure", "build_diagnostic_plan", "audit_troubleshooting"]
evals: ["eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl"]
quality_gate: audit_troubleshooting
priority: 40
---
# Troubleshooting

## 目标
把“不能用/报错”转化为可执行的最短排障路径。不要一次甩给客户十几个步骤，也不要在没有证据时随意猜根因。

## 工作流
### Phase 0 — 症状结构化
1. 提取：客户想完成的动作、实际现象、错误信息、已尝试步骤。
2. 可运行 `classify_failure` 将问题归为 auth/network/upload/payment/client/server/unknown。
3. 只询问影响下一步诊断的最少信息；已经在对话里出现的信息不要重复问。

### Phase 1 — 收集真实诊断证据
1. 用户提供 `request_id` 时先调用 `query_call_log`，以真实状态码、错误码、endpoint、appId 为主证据。后续依赖日志产出的 appId/errorCode 时，应放到下一轮。
2. 已知 `app_id` 且出现 401/API Key 问题时，用 `query_api_key_status` 检查有效/过期/禁用状态；只返回脱敏 Key。
3. 429/限流/QPS 问题使用 `query_recent_call_stats` 查看近时段状态码分布。
4. 已知标准错误码时优先 `query_error_code` 获取确定性原因和修复步骤，同时可用 `search_knowledge` 补充产品文档；此时尽量使用 `filters.category=["error_code","troubleshooting"]`、`filters.product`、`filters.channel=api` 等 Metadata Filter 缩小检索范围。
5. `query_api_key_status`、`query_recent_call_stats`、`query_error_code` 在参数都已知且互不依赖时，应同轮并行。
6. 普通页面/上传/客户端故障继续用 `search_knowledge` 查询错误码、症状和产品功能；知识库没有匹配项时明确说明，不发明根因。

### Phase 2 — 最小诊断路径
1. 复杂问题运行 `build_diagnostic_plan`，将排障控制在 1–4 个有顺序的动作。
2. 优先低风险、可逆、信息增益高的检查。
3. 不要求客户删除数据、关闭安全软件、修改系统关键配置等高风险操作，除非知识库明确给出并且风险已说明。
4. 需要追问时参考 `references/diagnostic-question-policy.md`。

### Phase 3 — 判断停止排障
满足任一条件时应考虑 `escalation`：
- 客户明确要求人工；
- 同一问题已经尝试多轮仍失败；
- 涉及支付争议、账户安全或需要后台人工权限；
- 缺少必要系统能力，无法验证下一步。

### Phase 4 — Troubleshooting Quality Gate
最终给出排障方案前运行 `audit_troubleshooting`。如果步骤过多、缺乏依据、存在高风险动作或已经达到升级阈值，应修正方案或转人工。

## 输出契约
- 先说明最可能的下一步，而不是列出百科全书式原因。
- 每个步骤清楚说明“做什么”；必要时说明“看到什么结果后进入下一步”。
- 不把猜测写成根因确认。
- 重复失败后不要无限循环排查。


> Metadata Filter 是检索约束，不是权限替代。ACL 仍由 Tool/Retrieval 层强制执行。
