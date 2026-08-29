# 本地启动

## 1. 运行模式

### Minimal Local

适合读代码、开发和测试 AI 客服主链路：

```text
SQLite
Local Storage
Background Processing
Database Retrieval
Local Hash Embedding（未配置 API Key 时）
Context-only LLM fallback（未配置 LLM Key 时）
```

可以体验 LangGraph 客服工作流、客服 Skill、知识检索、真实人工 handoff 持久化和并行 Tool Runtime，不要求额外基础设施。

### Full Infrastructure

用于完整生产链路：

```text
MySQL
Redis
MinIO
Elasticsearch
Kafka
Real LLM / Embedding Provider
Optional external MCP business systems
```

## 2. 后端

要求 Python 3.11+。

```bash
cd backend
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

macOS/Linux：

```bash
source .venv/bin/activate
```

安装并启动：

```bash
pip install -r requirements.txt
cp .env.example .env
python run.py
```

访问：

```text
API       http://localhost:8000
Swagger   http://localhost:8000/docs
Health    http://localhost:8000/health
Metrics   http://localhost:8000/metrics
WebSocket ws://localhost:8000/chat
```

开发模式默认创建 SQLite schema 和 bootstrap admin。生产环境使用 Alembic，不依赖自动建表。

## 3. API 诊断 / Billing Demo 数据（可选）

如果希望本地直接演示原 AI-DevSupport 的 API 技术支持与账单能力，完成数据库初始化后执行：

```bash
cd backend
python scripts/seed_support_demo.py --username admin --reset
```

会为指定用户写入脱敏演示数据：

```text
app_demo
req_demo_401 -> 401 / AUTH_KEY_EXPIRED
req_demo_429 -> 429 / RATE_LIMIT_EXCEEDED
Professional plan -> QPS 50 / 月配额 1,000,000
2026-08 usage -> 1,250,000 calls / 250,000 overage
2026-08 invoice -> 424.0
```

可测试：

```text
“请求 req_demo_401 返回 401，帮我定位原因。”
“app_demo 的 /v1/chat 最近一直 429，是不是限流？”
“为什么 2026-08 的账单比套餐基础价高？”
```

生产环境应由真实业务数据库或 MCP 同步这些数据，不使用 demo seed。

## 4. Demo 客服知识库（推荐）

项目自带 7 份面向 AI 客服的 Markdown 知识文档：

```text
api-getting-started.md
authentication.md
rate-limit.md
billing-policy.md
refund-policy.md
error-codes.md
troubleshooting-faq.md
```

先验证 Parser / Parent-Child Chunking：

```bash
cd backend
python scripts/seed_demo_knowledge.py --validate-only
```

然后一键走真实建库链路：

```bash
python scripts/seed_demo_knowledge.py --username admin --reset
```

默认以 public 文档写入当前用户的 primary organization；如希望只有文档拥有者可检索：

```bash
python scripts/seed_demo_knowledge.py --username admin --reset --private
```

重复运行默认会跳过已经完成索引且内容未变化的文档；强制重建可使用：

```bash
python scripts/seed_demo_knowledge.py --username admin --reindex
```

建库后验证 RAG：

```bash
python scripts/evaluate_rag.py eval/demo_knowledge_rag.jsonl --username admin -k 6
```

推荐直接问：

```text
“AUTH_KEY_EXPIRED 怎么处理？”
“429 一定代表月额度用完了吗？”
“Professional 套餐超额费用怎么算？”
“我的退款到账了吗，能不能直接从知识库判断？”
“接口超时时应该先收集什么信息？”
```

其中前三类知识问题可以由 RAG 回答；“我的退款是否到账”仍必须依赖真实业务 Tool/MCP，Demo 文档明确禁止根据政策推断个人状态。

## 5. 前端

```bash
cd frontend
pnpm install
pnpm dev
```

常用检查：

```bash
pnpm typecheck
pnpm lint
pnpm build
```

聊天前端使用 `/proxy-ws/chat`，本地 Vite proxy 和生产 Nginx 都应转发到后端 `/chat`。

## 6. 推荐的客服 Smoke Test

启动后可以按顺序测试：

```text
1. “你们的退款政策是什么？”
   预期：customer-support + knowledge search

2. “我登录一直报错，验证码也收不到。”
   预期：customer-support + troubleshooting

3. “不用继续排查了，帮我转人工。”
   预期：customer-support + escalation + real handoffId
```

用户可以通过：

```text
GET /api/v1/support/handoffs
```

查看自己的人工交接；管理员可通过 `/api/v1/support/admin/handoffs` 处理工单。

## 7. Full Infrastructure

```bash
docker compose -f deploy/compose.infra.yml up -d
cd backend
cp .env.full.example .env
alembic upgrade head
python run.py
```

Kafka Worker：

```bash
python -m app.workers.file_processor
```

## 8. LLM / Embedding

LLM 使用 OpenAI-compatible 接口：

```env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=...
LLM_MODEL=deepseek-chat
```

Embedding：

```env
EMBEDDING_BASE_URL=...
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
```

更换 Embedding model 或维度后应重新向量化客服知识文档。

## 9. 外部业务 MCP

订单、支付、账户、物流等个人状态推荐通过 MCP Client 接入。V14 提供稳定的 Business MCP Adapter：LLM/Skill 仍调用本地稳定 Tool 名，底层实现可从 Demo DB 切换成远程 MCP。

```env
MCP_REMOTE_SERVERS_JSON={"business":{"url":"https://business.example.com/mcp","bearerTokenEnv":"BUSINESS_MCP_TOKEN","readOnly":true}}
BUSINESS_TOOL_BACKEND=mcp
BUSINESS_MCP_SERVER=business
BUSINESS_MCP_TOOL_MAP_JSON={"query_bill":{"tool":"get_invoice","userArgument":"customer_id"},"query_usage":{"tool":"get_usage","userArgument":"customer_id"}}
```

如果远端 Tool 与本地 Tool 同名，`BUSINESS_MCP_TOOL_MAP_JSON={}` 即可。`customer_id` 只是业务路由上下文，远端 MCP 仍必须依据 bearer token/scopes 自己完成授权。

具体安全要求见 [AGENT_AND_SKILLS.md](AGENT_AND_SKILLS.md) 和 [PRODUCTION.md](PRODUCTION.md)。

## 10. 测试与客服 Benchmark

```bash
cd backend
pytest -q
python scripts/evaluate_skills.py
python scripts/evaluate_answers.py
python scripts/evaluate_customer_service.py
python scripts/evaluate_customer_service.py --dataset eval/customer_service/benchmark_extended.jsonl
```

内置 Demo Knowledge RAG Eval：

```bash
python scripts/evaluate_rag.py eval/demo_knowledge_rag.jsonl --username admin -k 6
```

真实自定义 RAG Eval：

```bash
python scripts/evaluate_rag.py eval/my_dataset.jsonl --username admin -k 6 --output eval/rag-report.json
python scripts/evaluate_customer_service.py --rag-report eval/rag-report.json
```

配置 `LLM_API_KEY` 后可以运行完整客服 Agent fixture A/B：

```bash
python scripts/evaluate_customer_service.py --live --compare-no-skill --output eval/customer-service-live.json
```
