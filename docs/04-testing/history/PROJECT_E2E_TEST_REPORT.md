# PaiSmart 完整项目 E2E 测试报告

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](README.md)。


执行日期：2026-09-09  
执行范围：Docker Demo、FastAPI、LangGraph Target Workflow、DeepSeek、Qwen Embedding Provider、Billing MCP、前端浏览器、聊天记录、工单、用量与管理员页面。  
状态：这是修复前基线报告；修复后的执行结果以 [PROJECT_E2E_REMEDIATION_REPORT.md](PROJECT_E2E_REMEDIATION_REPORT.md) 为准。基线中的 118/1 回归失败和旧的 7 条 Live 记录不应与最新复验混用。

## 1. 执行边界

- 复用已有 RAG 专项结果，不重复运行 14/60/60 条 RAG 批量评测。
- 使用本地 `demo_user` 作为普通用户，管理员使用本地 `admin`；密码不写入报告。
- DeepSeek 真实请求固定为 7 条，不自动重试；包含一组历史追问。
- 未执行真实 CRM 同步、生产部署和大规模并发压测。
- 未执行文件上传写入型 UI 测试，避免污染共享 Demo 数据。

## 2. 环境与 Provider 检查

| 检查项 | 结果 | 证据 |
|---|---|---|
| Compose 服务 | 通过 | API、MySQL、Redis、Elasticsearch、MinIO、Kafka、Billing MCP、Worker、Frontend 均运行；API/依赖健康 |
| API 健康 | 通过 | `http://127.0.0.1:8000/health` 返回 200，`{"status":"ok"}` |
| 前端首页 | 通过 | `http://127.0.0.1:9527/` 返回 200 |
| DeepSeek Provider | 通过 | `/admin/model-providers/llm/test` 返回 200，延迟约 323 ms |
| Qwen Embedding Provider | 通过 | `/admin/model-providers/embedding/test` 返回 200，延迟约 203 ms |
| 前端类型检查 | 通过 | `pnpm typecheck` |
| 前端生产构建 | 通过 | `pnpm build` |

## 3. 离线全量回归

执行命令：

```text
docker compose --profile test run --build --rm test pytest -q tests
```

结果：**118 passed，1 failed，1 warning**。

失败用例：

```text
tests/e2e/test_websocket_architecture.py::test_websocket_to_agent_final_answer_e2e_without_llm_api_key
```

失败点是测试夹具期待 `get_document` 被调用，但固定的 `stream_agent_turn` 只模拟了第一轮 `search_knowledge` Tool 调用；同一用例的 WebSocket 鉴权、路由、Tool 执行、证据汇总、handoff 决策、安全节点和 completion 事件均已通过。该问题需要修正测试夹具或明确 Target Workflow 的多轮 Tool 预期，当前不能把离线门禁标记为全绿。

## 4. DeepSeek 真实用户流程

7 条请求均收到 `completion=finished`，没有超时；每条请求都走过真实 WebSocket、Target Workflow、Tool Runtime、Safety 和持久化。

| 用例 | 用户问题类型 | 结果 | 关键路径 |
|---|---|---|---|
| LIVE-01 | 退款政策 | 完成，但回答被安全门降级为“证据不足” | Billing + Knowledge + 引用 |
| LIVE-02 | `req_demo_401` / 401 | 完成，但未给出完整诊断，转人工 | API 诊断、知识检索、`create_support_handoff` |
| LIVE-03 | 历史追问“那为什么会这样？” | 完成，但回答被安全门降级 | 历史上下文、API 诊断、RAG |
| LIVE-04 | `/v1/chat` / 429 | 完成，但回答被安全门降级 | QPS 统计、错误码、RAG、父文档 |
| LIVE-05 | 2026-08 账单解释 | 完成，但安全门未通过 | Billing MCP `get_plan/get_usage/get_invoice` |
| LIVE-06 | 个人退款到账状态 | 完成，但安全门未通过 | Billing MCP 只读账单核验 |
| LIVE-07 | 明确要求转人工 | 通过 | `target_create_handoff` 返回有效 `handoffId` |

### 4.1 真实调用成本

测试前普通用户余额：LLM `999,843`，Embedding `1,000,000`。  
测试后普通用户余额：LLM `926,367`，Embedding `1,000,000`。  

本轮 7 条问题的增量约为 **73,476 LLM Tokens**；Embedding 余额没有出现扣减记录。请求均未自动重试，但事件中多次出现同名 Tool 调用，说明 Target Workflow / Agent 回合存在重复调用或重复计费风险，需要单独优化。

### 4.2 回答质量观察

