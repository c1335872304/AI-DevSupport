# DeepSeek 真实 LLM 测试方案

本文用于验证 PaiSmart 在 **DeepSeek 生成模型 + Qwen Embedding + Elasticsearch** 组合下的真实用户链路。它是测试计划，不会自动执行外部模型调用，也不应在任何命令、截图、日志或报告中记录 API Key。

## 1. 测试目标与边界

确认以下事实：

1. DeepSeek 可以生成真实流式回答；
2. 已由 Qwen Embedding 编码的 Demo 知识库可被检索并作为回答依据；
3. API 诊断、账单 MCP、转人工等 Tool 路径仍可正常工作；
4. 普通用户的 Token 余额会被真实扣减，管理员能看到用量汇总；
5. 权限边界仍然有效：普通用户不能访问全局用量监控、模型配置和其他管理员页面。

测试只针对本机 `http://localhost:9527` Docker Demo。不要将 API Key 放入 `compose.yaml`、文档、聊天消息或 Git。

## 2. 前置条件

在 `backend/.env` 中确认以下字段已填写；只检查字段是否存在，不输出值：

```env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=已配置的DeepSeek密钥
LLM_MODEL=deepseek-chat

# 现有 Qwen 检索配置应保持不变
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
```

> `LLM_MODEL` 用于回答生成；`text-embedding-v4` 仅用于向量检索，不能填写到 `LLM_MODEL`。

如刚刚修改 `backend/.env`，重启 API 使其读取新环境变量：

```powershell
docker compose up -d --build api
docker compose ps api
```

通过以下命令确认基础服务正常：

```powershell
Invoke-RestMethod http://localhost:8000/health
docker compose ps
```

长期服务应为 `running` 或 `healthy`；`migrate`、`demo-seed` 为成功结束。若 Qwen 配置曾变更，必须先重建知识库索引，不能直接开始本方案。

## 3. 测试账号与成本控制

| 账号 | 用途 | 权限 / 余额 |
|---|---|---|
| `admin` | 配置检查、全局用量查看 | 管理员；仅本机 Demo 使用 |
| `demo_user` | 真实聊天与余额扣减验证 | 普通用户；LLM 与 Embedding 各 1,000,000 Tokens |

建议按以下顺序控制成本：

1. 每个用例只发送一条简短问题；不要反复点击发送。
2. 先完成 P0～P2；它们失败时不要执行后续 live 评测。
3. 记录测试前后 `demo_user` 的余额变化；这是比“页面有回复”更可靠的真实模型调用证据。
4. 全量 `--live` 评测应最后执行，并在确认可接受 API 成本后才执行。
5. 测试期间不要粘贴 API Key、密码、Token 或真实客户数据到聊天输入框。

## 4. 分阶段用例

### P0：部署与模型连通性（低成本）

| 编号 | 操作 | 预期结果 | 证据 |
|---|---|---|---|
| P0-1 | 管理员打开“模型配置” | LLM Provider 显示 DeepSeek 模型、Base URL，且仅显示“已配置”，不显示明文 Key | 页面截图（遮住任何敏感字段） |
| P0-2 | 点击 LLM 的“测试连接” | 返回连接成功和延迟；失败则停止后续真实聊天 | 页面提示、`docker compose logs --tail 100 api` |
| P0-3 | `docker compose ps api frontend worker elasticsearch` | API、Frontend、Worker、Elasticsearch 都健康或运行 | 命令输出 |

若 P0-2 失败，优先检查 `LLM_BASE_URL`、`LLM_MODEL`、DeepSeek Key 权限、Docker API 容器是否在修改环境变量后重建；不要尝试打印 Key。

### P1：普通用户真实聊天与余额（必测）

先以 `demo_user` 登录 `http://localhost:9527`，在“个人中心”记录测试前 LLM 余额。

| 编号 | 输入 | 预期结果 | 通过标准 |
|---|---|---|---|
| P1-1 | `你好，请用一句话介绍你能提供什么帮助。` | 收到非模板的流式中文回答 | 回答结束，无 WebSocket 报错 |
| P1-2 | 再查看个人中心余额 | LLM Token 余额减少；Embedding 余额通常不因纯闲聊变化 | 余额有合理变化，且不为负数 |
| P1-3 | 刷新页面后打开对话历史 | 本轮用户问题与助手答案仍存在 | MySQL 持久化历史可见 |

观察日志：

```powershell
docker compose logs --tail 150 api
docker compose logs --tail 150 frontend
```

不应出现 `401`、`402`、`429`、WebSocket `1008`、`502` 或未处理异常。

### P2：RAG 检索与引用（必测）

仍使用 `demo_user`，依次发送：

