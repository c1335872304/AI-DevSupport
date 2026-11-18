# 本地启动

四阶段交付的独立、无Provider费用演示见[三条演示与交付启动](../03-operations/PROJECT_DEMOS.md)；当前源码范围见[候选验收](../04-testing/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)，四阶段交付见[阶段最终报告](../04-testing/FINAL_PROJECT_ACCEPTANCE.md)。已有知识库和 `.env` 不需要为演示清空或覆盖。

## 1. 运行模式

### Minimal Local

适合读代码、开发和测试 AI 客服主链路：

```text
SQLite
Local Storage
Background Processing
Database Retrieval
Qwen Embedding（建库与查询必须配置有效 Key）
Context-only LLM fallback（未配置 LLM Key 时）
```

可以体验 LangGraph 客服工作流、客服 Skill、知识检索、真实人工 handoff 持久化和并行 Tool Runtime，不要求额外基础设施。

### Full Infrastructure

用于完整基础设施链路；生产边界另见运维文档：

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
cp -n .env.example .env  # 仅首次创建；已有配置不要覆盖
python -m alembic upgrade head
python run.py
```

访问：

```text
API       http://localhost:8000
Swagger   http://localhost:8000/docs
Health    http://localhost:8000/health
WebSocket ws://localhost:8000/chat
```

首次本地可创建开发 schema 和 bootstrap admin；已有数据库先备份并运行 Alembic。create_all 不负责新增列，不能替代版本迁移。run.py 仅在 DATABASE_AUTO_MIGRATE=true 时自动执行迁移。Windows PowerShell 首次复制配置使用 Copy-Item .env.example .env，须先确认 .env 不存在。

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

默认知识库为 DeepSeek、Qwen、GPT / OpenAI 的 60 份官方正文快照，每家 20 份，使用千问 `text-embedding-v4` 编码。资料清单、来源和导入方式见 [官方文档知识库](VENDOR_KNOWLEDGE.md)。旧假想公司手册只保留作历史测试夹具，不再默认导入。

先验证 Parser / Parent-Child Chunking：

```bash
cd backend
python scripts/seed_demo_knowledge.py --validate-only
```

然后一键走真实建库链路：

```bash
python scripts/seed_demo_knowledge.py --username admin
```

默认以 public 文档写入当前用户的 primary organization；如希望只有文档拥有者可检索：

```bash
python scripts/seed_demo_knowledge.py --username admin --private
```

重复运行默认会跳过已经完成索引且内容未变化的文档；强制重建可使用：

```bash
python scripts/seed_demo_knowledge.py --username admin --reindex
```

建库后验证 RAG：

```bash
python scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6
```

推荐直接问：

```text
“DeepSeek 的 402 和 429 分别表示什么？”
“Qwen 的 API Key 如何配置？”
“GPT API 的限流应该如何处理？”
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

Docling 的独立环境和模型准备见 [RAG 操作手册](../03-operations/RAG_OPERATIONS.md)。仅运行 Markdown 语料无需安装 Docling；测试替身不代表真实编码效果。

## 6. 推荐的客服 Smoke Test

启动后可以按顺序测试：

```text
1. “Qwen 的 API Key 如何配置？”
   预期：customer-support + knowledge search

2. “DeepSeek 返回 429 时该如何处理？”
   预期：RoutingPolicy → knowledge Agent → 受控知识检索

3. “不用继续排查了，帮我转人工。”
   预期：customer-support + escalation + real handoffId
```

用户可以通过：

```text
GET /api/v1/support/handoffs
```

查看自己的人工交接；管理员可通过 `/api/v1/support/admin/handoffs` 处理工单。

## 7. 手动完整基础设施（高级）

根目录 `compose.yaml` 是当前推荐入口；下面的基础设施 Compose 只适合需要手动运行后端的场景。

以下配置复制仅适用于新环境。已有 `.env` 须保留并逐项调整，不直接覆盖；数据库升级前先备份。

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

## Docker 完整个人 Demo

根目录的 `compose.yaml` 启动 MySQL、Redis、MinIO、Elasticsearch、Kafka、Worker、一次性迁移、Demo 数据初始化、API、Billing MCP 和前端。所有后端依赖通过 Docker 服务名连接，并使用命名卷保存数据。

```bash
docker compose up --build
```

浏览器访问 `http://localhost:9527`；API 健康检查为 `http://localhost:8000/health`。首次启动会由 `demo-seed` 自动导入演示账单/API 数据和知识库。Billing MCP、MinIO、Elasticsearch、Kafka 只在 Docker 内部网络开放。服务边界和验收方式见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](../03-operations/DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md)。

本地 Demo 默认管理员为 `admin / admin123`；只适用于本机演示，部署到其他网络前必须通过环境变量修改管理员密码和 JWT Secret。

### 记忆与 Redis

Redis 不是会话记忆的持久化真源。当前 Docker Demo 已启用 Redis，用于近期历史、实体记忆的加速缓存，以及分布式限流和 WebSocket 连接协调；MySQL 仍持久化 `conversation_messages`（对话历史）和 `conversation_sessions.collected_entities_json`（跨轮实体记忆）。缓存丢失时自动回到 MySQL。

