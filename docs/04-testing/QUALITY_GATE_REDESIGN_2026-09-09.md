# 质量门重构与限流首次问答验收记录

日期：2026-09-09  
状态：已部署、已完成真实复验  
范围：客户首次询问“我被限流了，怎么回事”及相关 API 诊断质量门。

## 结论

质量门已从“根据工具结果重写诊断结论”改为“删除没有证据支撑的个人事实”。首次限流提问现在只返回有文档依据的通用说明、恢复建议和补充信息引导；没有调用日志或统计时，不再声称已核验用户发生 `HTTP 429` 或 `RATE_LIMIT_EXCEEDED`。

Docker 后端全量回归：**129 passed，1 warning**。最终真实 WebSocket 复验状态：`COMPLETED`。

## 原问题

用户只输入：

```text
我被限流了，怎么回事
```

旧流程曾产生以下不合理结论：

```text
已核验错误码为 RATE_LIMIT_EXCEEDED，表示请求触发了限流。
这能确认本次或近期调用触发了限流。
```

该用户没有提供 `request_id`、HTTP 状态、错误码、接口地址或发生时间；系统也没有取得该用户的调用日志或接口统计。因此上述内容把“错误码定义/文档知识”误写成“用户个人事件事实”。

## 证据分级

| 证据来源 | 可以说明什么 | 不可以说明什么 |
|---|---|---|
| `query_call_log` 返回该请求 `HTTP 429` | 该用户、该请求发生限流 | 月额度已经耗尽 |
| `query_recent_call_stats` 返回指定接口的限流次数 | 该用户该接口在对应时间窗口内出现过限流 | 某个未找到的请求发生限流 |
| `query_error_code` | 标准错误码的通用含义 | 用户本次请求返回该错误码 |
| 知识库文档 | 通用原因、恢复建议、产品规则 | 用户实时调用状态、账单或额度状态 |
| 用户自述 | 需要排查的现象 | 已经核验的系统事实 |

## 重构原则

1. 回答节点负责组织语言，但只能使用结构化证据中的事实。
2. 质量门只做验证、删除和阻断；不得将草稿改写为新的个人诊断结论。
3. 文档知识与错误码定义必须保留为“通用解释”类别，不能提升为客户事件证据。
4. 工具参数不仅要通过 JSON Schema，还必须具有来源：来自用户输入、被允许的历史追问实体，或前一轮成功调用日志。
5. 当没有个人事件证据时，答复必须说明边界，并请求最少诊断字段。

## 实现改动

### 1. API 诊断质量门

文件：[audit_api_diagnostic.py](../../backend/skills/api-diagnostic/scripts/audit_api_diagnostic.py)

- 将“调用日志 429 / 近期统计”与“错误码释义”分离。
- 仅前两类可构成 `rateLimitEvidenceSufficient`。
- 新增 `unsupported_personal_rate_limit_claim`：无事件证据时，禁止“已核验”“已确认本次请求/近期调用触发限流”等个人结论。
- 新增 `unsupported_unanchored_diagnostic_query_claim`：无诊断锚点时，禁止“我查询了错误码”“当前已确认的信息”等无价值诊断叙述。
- “事实覆盖不足”保留为可观测告警，不再触发质量门凭空补写事实。

### 2. 质量门过滤器

文件：[workflow.py](../../backend/app/agent/graph/workflow.py)

- 删除旧的 `_confirmed_rate_limit_answer` 重写路径。
- 新增 `_remove_unsupported_rate_limit_claims`，仅删除无依据的行，保留文档建议和来源引用。
- 增加 `quality_gate_filtered` 事件和 `qualityGatesFiltered` 审计字段。
- 只有过滤后正文为空时，才返回固定的“请提供 request_id、HTTP 状态/错误码、接口地址或发生时间”提示。
- 回答节点提示词明确：错误码定义和文档不能证明客户本次事件。

### 3. 工具参数来源校验

文件：[target_agents.py](../../backend/app/agent/target_agents.py)

- 对 API Agent 的 `query_call_log`、`query_error_code`、`query_recent_call_stats` 增加锚点校验。
- 请求号、错误码、endpoint 必须与用户实体或成功调用日志中的对应字段一致。
- 单独出现“限流”时，LLM 提议的错误码查询会被拒绝，不会执行。

## 首次提问的目标答复契约

当用户只问“我被限流了，怎么回事”时：

- 可以解释：429 的通用含义、QPS/并发与月度额度的区别、指数退避和降低并发的建议。
- 必须说明：当前没有足够的个人调用数据，不能确认该用户的具体原因。
- 应请求：`request_id`、HTTP 状态/错误码、endpoint、发生时间。
- 禁止声称：已核验 429、已核验 `RATE_LIMIT_EXCEEDED`、该请求被限流、月额度已耗尽。

## 验证

### 自动化回归

| 范围 | 结果 |
|---|---|
| 定向 Agent/质量门回归 | 20 passed，1 warning |
| Docker 后端全量 pytest | **129 passed，1 warning** |

新增或调整的断言包括：

- 无诊断锚点时，错误码查询不被 Agent 执行；
- 有真实调用日志时，后续错误码/统计查询仍可使用日志返回的字段；
- 质量门删除无依据限流结论，但保留文档建议和引用；
- 已确认 429 的合格回答不会被质量门改写；
- 旧的 `quality_gate_repaired` 限流模板路径不再用于生成个人诊断。