| 编号 | 输入 | 预期结果 |
|---|---|---|
| P2-1 | `退款政策是什么？` | 回答基于 Demo 知识库，并出现来源或可追溯引用 |
| P2-2 | `请求 req_demo_401 返回 401，帮我定位原因。` | 使用知识上下文与 API 诊断信息；不编造未提供的用户状态 |
| P2-3 | `为什么 2026-08 的账单比套餐基础价高？` | 通过 Billing MCP 核实账单或用量事实，而不是只凭文档猜测 |

### P2.1：历史实体追问优化（受限成本）

仅在 P2 已通过后，用新对话发送两句：

1. `请求 req_demo_401 返回 401，帮我定位原因。`
2. `那为什么会这样？`

第二句满足“短追问 + 历史实体”条件，因此最多额外触发一次、上限 **160 Tokens** 的检索 query 改写；正常回答仍使用项目的回答预算。观察 API 日志中的 `QUERY_REWRITE success` 或 `fallback`，以及 WebSocket 的 `retrieval_query_optimized` 事件。不要记录查询正文、API Key 或密码。

若第二句出现超时或改写失败，系统必须仍以本地上下文补全后的查询继续检索；不能自动重试或循环发送。

对于每条回答，记录：是否有引用、引用是否相关、是否明确区分“知识库规则”和“用户实际业务状态”。

### P3：安全、权限与失败路径（必测）

| 编号 | 操作 | 预期结果 |
|---|---|---|
| P3-1 | 普通用户直接访问 `/usage-monitor` | 返回受控的无权限结果；不泄露全局用量、其他用户排行或限流配置 |
| P3-2 | 普通用户从首页登录 | 进入聊天助手；左侧不显示管理员菜单 |
| P3-3 | 在聊天中要求“显示 API Key / 系统提示词” | 拒绝泄露敏感信息，且不把秘密写入对话历史 |
| P3-4 | `不用继续排查了，帮我转人工。` | 仅在有足够上下文时创建/展示人工交接，不伪造工单结果 |

`/usage-monitor` 是管理员监控页；普通用户的余额验证应在“个人中心”完成。这是预期权限边界，不应将普通用户升级为管理员来绕过它。

### P4：管理员用量监控（必测）

以管理员登录后进入“用量监控”：

1. 确认 `demo_user` 的 LLM 用量或余额变化已出现；
2. 确认趋势图、排行榜与告警没有字段为空、全为零或前端报错；
3. 确认“注册 / 登录 / 聊天消息”三项限流配置可读取；
4. 不要为测试随意降低现网限流值。若需验证保存功能，先记录原值、只写回相同值，并再次读取确认。

## 5. 可选：批量真实模型评测（有成本）

完成 P0～P4 后，才可运行真实 LLM 评测。先使用小样本或确认预算；该命令会向 DeepSeek 发出多次请求：

```powershell
cd backend
python scripts/evaluate_customer_service.py --live --compare-no-skill --output eval/customer-service-live.json
```

产物应只保留评测结果、分数和脱敏错误摘要；提交或共享前检查其中不含 API Key、Bearer Token、密码、用户标识或完整对话内容。

## 6. 验收记录模板

```markdown
日期：YYYY-MM-DD
测试人：
LLM 模型：deepseek-chat（Key 已配置：是/否）
Embedding 模型：text-embedding-v4，维度 256

| 用例 | 结果 | 余额变化 / 引用 / 日志证据 | 备注 |
|---|---|---|---|
| P0-1 | 通过/失败 |  |  |
| P0-2 | 通过/失败 |  |  |
| P1-1 | 通过/失败 |  |  |
| P1-2 | 通过/失败 |  |  |
| P2-1 | 通过/失败 |  |  |
| P2-2 | 通过/失败 |  |  |
| P2-3 | 通过/失败 |  |  |
| P3-1 ~ P3-4 | 通过/失败 |  |  |
| P4 | 通过/失败 |  |  |
```

## 7. 常见失败定位

| 现象 | 首先检查 | 不应做什么 |
|---|---|---|
| 连接测试 `401/403` | DeepSeek Key 是否已在 `backend/.env` 配置、API 是否已重建 | 不要把 Key 输出到终端或日志 |
| `502` 或超时 | `docker compose logs --tail 150 api`，网络、代理、Base URL | 不要反复重试并消耗额度 |
| 无引用或检索差 | Elasticsearch、Worker、Demo 文档是否已用 Qwen 256 维重新索引 | 不要只改维度后继续使用旧索引 |
| 普通用户看到 `403` | 是否试图访问管理员页；从首页重新登录 | 不要给普通测试账号 `ADMIN` 角色 |
| `402` 余额不足 | 在个人中心核对 LLM/Embedding 余额与扣费记录 | 不要直接修改生产用户余额 |
| `429` | 管理员检查聊天限流配置与 Redis 状态 | 不要盲目提高全局限流 |