传输层是 7/7 完成，但业务回答不是 7/7 通过：退款政策、历史追问、429、账单和个人退款问题多次返回安全兜底，而不是可用的事实回答。`LIVE-01` 的引用中出现了 `fixture-refund-policy-v2025.md`、`fixture-refund-policy-v2026.md` 等隔离夹具，说明当前共享 Elasticsearch 索引会污染面向用户的 Live 检索；应使用干净 Demo 索引或强制 metadata/version 隔离后重测。

## 5. 持久化、工单与权限

| 检查项 | 结果 | 证据 |
|---|---|---|
| 普通用户身份 | 通过 | `/users/me` 返回 `demo_user / USER` |
| 用户余额与用量 | 通过 | `/users/usage`、`/users/token-records` 返回可读账本 |
| 会话持久化 | 通过 | 当前会话读取到 20 条消息（10 user + 10 assistant） |
| 普通用户工单列表 | 通过 | `/support/handoffs` 返回 2 条本轮工单 |
| 工单详情 | 通过 | 普通用户可读取自己的 handoff |
| 管理员工单列表 | 通过 | `/support/admin/handoffs` 返回 2 条 |
| 管理员更新工单 | 通过 | 工单从 `OPEN` 更新为 `IN_PROGRESS`，写入处理人和备注 |
| 管理员用户/用量/聊天记录 | 通过 | `/admin/users`、`/admin/usage/overview`、`/admin/conversation` 均返回 200 |
| 普通用户访问管理员接口 | 通过 | `/admin/usage/overview`、`/support/admin/handoffs` 返回 403 |

## 6. 浏览器前端验收

使用本机 Chrome 无头浏览器访问 `http://127.0.0.1:9527`，不再发送聊天问题。

### 普通用户

- 登录成功并跳转 `/chat`；
- 聊天、知识库、个人中心和对话列表可见；
- 管理员菜单（用量监控、用户管理、充值管理等）正确隐藏；
- 没有独立的“聊天记录”菜单，历史记录通过聊天页的“对话列表”和 API 查询；
- 该菜单差异与当前测试方案中“普通用户打开聊天记录”描述不完全一致，应调整方案或补充普通用户入口。

### 管理员

以下页面均能加载且没有 5xx 空状态：

```text
/user
/chat-history
/knowledge-base
/model-provider
/usage-monitor
/recharge-manage
```

## 7. 发现的问题与优先级

| 优先级 | 问题 | 影响 |
|---|---|---|
| P1 | 真实 Live 多数回答被安全门降级，不能稳定回答已检索到的 Demo 政策/故障问题 | 用户体验与客服解决率不足 |
| P1 | 7 条问题消耗约 73,476 LLM Tokens，事件中存在重复 Tool 调用 | 成本不可控，需先限流/去重再扩大测试 |
| P1 | 共享索引混入 RAG 夹具文档，导致公开退款问题召回版本夹具 | 线上 Demo 结果被测试数据污染 |
| P1 | 前端 Nginx 在 API 容器重建后缓存旧 IP，出现登录 502；重启 frontend 后恢复 | 部署重建后前端可能再次不可登录 |
| P2 | `test_websocket_architecture` 夹具与当前多轮 Tool 行为不一致 | 离线 CI 不能全绿 |
| P2 | 普通用户没有独立“聊天记录”菜单，但 API 和聊天页对话列表可用 | 方案与界面入口描述不一致 |

## 8. 当前结论

- 基础设施、Provider、API、WebSocket、Agent 节点、Tool、工单、用量、权限和管理员页面均已实际走通。
- 核心系统“能运行”的结论成立；普通用户到工单/用量/管理员闭环已有真实证据。
- 但完整项目验收**尚未通过**：离线回归有 1 项失败，真实回答质量和 Token 成本存在明显问题，前端代理还暴露了容器重建后的 502 风险。
- 在修复索引污染、重复 Tool 调用、回答安全门和 Nginx 服务发现前，不建议继续扩大 Live 测试规模。

## 9. 建议的修复后重测顺序

1. 清理或隔离 RAG fixture 索引，保留公开 Demo 文档；
2. 统计同一 generation 的重复 Tool 调用和重复 LLM 请求，增加单 generation 上限；
3. 修复安全门对有效引用回答的判定，重新跑 LIVE-01、03、04、05、06；
4. 修复 Nginx 动态服务发现，或把 API/Frontend 重建顺序写入 Compose 运维流程；
5. 修正 WebSocket 离线测试夹具；
6. 仅在单次 Live 成本恢复可控后，再抽样执行用户问题模拟库。
