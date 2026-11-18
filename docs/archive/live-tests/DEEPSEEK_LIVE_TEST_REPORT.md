# DeepSeek 小样本真实测试记录

执行日期：2026-09-08\
执行范围：`DEEPSEEK_LIVE_TEST_PLAN.md` 的 P0、P1、P2 小样本，以及一次有安全上限的端到端 RAG 测试；未运行批量 `--live` 评测。

## 结果

| 用例 | 操作 | 结果 | 验证证据 |
|---|---|---|---|
| P0 | DeepSeek 真实生成链路 | 通过 | 两次 WebSocket 生成均收到 `COMPLETED`，说明 LLM Base URL、Key、模型与 API 容器之间的实际调用可用。 |
| P1 | `demo_user` 发送一条简短闲聊 | 通过 | 收到 56 字符回答；生成完成。 |
| P2 | `demo_user` 询问退款政策 | 通过 | 收到 56 字符回答，并返回 6 条知识库引用映射。 |
| 余额 | 两次真实调用前后余额核对 | 通过 | LLM 余额从 1,000,000 变为 999,922，共扣除 78 Tokens。 |
| 受控 E2E | 一次退款政策 RAG 端到端调用 | 通过 | 登录、WebSocket 鉴权、生成、6 条引用、Generation 持久化和余额扣费均成功；35 个事件、56 个回答字符、扣除 79 Tokens。 |

## 结论

DeepSeek 生成、WebSocket 流式回包、Qwen/Elasticsearch 检索引用、Generation/会话持久化和普通用户 Token 计费主链路均已通过最小真实调用验证。受控 E2E 设置了 60 秒、80 个事件和 1,500 个回答字符三重上限；本次未触发任何上限。

本轮刻意没有执行批量真实模型评测，以避免不必要的外部 API 消耗。后续如需更全面评测，按 [DeepSeek 真实 LLM 测试方案](DEEPSEEK_LIVE_TEST_PLAN.md) 的 P3、P4 与“可选批量真实模型评测”继续执行，并先确认可接受的预算。

## 安全说明

本记录不包含 DeepSeek API Key、访问令牌、密码、完整模型回答或原始请求载荷。

## 2026-09-09 受控修复复验追加记录

在 R1～R6 修复后，按最多 4 条上限执行了新的真实链路复验；未运行批量评测，也未发送新的 Qwen Embedding 请求。4 条请求均通过 API 直连收到 `completion=finished`，随后修复并验证了前端 `/proxy-ws/chat` 的 Nginx URI 重写，浏览器普通用户页面显示“已连接”。

| 用例 | 结果 | Token 增量 | 备注 |
|---|---|---:|---|
| L1 退款政策 | 完成；2 条引用；无退款条款时安全说明 | 11,949 | 链路通过，成本超目标 |
| L2 401 诊断 | 完成；7 条引用；未编造日志事实 | 21,935 | 多轮 Tool/LLM，成本超目标 |
| L3 历史追问 | 完成；质量门阻断后转人工 | 9,953 | 有 `retrieval_query_optimized`，成本超目标 |
| L4 明确转人工 | 完成；创建工单 | 2,847 | 链路通过 |

余额从 926,367 降至 879,683，合计扣除 **46,684 LLM Tokens**；Embedding 余额保持 1,000,000。结论是“真实链路可用，但成本/质量门未达到扩大测试的标准”，因此停止后续 live 请求，先回到离线优化。

## 2026-09-09 知识证据修复后的真实复验

本次为已授权的单条受控复验，用于验证“知识库正文未进入最终回答节点”的修复是否在真实 DeepSeek 调用中生效。使用普通权限的本地 WebSocket 测试夹具账户及其既有测试额度；认证票据仅在进程内生成和使用，未记录密码、Bearer Token 或 API Key。

### 用例与判定

| 项目 | 记录 |
|---|---|
| 请求 | `退款政策是什么？` |
| 传输 | 已签名测试夹具访问票据 → `WebSocket /chat` |
| Generation / Agent Run | `58513909b9a54d5abeed4fbe6722ab2d` |
| 执行时间 | 2026-09-09 12:53:34–12:53:41（约 7 秒） |
| 完成状态 | `COMPLETED`；流式事件以 `completion` 收束 |
| 回答核验 | **通过**：最终回复明确说明“支付完成后 7 天内可提交退款申请”，并列出来源 #1 `refund-policy.md`、#2 `billing-policy.md`、#3 `release-notes.md` |
| 工单核验 | **通过**：`handoffAttempted=false`、`handoffId=null`，未创建工单 |
| 质量门 | **通过**：3/3，覆盖率 `1.0`，无缺失项、无失败项、无阻断 |
| 本次 LLM 结算 | 13,956 Tokens；余额 100,000 → 86,044 |

