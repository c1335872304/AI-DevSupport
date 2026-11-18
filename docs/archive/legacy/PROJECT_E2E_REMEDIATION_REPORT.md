# PaiSmart E2E 修复复验报告

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../reports/RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](../README.md#legacy)。


执行日期：2026-09-09\
关联计划：[PROJECT_E2E_REMEDIATION_PLAN.md](PROJECT_E2E_REMEDIATION_PLAN.md)\
执行边界：完成离线测试、前端构建、本地 Docker 容器重建、12 条旧 RAG 夹具的受控清理、4 条 DeepSeek 真实请求，以及普通用户浏览器验收。未运行批量评测，未发送新的 Qwen Embedding 请求。

## 1. 修复结果

| 编号 | 实施内容 | 结果 |
|---|---|---|
| R1 | 正常检索、文档列表和文档读取默认排除 `fixture-*`；盲测脚本须显式传入评测开关；新增受控 `--cleanup` 命令 | 已实施；明确 owner/prefix 命名空间实际删除 12 条，复查为 0 |
| R2 | 最终回答提示词带入允许引用；若模型漏写引用尾注，系统只从已验证 references 补齐 `来源#n` | 已实施；Live 中引用能落到页面，但部分问题仍触发质量门兜底 |
| R3 | 引入请求级 `tool_name + 规范化参数` 指纹；共享调度器去重并记录拒绝原因；每 generation 最多 8 次读 Tool | 已实施；硬上限生效，但真实模型仍有多轮调用和高成本 |
| R4 | Nginx 使用 Docker DNS `127.0.0.11` 和运行时 upstream 变量，并显式重写 `/proxy-ws/*` URI | 已实施；容器重建后 HTTP 与 WebSocket 均验证通过 |
| R5 | WebSocket E2E mock 显式模拟搜索后读取父文档的第二轮 Tool | 已实施 |
| R6 | 新增普通用户 `/my-chat-history` 菜单页，只使用当前用户会话 API，管理员全量 `/chat-history` 保持不变 | 已实施；浏览器已登录普通用户并看到入口、会话和“查看”按钮 |

## 2. 离线验证

| 检查 | 命令 / 方法 | 结果 |
|---|---|---|
| 受影响后端回归 | `pytest` 覆盖 Scheduler、Target Agent、Skill、RAG metadata、WebSocket | 21 passed，1 warning |
| 完整后端回归 | `docker compose --profile test run --rm test pytest -q tests` | **123 passed，1 warning** |
| 前端类型检查 | `pnpm typecheck` | 通过 |
| 前端生产构建 | `pnpm build` | 通过 |
| API 重建代理检查 | 保持 frontend 运行，强制重建 api；健康后访问受保护 `/api/v1/users/me` | 返回预期 **401**，非 502 |
| Nginx WebSocket | 重建 frontend 后经 `/proxy-ws/chat` 鉴权握手 | 收到 `connection` 事件；API 不再记录 `WebSocket /` 的 403 |
| 普通用户聊天历史 | 浏览器登录 `demo_user`，打开 `/my-chat-history`，查看当前会话 | 页面显示“我的聊天记录”、本人会话和“查看”；API 返回同一会话的 28 条消息 |

重建后的启动期短暂 502 不作为失败：当时 API 仍处于 `health: starting`。API 变为 `healthy` 且超过 Nginx 10 秒 DNS 缓存窗口后，前端代理无需重启即恢复 401。

## 3. 受控 Live 与数据清理记录

### 3.1 RAG 夹具清理

清理范围严格限定为用户 `rag_eval_fixture_owner` 且文件名以 `fixture-` 开头的上传、向量、父块、处理任务、对象和 Elasticsearch 文档。首轮 Docker 测试镜像仍是旧版脚本，`--cleanup` 实际返回并删除 **12** 条；随后使用同一命名空间复查返回 `deleted=0`。重建 `test` 镜像后，最新脚本默认 dry-run 返回 `would_delete=0`。后续不得对其他 owner 或无前缀文件执行删除。

### 3.2 DeepSeek 受控复验

本轮仅发送 4 条请求，沿 `/proxy-ws/chat` 代理修复前先用 API 直连完成，未自动重试；每条均收到 `completion=finished`。余额从 **926,367** 降至 **879,683**，增加消耗 **46,684 LLM Tokens**；Embedding 余额保持 **1,000,000**。

| 用例 | 结果摘要 | 本条 LLM 增量 | 关键证据 |
|---|---|---:|---|
| L1 退款政策 | 完成；2 条可追溯来源；因证据没有退款条款而安全说明 | 11,949 | `search_knowledge`、`get_document`、引用尾注 |
| L2 401 诊断 | 完成；7 条来源；未编造不存在的日志/错误码 | 21,935 | `query_call_log`、`query_error_code`、引用尾注 |
| L3 历史追问 | 完成；触发 `quality_gate_blocked` 后安全转人工 | 9,953 | `retrieval_query_optimized`、`create_support_handoff` |
| L4 明确转人工 | 完成；创建工单并返回脱敏工单号 | 2,847 | `create_support_handoff`、completion |

Live 的“链路可用”门通过，但成本门未通过：L1～L3 均超过计划中的常规/诊断 4,000～6,000 Token 目标，L2/L3 还出现多轮 Tool/LLM 调用。因此本报告不把真实回答质量标记为全绿，也不继续扩大 live 样本。

### 3.3 Compose 全量更新

为避免继续使用旧容器或旧测试镜像，已在当前工作区执行：

```text
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d --force-recreate
docker compose --profile test build --no-cache test
```

停止并移除的范围仅限 Compose 项目 `paismart-demo`；未删除 MySQL、Redis、Elasticsearch、Kafka、MinIO、API 数据卷。最新启动结果：API、前端、Worker、Billing MCP 运行中；MySQL、Redis、Elasticsearch、Kafka、MinIO 健康；`migrate` 与 `demo-seed` 均以退出码 0 完成。API `/health` 返回 `{"status":"ok"}`，前端返回 HTTP 200，容器内 `nginx -t` 通过。

## 4. 尚未执行的项目

1. **独立评测索引 / Profile**：当前采用安全的查询层隔离，尚未迁移到独立 Elasticsearch 索引。
2. **成本与回答质量优化**：真实链路已跑通，但需要在不新增 live 消耗的前提下继续收紧规划轮次、单请求 Token 预算和质量门条件。
3. **浏览器菜单点击的视觉回归**：路由直达与“查看”导航已验证；菜单在窄视口下需要单独补一个可见性/响应式回归，不影响 API 权限隔离。

## 5. 当前结论

离线质量门禁已从此前的 `118 passed, 1 failed` 修复为 `123 passed, 1 warning`，并已部署到本地 Docker Demo。R1～R6 的代码级修复、夹具清理、4 条受控 DeepSeek 请求和普通用户历史页均已实际执行；Nginx WebSocket 403 也已修复。当前剩余主要问题是 Live 成本和部分问题的质量门仍偏严/调用轮次偏多，后续应先做离线预算与质量门优化，再决定是否增加真实样本。