### 真实空白会话复验

| 项目 | 结果 |
|---|---|
| 先决条件 | 通过 `POST /api/v1/users/conversations` 创建空白活动会话，无历史消息和实体记忆 |
| 用户首条消息 | `我被限流了，怎么回事` |
| Generation / Agent Run | `bfd8b76fec854633baec2f48a9645cb2` |
| 状态 | `COMPLETED` |
| 工具 | 两次 `search_knowledge`；未调用调用日志、错误码、近期统计工具 |
| 最终答复 | 文档型限流解释、QPS/额度边界、恢复建议、补充字段引导和来源引用 |
| 不应出现的结论 | 未出现“已核验 429”“已核验 RATE_LIMIT_EXCEEDED”“已查询到个人日志” |
| 工单 | 未创建 |
| LLM 结算 | 17,043 Tokens |

审计中的 API 质量门检查为：

```text
rateLimitEvidenceSufficient = false
rateLimitIncidentObserved  = false
rateLimitRecentObservation = false
hasDiagnosticAnchor        = false
qualityGateAction          = passed
```

该组合是预期结果：没有个人事件证据，但答复没有越界主张，因此可安全发送。

### 补充自然问法复验：`限流了怎么办`

再次创建空白活动会话后，以首条消息发送“限流了怎么办”。Generation / Agent Run：`53b05edd82434f7c90cf0bca15c34fcb`；2026-09-09 15:27:14–15:27:25；`COMPLETED`；结算 17,169 Tokens。

结果与首次问法一致：路由选择 `api_diagnostic` 与 `knowledge`，但由于没有 `request_id`、错误码或 endpoint，运行时只执行两次 `search_knowledge`，没有执行调用日志、错误码或近期统计查询。最终答复正确说明无法核实账户具体情况，解释 429、QPS 与月度额度的差异，给出指数退避、随机抖动、降低并发/批量等建议，并请求补充诊断字段；引用 `rate-limit.md`、`billing-policy.md` 和 `troubleshooting-faq.md`。未创建工单，也没有声称已经核验用户 429、错误码、实时套餐或额度。

三个质量门均通过；API Gate 的 `rateLimitEvidenceSufficient=false`、`rateLimitIncidentObserved=false`、`rateLimitRecentObservation=false`、`hasDiagnosticAnchor=false`。这证明“没有个人证据”不再被误处理为“必须编造诊断”或“必须阻断文档型答复”。

## 补充真实问答回归：已知请求、未知请求与人工交接

每条用例均先创建空白活动会话，使用普通权限测试账户通过 WebSocket `/chat` 执行。

| 用例 | Generation | 结果 | LLM Tokens |
|---|---|---|---:|
| `request_id req_demo_429_u11 返回 429，是不是月度额度用完了？` | `681c75a8069d43f6a64fea86cdae62ed` | 正确核验 `/v1/chat` 的 429、`RATE_LIMIT_EXCEEDED` 和最近 60 分钟“2 次调用、1 次 429”；明确不能直接断定月度额度耗尽；无工单。 | 18,272 |
| `request_id req_missing_429_u11 返回 429，是不是月度额度用完了？` | `ca87bde78cb24331a22fc23a71587bf4` | 正确说明调用日志未找到该请求，不能确认该 429 的具体原因或月度额度；保留通用建议与补充字段引导；无工单。 | 40,728 |
| `request_id req_demo_429_u11 返回 429，我需要人工客服立即处理。` | `1677379fa1e446f4833740027d9d1b7e` | 核验调用日志后成功创建工单 `CS_412a76a5e05442f2bb58`，最终答复展示同一编号。 | 8,376 |

三条状态均为 `COMPLETED`，累计结算 **67,376 Tokens**。未知请求号用例成本显著偏高，仍需减少重复规划和知识检索。

### 本轮发现的后续优化项

1. 已知 429 问题明确询问“月度额度是否用完”时，路由只选择 `api_diagnostic` 与 `knowledge`，未启动 `billing`，因而没有调用套餐/用量 Tool。当前答复保持了“无法断定”的安全边界，但不够完整；应将“月度额度/配额/用量”与 API 诊断并列路由到 Billing，并在权限允许时读取实时套餐和用量。
2. 已知 429 与显式人工交接用例的 API Gate 记录 `answer_omits_verified_rate_limit_facts`、`missing_quota_boundary`，但以非阻断告警通过。答复已表达“不能直接断定月度额度耗尽”，说明当前匹配规则过于依赖固定措辞；应改为语义化、结构化的主张覆盖检查，或在最终答复节点要求稳定的额度边界字段。
3. 明确转人工用例的工单写入和答复一致性已通过；质量门没有添加或伪造工单信息。

## 仍需持续优化

1. 首次问答仍消耗 17,043 Tokens，应减少重复检索和规划轮次。
2. 会话实体继承仍需继续收紧：只有明确指代或用户显式继续上一话题时才能继承历史实体。
3. 对更多账户事实（账单、套餐、退款、权限状态）复用同一套“主张—证据类型—范围”校验模型。
4. 将无锚点工具调用拒绝率、质量门过滤率、错误事实拦截率和真实调用成本纳入长期监控。

## 安全说明

本文不包含 API Key、访问令牌、密码或完整原始请求载荷。测试使用本地项目环境中的普通权限测试账户和已分配的测试额度。