### 过程记录

1. 建立 WebSocket，服务端返回连接确认；发送问题后获得同一 `generationId`。
2. 事件顺序为：`start` → 工作流节点/实体提取 → 路由判定 → 检索查询优化 → 专家分派 → Tool 调用 → 证据汇总 → 工单决策 → 质量门 → `chunk` → `completion`。共收到 35 个事件：工作流节点 12、检索优化 2、专家分派 2、Tool 调用 6、证据汇总 2、质量门 3，以及其余各阶段事件各 1 个。
3. 路由选中 `billing` 和 `knowledge`，命中 `billing_semantic_hint`、`knowledge_keyword`；风险等级为 `MEDIUM`，但 `requiresHandoffAfterSummary=false`。
4. 第一批业务工具均成功：`mcp__billing__get_plan`（78ms）以及两次 `search_knowledge`（1,147ms、1,152ms）。
5. 三项质量门全部放行：Billing 的“无人工交接不得写入”、Knowledge 的“可追溯”、客服答复审计均通过；系统未转人工。
6. 账本先预留 2,003 Tokens，完成后按 Provider 用量结算 13,956 Tokens；该预留值只是过程中的临时额度，最终消耗应以结算记录为准。

### 结论与限制

修复已在真实 Provider + WebSocket + 持久化 Agent Run 链路中验证：最终回答现在能消费受权限限制、长度受限、明确标为不可信数据的知识正文，因此能回答本问题的“7 天”规则，且保留人工交接和提示注入防护边界。

单条请求的 13,956 Tokens 仍明显高于简单政策问答的合理预算；因此本次只做一条授权复验，不应据此扩大真实调用。后续优化方向仍是压缩重复检索/规划和缩短最终生成上下文。

## 2026-09-09 用户自身 429 限流诊断修复与真实复验

此前的 `LIVE-04` 虽取得调用日志、错误码、QPS 统计和知识库资料，却被质量门替换为“证据不足”。本轮将该场景改为明确的运行时契约：只要当前用户的受权工具结果确认 429，最终答复必须给出已确认的请求与统计事实，明确“不能仅凭 429 推断月额度已耗尽”，并附真实来源；否则才允许说明无法核验。

### 修复内容

1. 质量门读取 `EvidenceSummary.verifiedFacts`，先判定 429 证据是否充分，再判定答复是否覆盖已确认的 429、请求号、统计数值和“月额度尚未确认”边界；仍拒绝凭据泄露和无工具依据的确认。
2. 如果证据充分而模型草稿漏答，质量门记录 `answer_omits_verified_rate_limit_facts`，并以 `repaired_from_verified_evidence` 标记后续受控渲染。这是“答复覆盖失败”，不是“证据不足”；真正没有工具事实时仍走安全说明。
3. 只读工具的局部失败不再在同一轮已有可用事实时自动建工单。显式转人工、高风险操作或完全没有可用证据的情形仍保持原有转人工策略。
4. 支持演示种子改为为非管理员用户生成隔离的 API 应用、Key 和请求 ID，避免普通用户读取到管理员的演示日志，或没有自己的可验证 429 数据。

### 过程与结果

| 阶段 | 结果 | LLM Tokens | 说明 |
|---|---|---:|---|
| 数据隔离发现 | 安全完成，但未确认个人 429 | 25,615 | 普通用户没有自己的演示调用日志；系统没有编造事实。 |
| 首次确认数据复验 | 回答正确，但错误建工单 | 30,230 | 一个无效的只读 RAG 参数被错误视为“需要人工”；已据此修复。 |
| 最终复验 | **通过** | 25,236 | `COMPLETED`、质量门 3/3 通过、无工单。 |

最终 Generation / Agent Run：`0487496b051d46dda43862425c9962fd`，执行时间 2026-09-09 13:25:54–13:26:03。问题为 `request_id req_demo_429_u11 接口返回 429，是不是月额度用完了？`。最终答复准确给出：该请求在 `/v1/chat` 返回 `HTTP 429 (RATE_LIMIT_EXCEEDED)`；最近 60 分钟 2 次调用中 1 次为 429；不能由此判断月额度已经用尽；建议降低突发并发、采用带抖动的指数退避并检查 QPS。

服务端追踪确认：路由仅选择 `api_diagnostic` 与 `knowledge`，`handoffAttempted=false`、`handoffId=null`；当次运行的 `audit_api_diagnostic`、`audit_knowledge_answer`、`audit_support_answer` 全部通过，覆盖率 1.0，无失败或缺失质量门。最终测试用户 LLM 余额为 798,602；本节三条受控请求累计结算 81,081 Tokens。

