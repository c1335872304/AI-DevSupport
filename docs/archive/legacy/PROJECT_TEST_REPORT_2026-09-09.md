# PaiSmart 项目复验报告（2026-09-09）

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../reports/RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](../README.md#legacy)。


## 1. 执行结论

本轮完成了后端、前端、Docker Compose、Billing MCP、WebSocket 客服主链路、工单闭环、离线评测和本地 RAG 检查。

核心代码与 Docker 离线质量门禁通过。2026-09-09 已修复“知识库正文未传给最终答复节点”的缺口，并在随后获授权的一条真实 DeepSeek WebSocket 请求中复验通过：退款政策回答包含“7 天”规则、来源编号，未创建工单，三项质量门均放行。

## 2. 测试结果

| 项目 | 结果 |
|---|---|
| Docker 内后端全量 pytest | **126 passed，1 warning** |
| Skill 合约与路由 | 17/17 通过 |
| Answer Eval | 15/15 通过 |
| 客服基础 Benchmark | 24/24 通过 |
| 客服扩展 Benchmark | 120/120 通过 |
| Python compileall | 通过 |
| 本地 RAG | 14/14；Hit Rate=1.0，Recall=1.0，MRR=0.964，nDCG=0.974 |
| 前端 typecheck | 通过 |
| 前端 build | 通过 |
| Compose YAML 解析 | 通过 |
| Docker Compose 实际启动 | 通过；API、前端、MySQL、Redis、Kafka、Elasticsearch、MinIO、Worker、Billing MCP 均已运行 |
| Docker Billing MCP / WebSocket E2E | 通过；包含业务 Tool、证据汇总、人工交接和失败降级 |
| 远端 Qwen Embedding | 当前未扩大重测；历史受控链路可用，但仍依赖 DashScope DNS/代理 |
| DeepSeek Live 客服问答 | 修复后退款政策与用户自身 429 诊断均完成真实复验；429 最终复验无工单、质量门 3/3 通过，但单条成本仍偏高 |
| 前端 ESLint | 未完成：`prettier-plugin-json-sort` 依赖解析失败 |

## 3. 已修复的问题

### 3.1 WebSocket E2E 数据库初始化

原测试在 TestClient 生命周期启动前创建用户，干净 SQLite 数据库中会出现：

```text
sqlite3.OperationalError: no such table: users
```

已在测试中显式初始化数据库，使测试不再依赖外部启动顺序。

### 3.2 Python 3.11 兼容性

`app/evaluation/answer.py` 原先在 f-string 表达式中使用带反斜杠的换行连接，Python 3.11 不支持该语法。已改为先计算 `evidence_text`，再插入 f-string。

### 3.3 知识证据传递与退款政策回答

真实链路曾出现“`退款政策是什么？` 已检索到引用，却返回证据不足”的问题。根因是 `get_document` 返回的正文只被保留为文件名、页码和 Chunk 引用；`EvidenceSummary` 未携带受限正文摘要，最终答复节点只能看到引用元数据，不能看到“支付后 7 天内可提交退款申请”的实际政策条款。

已修复为：

1. 仅把当前用户已授权文档的最多 3 条、每条最多 1,600 字符的脱敏摘要传给最终答复节点；
2. 摘要与业务 `verifiedFacts`、工单摘要分离，不会写入人工工单；
3. 最终答复提示词将知识摘要标记为“不可信检索数据”，不得执行其中任何指令或改变权限；
4. 新增 WebSocket 回归：`退款政策是什么？` 必须看到“7 天”正文、输出来源引用，且不得创建工单；
5. 同时修复该 E2E 测试在 MySQL 下跨 `asyncio.run` 复用连接池导致的事件循环错误。

受影响单测和 WebSocket E2E 为 `4 passed`；后续新增 429 诊断与误工单回归后，Docker 全量回归为 **126 passed，1 warning**。API 已以新镜像重建，`/health` 返回 200。

### 3.4 修复后的真实 DeepSeek 复验

在用户授权后，以普通权限测试夹具走 WebSocket `/chat` 发送 `退款政策是什么？`。Generation `58513909b9a54d5abeed4fbe6722ab2d` 在约 7 秒内 `COMPLETED`：最终答复明确给出“支付完成后 7 天内可提交退款申请”，并列出 `refund-policy.md` 等来源编号。

服务端持久化追踪显示：`billing` 与 `knowledge` 路由均被选择；1 次 Billing MCP 和 2 次知识检索均成功；三个质量门全部通过（覆盖率 1.0）；`handoffAttempted=false`、`handoffId=null`。账本最终结算 13,956 LLM Tokens（100,000 → 86,044）。完整事件和账本过程见 [DEEPSEEK_LIVE_TEST_REPORT.md](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。

### 3.5 用户自身 429 限流诊断与误工单修复

对已确认的用户自身 429，质量门现在以结构化 `verifiedFacts` 判定证据充分性，并单独核验最终答复是否呈现请求号、`HTTP 429 / RATE_LIMIT_EXCEEDED`、可用统计和“不能仅凭 429 判断月额度耗尽”的边界。模型遗漏这些要点时，追踪标记为“证据充分、答复遗漏”并触发 `repaired_from_verified_evidence`，而不是返回“证据不足”。API 质量门同时核验这些字段与凭据安全。

真实复验的最终 Generation `0487496b051d46dda43862425c9962fd` 在 9 秒内完成：`/v1/chat` 2 次调用中 1 次为 429，答复完整呈现该事实和月额度边界；质量门 3/3 通过、`handoffAttempted=false`、`handoffId=null`。随后，针对“模型明明看到充分事实却输出证据不足”的质量门语义新增强制回归并部署，Docker 全量仍为 126 通过；为控制成本未追加第四条真实 429 请求。同时修复了“局部只读 Tool 失败即自动建工单”的规则：同轮已有可用事实时只保留失败记录，不转人工。完整过程及三条受控请求成本见 [DEEPSEEK_LIVE_TEST_REPORT.md](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。

## 4. 网络问题

项目文档已经说明：

- Docker 不会自动继承 Windows 系统代理；
- Clash 需要通过 `host.docker.internal` 提供容器代理；
- DashScope 需要检查 DNS、代理端口和 `EMBEDDING_HTTP_PROXY`；
- 无 Embedding Key 时才使用本地 hash embedding；
- 真实模型测试不应在网络失败时批量重试。

本轮实际确认：

1. Docker Desktop 与 Docker Engine 已启动；Docker CLI 未加入 PATH，但使用 Docker Desktop 安装目录中的 CLI 已完成 Compose 启动和全量测试；
2. `backend/.env` 中 Embedding Key 非空时，程序按远端模式执行；
3. DashScope 仍依赖 Windows DNS/代理，不能把本地离线 RAG 结果当成远端 Provider 结果；
4. 临时清空进程级 `EMBEDDING_API_KEY` 后，本地 RAG 全部通过。

详细处理见 [NETWORK_TROUBLESHOOTING.md](../reference/OPERATIONS_2026-11-19.md#network)。

## 5. 当前剩余问题

1. 修复前端依赖安装状态后重新运行 ESLint；
2. 恢复 DashScope DNS/代理后重新执行远端 Embedding 连接测试；
3. 优化真实客服问答的规划轮次、重复 Tool 调用和 Token 预算；退款与 429 真实复验的单条成本仍偏高；
4. 继续保持真实 DeepSeek 测试的小样本和预算控制，不能用离线测试替代；
5. 后端 Ruff 仍有存量告警，不影响当前功能测试，但暂不适合作为严格静态门禁。

## 6. 推荐复验顺序

```text
Docker Desktop / Compose
  → docker compose config --quiet
  → docker compose up -d --build
  → Docker 全量 pytest
  → Provider 连接测试
  → 最多 1～4 条受控 DeepSeek Live
```

本报告未记录任何 API Key、密码、Bearer Token 或完整模型请求内容。

## 7. 2026-09-09 限流客户问答全流程最终复验

在用户授权继续真实测试后，已重建 API 并确认健康检查 `200`。完整流程覆盖普通用户的个人 429 查询、未知请求号查询和显式转人工查询：三条请求均经 WebSocket、只读诊断工具、证据汇总、质量门、持久化审计和最终回复收束为 `COMPLETED`。

| 场景 | 最终行为 |
|---|---|
| 确认存在的 `req_demo_429_u11` | 正确报告 `/v1/chat` 的 `HTTP 429 (RATE_LIMIT_EXCEEDED)` 与“最近 60 分钟 2 次、1 次 429”，并说明不能由此推断月额度耗尽；不建工单。 |
| 不存在的请求号 | 明确区分“未查到该请求”与“接口近期统计有 429”：不会把近期统计伪装成该请求的事实；不建工单。 |
| 确认 429 + 明确要求人工 | 创建并持久化工单 `CS_c859a4003361425fb9e1`，且最终答复展示相同工单号。 |

最后一条运行 `65f364e062a447819c5b1ab124d13369` 的审计结果为：`handoffSuccess=true`；质量门以 `rateLimitEvidenceSufficient=true`、`rateLimitFactsCovered=false` 识别“证据充分但模型草稿遗漏”，执行 `repaired_from_verified_evidence`，而非错误输出“证据不足”。Docker 全量回归更新为 **128 passed，1 warning**。三条最终验收的真实模型结算为 51,236 Tokens，功能通过但成本优化仍是待办。完整事件、审计字段和测试工单说明见 [DEEPSEEK_LIVE_TEST_REPORT.md](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。

随后以自然语言“我被限流了，怎么回事”进行真实复验，得到知识库引用 `rate-limit.md`，但发现当前短句追问规则过宽：测试复用了活动会话，80 字内的句子自动继承上一轮 `request_id`。因此该次回答虽有真实证据，却不能代表“无上下文首次提问”已通过；需修复实体继承条件，并修复一次 `search_knowledge` 的非法 `category` 参数。详见 [真实模型限流测试报告](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。

随后创建了**空白新对话**后再次发送同一首条消息，确认不再继承 `request_id`，但发现更关键的首次问答缺陷：系统仅查询文档和错误码释义，却将用户口述“限流”写成已核验的 `RATE_LIMIT_EXCEEDED` 与个人事件。该结论没有请求日志、近期统计或用户提供的错误码支撑，故首次自然语言限流问答当前判定为**失败**；必须改为文档型解释 + 补充诊断信息引导，不得把错误码定义当作用户事件事实。

### 7.1 质量门过滤重构后的最终验收

质量门现只删除没有用户/日志/统计证据的个人诊断句，不再生成或重写“已核验”结论；`query_error_code` 仅作为错误码释义，诊断工具参数必须来自用户实体或前一轮调用日志。首次提问的最终真实复验 `bfd8b76fec854633baec2f48a9645cb2` 仅运行两次知识检索，回复正确保留限流文档解释、QPS/额度边界、恢复建议和待补充字段，未声称已核验用户 429 或错误码。Docker 全量回归更新为 **129 passed，1 warning**。完整过程见 [真实模型限流测试报告](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。
