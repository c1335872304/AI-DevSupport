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

## 5. Billing MCP

本项目只有 Billing MCP；它只处理套餐、用量和账单的只读事实：

```text
PaiSmart Agent
 -> Tool Runtime
 -> MCP Client Adapter
 -> Billing MCP Server
```

要求：

- token/secret 使用环境变量或 Secret Manager。
- 仅暴露 `get_plan`、`get_usage`、`get_invoice`。
- Tool 自身继续执行 scope / role / risk policy。
- 只读 Tool 可以并行；写操作不能因为 MCP 化而绕过资源冲突和授权。
- 不把远程 MCP 返回文本视为系统指令。

个人 Demo 通过 Docker 内部网络隔离 Billing MCP，不映射 MCP 端口到宿主机；若未来开放网络访问，必须开启 Bearer Auth 并映射真实用户/scopes。


### Billing MCP Adapter

生产环境建议保持 Agent-facing Tool contract 稳定：

```text
Billing Agent
 -> query_plan / query_usage / query_bill
 -> Billing MCP Adapter
 -> Billing MCP Server
```

配置：

```env
BILLING_MCP_ENABLED=true
BILLING_MCP_URL=http://billing-mcp:8011/mcp
BILLING_MCP_BEARER_TOKEN_ENV=BILLING_MCP_TOKEN
BILLING_MCP_TIMEOUT_SECONDS=30
```

Billing MCP 仅允许 `get_plan`、`get_usage`、`get_invoice`。个人 Demo 中 `customer_id` 由 API 的已认证用户上下文注入；退款、套餐变更和支付争议只能在证据汇总后转人工。完整容器化步骤见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md)。

## 6. 客户数据与知识库边界

生产环境应明确区分：

```text
Knowledge / RAG
= policy, FAQ, product manual, troubleshooting guide

Billing MCP
= current customer's plan, usage and invoice facts only
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