离线保护回归新增两项：故意让模型输出“知识库证据不足”时，质量门必须先标记“证据充分、答复遗漏”，再触发 `repaired_from_verified_evidence`，不得把它称作证据不足；以及“一个成功的 429 调用日志 + 一个无效只读检索参数”不得自动创建工单。Docker 全量测试为 **126 passed，1 warning**。该质量门语义调整已部署到 API；为控制成本，没有再发送第四条真实 429 请求。

## 2026-09-09 限流问题完整客户问答流程复验

用户明确要求继续真实限流流程测试后，已将最新修复重新构建并部署到 API 容器；`GET /health` 返回 `200`。本节覆盖同一普通用户在三种限流问法下的完整链路：鉴权、WebSocket `/chat`、路由、只读诊断工具、证据汇总、质量门、回答输出、持久化审计，以及明确要求时的人工工单。

| 场景 | 核验结果 | 人工工单 | 最终结算 Tokens |
|---|---|---|---:|
| 已存在的个人 429 请求 | 正确确认 `req_demo_429_u11` 在 `/v1/chat` 返回 `HTTP 429 (RATE_LIMIT_EXCEEDED)`；给出“60 分钟 2 次、其中 1 次 429”，并明确不能据此断定月额度耗尽 | 未创建 | 15,428 |
| 不存在的请求号 | 明确说明未查询到该请求日志，因而**不能确认该请求本身**是否返回 429；仅陈述接口近期统计所支持的“近期出现过限流” | 未创建 | 15,124 |
| 已存在 429 且明确要求转人工 | 同上完成 429 核验、知识库引用和月额度边界说明，并在答复中呈现已创建的工单号 | 已创建，`CS_c859a4003361425fb9e1` | 20,684 |

三条最终验收请求合计结算 **51,236 Tokens**。这仍高于简单诊断问答的预算预期，后续应继续削减重复规划和工具轮次；本次不以成本问题掩盖功能结论。

### 显式转人工场景的可审计记录

最终 Generation / Agent Run：`65f364e062a447819c5b1ab124d13369`，执行时间 2026-09-09 13:51:10–13:51:22，状态 `COMPLETED`。流式事件依次经历路由、检索优化、专家分派、Tool 调用、证据汇总、人工交接决策、质量门、`quality_gate_repaired`、回答分片及 `completion`。

服务端持久化追踪显示：路由命中 `explicit_handoff_request`、`api_diagnostic_entity`、`knowledge_keyword`，风险等级为 `HIGH`；`query_call_log`、`query_error_code`、`query_recent_call_stats`、知识检索/正文读取和 `create_support_handoff` 均成功。`handoffAttempted=true`、`handoffSuccess=true`，工单号与最终回答中的工单号一致。

API 诊断质量门的结构化检查为 `rateLimitEvidenceSufficient=true`、`rateLimitFactsCovered=false`：含义是工具已经给出充分的受权事实，而模型初稿遗漏了必要事实/额度边界。系统因此记录 `answer_omits_verified_rate_limit_facts` 并执行 `qualityGateAction=repaired_from_verified_evidence`，不是将该情形误称为“证据不足”。修复后的答复保留来源 `#1 rate-limit.md`，并追加“已创建人工工单，工单号：CS_c859a4003361425fb9e1”。

### 回归结果与测试工单说明

Docker 后端全量回归为 **128 passed，1 warning**（第三方 `starlette` 的弃用警告）。本次显式人工交接会在本地演示数据中真实创建测试工单；上列工单及此前同一流程生成的测试工单是验证产物，未被删除，以便继续从管理员界面或审计接口复核。

## 2026-09-09 自然语言“我被限流了，怎么回事”复验

以普通用户身份通过真实 WebSocket `/chat` 发送原话“我被限流了，怎么回事”，Generation / Agent Run 为 `10dfb8f7569f4fcdb280cf7f438f43c8`，10 秒内 `COMPLETED`，消耗 18,537 Tokens。路由选择 `api_diagnostic` 与 `knowledge`；审计显示调用了 `query_call_log`、`query_error_code`、`query_recent_call_stats` 和知识检索，最终答复引用 `#1 rate-limit.md`，且没有创建人工工单。

该次结果**不应作为无上下文首次提问的验收通过**。测试账户仍使用最近的活动会话；当前 `looks_like_follow_up` 将任何不超过 80 字的短句都认定为追问，因而本句继承了上一轮的 `req_demo_429_u11`，并据此正确查询到该请求的 429。它不是模型凭空编造该请求号，但这个“短句即追问”的规则会让用户的新话题错误继承历史实体，必须调整为仅在存在明确指代/衔接词或用户显式继续会话时继承。