## 8. LLM / Embedding

Docker API 从 `backend/.env` 读取 LLM 配置。当前仓库只提供空的占位配置，不包含真实 Key；填写 `LLM_API_KEY` 后重启 API 容器即可生效：

```bash
docker compose up -d api
```

LLM 使用 OpenAI-compatible 接口：

```env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=...
LLM_MODEL=deepseek-chat
```

Embedding：

```env
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-替换为你的阿里云百炼Key
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
EMBEDDING_HTTP_PROXY=http://host.docker.internal:7897
```

项目已按 Qwen `text-embedding-v4` 配置。该模型默认返回 1024 维，但本项目当前 Elasticsearch 索引使用 256 维，因此代码会显式请求 256 维；不要删掉 `EMBEDDING_DIMENSION=256`。Qwen 文档说明 v4 支持 256 维输出，详见 [Embedding 兼容 OpenAI 接口](https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai)。

填写 Key 后，在项目根目录执行：

```bash
docker compose up -d --build api worker
docker compose run --rm demo-seed python scripts/seed_demo_knowledge.py --username admin --reindex
```

`--reindex` 会用 Qwen 为清单内 60 份官方文档重新生成向量；之后新的上传文档也会由 worker 使用同一套 Qwen 配置。Key 只写入本机 `backend/.env`，不要提交到 Git，也不要发到聊天中。

如果要使用 1024 维而不是当前的 256 维，需要先删除/重建 Elasticsearch 知识索引，再将 `EMBEDDING_DIMENSION=1024` 并完整重建所有文档；不能只改环境变量。

如果使用 Clash Verge，Docker 容器不能直接继承 Windows 的系统代理。请在 Clash 中切换到“规则”模式，并为 `dashscope.aliyuncs.com` 设置 `DIRECT`（中国区 Qwen 不要经过新加坡节点）；容器通过 `host.docker.internal:7897` 访问 Clash。本机 Clash 端口不是 7897 时，按实际 HTTP 端口修改 `EMBEDDING_HTTP_PROXY`。

如果遇到 Docker CLI、DNS、代理或 DashScope 连接失败，请先按 [网络、代理与 Provider 连通性排障](../03-operations/NETWORK_TROUBLESHOOTING.md) 检查，不要直接重复运行真实模型评测。

## 9. Billing MCP

只有 Billing Agent 使用 MCP，并且只读取套餐、用量和账单事实。个人 Demo 的目标是 Compose 内部 `billing-mcp` 服务；API 诊断与 Knowledge 使用本地受控 Tool。

```env
BILLING_MCP_ENABLED=true
BILLING_MCP_URL=http://billing-mcp:8011/mcp
BILLING_MCP_BEARER_TOKEN_ENV=BILLING_MCP_TOKEN
BILLING_MCP_TIMEOUT_SECONDS=30
```

Billing Agent 通过 MCP `list_tools` 动态获取远端 Tool 名和输入 Schema；`customer_id` 不会提供给 LLM，而是在 API 执行边界注入。Billing MCP 不映射宿主机端口，API 通过 Docker 内部服务名访问。Docker 编排与服务边界见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](../03-operations/DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md)。

具体安全要求见 [CUSTOMER_SERVICE_ARCHITECTURE.md](../02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md) 和 [PRODUCTION.md](../03-operations/PRODUCTION.md)。

## 10. 测试与客服 Benchmark

### 不需要 LLM API Key 的架构验证

这些测试使用固定模型输出或本地 Tool，不调用外部 LLM：

```bash
cd backend
# Agent、RoutingPolicy、Scheduler、Skill、Security、Fixture Eval
pytest -q tests/agent tests/architecture tests/skills tests/security tests/evaluation

# 解析、分块、存储与显式测试替身回归；不调用真实 Embedding
pytest -q tests/knowledge
python scripts/evaluate_skills.py
python scripts/evaluate_answers.py
python scripts/evaluate_customer_service.py
# 真实 RAG 评测另需 EMBEDDING_API_KEY，不能用空 Key 代替
python scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6
```

Docker 内 Billing MCP E2E：

```bash
# 回到包含 compose.yaml 的项目根目录
cd ..
docker compose --profile test run --build --rm test
```

它验证路由、Tool 权限、证据后转人工、真实本地 Billing MCP、MySQL 数据、WebSocket 完整事件流和失败降级。当前核心 Compose 回归为 11 项，已全部通过。

如需运行所有现有 pytest：

```bash
docker compose --profile test run --build --rm test pytest -q tests
```

当前 Docker 全量 pytest 已验证 **129 passed，1 个第三方弃用警告**，不需要 `LLM_API_KEY`，包含三 Agent 独立并发 E2E、前端 WebSocket 完整 E2E、质量门证据过滤和父子 RAG 指标回归。

### 需要 LLM API Key 的真实模型验证

填写 `backend/.env` 的 `LLM_API_KEY` 后，重启 API，再运行：

```bash
cd backend
python scripts/evaluate_customer_service.py --live --compare-no-skill --output eval/customer-service-live.json
```

这一步才验证真实 LLM 的 Tool 选择、Skill 效果和最终回答质量。

### 常规回归

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
python scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6
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
