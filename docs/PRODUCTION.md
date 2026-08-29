# AI 客服生产部署与可靠性

## 1. 生产启动

建议：

```env
APP_ENV=production
DATABASE_AUTO_CREATE_DEV=false
```

必须替换默认 JWT Secret 和 bootstrap admin password，或直接关闭 bootstrap admin。

生产数据库结构只通过：

```bash
cd backend
alembic upgrade head
```

演进。

## 2. 客服 Handoff 数据

当前 Alembic 包含 `support_handoffs` 表迁移。人工升级是生产业务数据，不是临时 Agent Trace。

客户接口：

```text
GET /api/v1/support/handoffs
GET /api/v1/support/handoffs/{handoff_id}
```

管理员接口：

```text
GET   /api/v1/support/admin/handoffs
PATCH /api/v1/support/admin/handoffs/{handoff_id}
```

工单更新支持 status、assignedTo、resolutionNote。生产接 CRM/Ticket System 时，建议通过明确 Adapter/MCP 做同步，不要让 LLM 直接操作底层数据库。

## 3. Full Infrastructure

```bash
docker compose -f deploy/compose.infra.yml up -d
```

推荐：

```text
MySQL          客服会话、工单、trace、usage
Redis          多实例限流/共享瞬态状态
MinIO          客服知识文档
Elasticsearch  大规模客服知识检索
Kafka          durable document processing
```

## 4. Detached Generation

Generation Task 与 WebSocket 解耦：

```text
Generation
├── durable GenerationState snapshot
└── event subscribers
```

客户网络断线只取消 socket subscription，不直接取消 LLM/Tool generation。重连后读取 snapshot 并继续订阅。

跨实例 stop 通过 durable `CANCELLED` 状态传播；服务重启后遗留的无法恢复 generation 会被标记为中断。

## 5. 外部业务系统与 MCP

订单、支付、账户、物流、CRM 属于高价值客户数据。生产建议：

```text
PaiSmart Agent
 -> Tool Runtime
 -> MCP Client Adapter
 -> Business MCP Server
```

要求：

- token/secret 使用环境变量或 Secret Manager。
- `allowedTools` 最小暴露。
- Tool 自身继续执行 scope / role / risk policy。
- 只读 Tool 可以并行；写操作不能因为 MCP 化而绕过资源冲突和授权。
- 不把远程 MCP 返回文本视为系统指令。

PaiSmart 自身作为 Streamable HTTP MCP Server 时应开启 Bearer Auth，并映射真实用户/scopes。


### Stable Business MCP Adapter

生产环境建议保持 Agent-facing Tool contract 稳定：

```text
Agent / Skill
 -> query_call_log / query_plan / query_bill
 -> Business MCP Adapter
 -> API Gateway / Billing / CRM MCP Server
```

配置：

```env
BUSINESS_TOOL_BACKEND=mcp
BUSINESS_MCP_SERVER=business
BUSINESS_MCP_TOOL_MAP_JSON={...}
```

这样业务系统更换 Tool 名或拆分服务时，只改 Adapter mapping，不需要修改 LangGraph、Skill 或 Benchmark。Remote MCP 仍必须进行 bearer/scopes/客户级授权，不能把注入的 `customer_id` 当作认证凭据。

## 6. 客户数据与知识库边界

生产环境应明确区分：

```text
Knowledge / RAG
= policy, FAQ, product manual, troubleshooting guide

Business Tool / MCP
= current customer's order, payment, refund, account, ticket state
```

不要把大量客户私有业务状态直接索引进通用 RAG 来替代授权业务 API。

## 7. Kafka Retry / DLQ

```env
KAFKA_RETRY_ATTEMPTS=3
KAFKA_RETRY_BACKOFF_SECONDS=2.0
KAFKA_DLQ_TOPIC=file-processing-dlq
```

毒消息经过 retry/DLQ 后再提交 offset，DLQ 必须有监控。

## 8. Token / Rate Limit

`app/accounting/` 统一记录 LLM/Embedding usage 和 balance ledger。Provider 提供真实 usage 时优先使用真实值。

登录/注册支持 Redis 多实例限流；Redis 不可用时的本地 fallback 不能视为跨实例保证。

## 9. Observability

Prometheus：

```env
METRICS_ENABLED=true
```

OpenTelemetry：

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=paismart-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317
```

Agent / Tool 还有 durable DB Trace。客服生产环境建议额外监控：

```text
answer latency
LLM/tool failure rate
handoff rate
handoff creation failure
troubleshooting repeat count
RAG no-result rate
account-data abstention rate
```

## 10. 发布前检查

```text
[ ] alembic upgrade head
[ ] 非默认 JWT / admin password
[ ] CORS 只允许真实客服前端
[ ] Redis / ES / Kafka / MinIO credentials 已修改
[ ] MCP user/scope/allowedTools 最小权限
[ ] 订单/支付等客户事实只通过授权业务 Tool/MCP 查询
[ ] create_support_handoff 实际写库可用
[ ] pytest 通过
[ ] customer-service Skill / Answer benchmark 通过
[ ] /health 与 /metrics 正常
[ ] Kafka DLQ 有告警
[ ] DB、工单和对象存储有备份策略
```