本次还观察到一项非致命工具参数问题：一个 API 诊断分支向 `search_knowledge` 传入未在 schema 中定义的 `category`，该调用被拒绝为 `INVALID_ARGUMENT`；其他知识检索成功，故不影响最终引用，但应纳入修复与回归测试。

## 2026-09-09 空白新对话的首次限流提问复验

为模拟“一个用户第一次提问”，先通过 `POST /api/v1/users/conversations` 创建无消息、无实体记忆的活动会话，再以同一普通权限测试账户发送首条消息“我被限流了，怎么回事”。Generation / Agent Run 为 `5a01e91cd27a44c6a82882817a0dbbcd`，状态 `COMPLETED`，消耗 25,710 Tokens；未创建工单。

路由正确选中 `api_diagnostic` 与 `knowledge`，并成功检索 `rate-limit.md`、`troubleshooting-faq.md` 等文档，给出降低并发、带抖动的指数退避、检查 QPS 的通用建议及来源引用。没有任何历史 `request_id` 被继承，证明本次是空白会话。

**本用例判定为失败，不能作为首次客户问答验收通过。** 审计显示仅执行两次 `search_knowledge` 和一次 `query_error_code`，没有 `query_call_log`、没有 `query_recent_call_stats`，也没有用户提供的错误码；但最终答复写成“已核验错误码为 `RATE_LIMIT_EXCEEDED`”“本次或近期调用触发了限流”。`query_error_code` 只能解释标准错误码，不能证明该用户的本次请求带有该错误码。应修复为：把“限流”作为用户描述，先给文档支持的通用原因与排障建议；若要确认个人事件，则提示用户提供 `request_id`、HTTP 状态/错误码、endpoint 和发生时间，或在已知 endpoint 时用受权的近期统计明确其适用范围。

## 2026-09-09 质量门过滤重构与首次限流问答最终复验

按“质量门只删除无依据主张、不得重写诊断结论”的要求完成重构：

1. `query_error_code` 被定义为**错误码释义**，不能再单独证明客户发生限流；只有当前用户调用日志中的 `HTTP 429` 或有明确 endpoint/时间窗口的近期统计才属于个人事件证据。
2. API 诊断 Agent 对 LLM 提出的 `query_call_log`、`query_error_code` 和 `query_recent_call_stats` 增加参数来源校验：参数必须来自用户实体或前一轮成功调用日志。单独出现“限流”不能触发虚构的错误码查询。
3. 质量门把无事件证据的“已核验”“已确认本次/近期调用触发限流”“我查询了错误码”等行标为不受支持并删除；它不再把草稿替换为新的“已核验”模板。若删除后只剩引用，才使用固定的补充信息提示。
4. 最终回答节点明确区分“文档/错误码定义”与“客户事件”，在没有个人事件证据时必须给出文档型建议并请求 `request_id`、状态/错误码、endpoint 或时间。

新增/调整回归覆盖：首次限流提问的无依据主张过滤、诊断工具参数来源、已确认 429 不被质量门改写，以及既有请求号、未知请求号、人工工单流程。Docker 后端全量结果为 **129 passed，1 warning**。

最终真实复验先创建空白活动会话，再以首条消息发送“我被限流了，怎么回事”。Generation / Agent Run：`bfd8b76fec854633baec2f48a9645cb2`；2026-09-09 15:13:20–15:13:28；`COMPLETED`；结算 17,043 Tokens。最终回复：

- 明确说明未查询到实时调用数据，因此不能确认该用户的具体限流原因；
- 用来源 `rate-limit.md`、`troubleshooting-faq.md`、`billing-policy.md` 解释 429、瞬时 QPS 与月度额度是不同维度；
- 给出指数退避、随机抖动、降低并发/批量等通用恢复建议；
- 请求补充 `request_id`、状态/错误码、endpoint 和发生时间；
- 未创建工单，且没有“已核验 429”“已核验 RATE_LIMIT_EXCEEDED”或虚构日志查询结论。

持久化审计显示只执行两次 `search_knowledge`，没有执行 `query_error_code`、`query_call_log` 或 `query_recent_call_stats`。API 质量门的检查为 `rateLimitEvidenceSufficient=false`、`rateLimitIncidentObserved=false`、`rateLimitRecentObservation=false`、`hasDiagnosticAnchor=false`，但所有质量门通过，因为最终答复没有把通用资料升级为个人事实。
