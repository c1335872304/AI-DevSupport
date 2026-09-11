# Docker 与本地 Billing MCP

本文是 PaiSmart 个人 Demo 的当前容器化实现说明。Billing MCP 是本项目内的独立 Docker 服务，不依赖第三方计费系统；它只读取同一套 Demo 数据库中的套餐、用量和账单事实。

## 1. 目标

在一条 `docker compose` 命令下启动可访问的 Linux 容器环境。宿主机浏览器访问前端/API；容器间只通过 Docker 内部网络通信。

```text
Browser on host
  -> frontend (host port 9527)
  -> api (host port 8000)
       -> billing-mcp (internal port 8011 only)
       -> mysql (internal port 3306 only)
       -> redis / minio / elasticsearch / kafka (internal only)

api / worker / demo-seed
  -> redis, minio, elasticsearch, kafka (internal only)
```

Billing 请求的唯一链路：

```text
Billing Agent
  -> Billing MCP Tool Discovery
  -> list_tools
  -> http://billing-mcp:8011/mcp
  -> discovered read-only billing Tool schemas
  -> Billing Agent selects a discovered Tool
  -> call_tool
  -> MySQL support_* billing tables
```

`RoutingPolicy`、三个专业 Agent、Shared Scheduler、证据汇总和转人工顺序不因容器化而改变。

## 2. MCP Tool 发现与路由边界

Billing MCP 采用标准 MCP 的 Tool Discovery，而不是在 API 代码中硬编码远端 Tool 名和参数 Schema：

```text
RoutingPolicy --deterministically selects--> billing Agent
  -> MCP client connects to the fixed billing-mcp service
  -> list_tools
  -> validates the discovered catalog
  -> passes the valid Tool name / description / JSON Schema to billing Agent
  -> Agent selects and calls one of those discovered Tools
```

这里“LLM 发现 Tool”的准确含义是：MCP 客户端负责协议层的 `list_tools` 通信，随后将服务端实时返回的 Tool 描述和 JSON Schema 提供给 Billing Agent 的 LLM。LLM 不需要知道 Docker 地址，也不应自行连接任意 MCP Server。

这不会破坏“路由不能错”的要求：

- `RoutingPolicy` 仍只决定是否启动 `billing` Agent，LLM 不能新增或替换 Agent。
- 发现只会连接固定 Compose 服务名 `billing-mcp`，不会扫描网络或连接用户指定地址。
- `billing-mcp` 只能发布只读 Billing Tool；客户端拒绝非只读、缺少 Schema、重复名称或不符合 Billing 域声明的 Tool。
- 发现失败、目录为空或 Schema 不合法时，不向 LLM 提供 Tool，记录为账务事实无法核验，再由证据/转人工链路处理。

个人 Demo 初始 MCP Server 只发布 `get_plan`、`get_usage`、`get_invoice`。后续在该 Server 新增符合只读 Billing 约束的 Tool 时，Agent 不需要修改硬编码 Tool Schema 即可发现和使用它。

## 3. 当前实现状态

| 项目项 | 当前状态 | 实现说明 |
| --- | --- | --- |
| 后端镜像 | 使用 `backend/Dockerfile` | 非 root 运行并提供 API 健康检查。 |
| 基础设施 | 提供 `deploy/compose.infra.yml` | 作为可选完整依赖，不直接承担应用编排。 |
| API 容器 | `compose.yaml` 已提供 API、迁移、数据库、Redis、对象存储、搜索、Kafka、Demo seed 和 Billing MCP | 当前完整个人 Demo 主链路。 |
| Worker 容器 | 已接入独立 Kafka Worker 服务 | 处理上传后的文档索引、重试和 DLQ。 |
| 前端容器 | 多阶段前端 Dockerfile、Nginx 代理和 Compose 服务 | 宿主机 `9527` 访问。 |
| Billing MCP Client | 支持 MCP `list_tools`、目录校验和动态 Tool 注册 | 已在运行中的 API 容器内完成真实目录发现。 |
| Billing MCP Server | `billing_mcp_server.py` 只暴露三条账单 Tool | 已通过真实 HTTP MCP 边界发现并调用 `get_plan`。 |
| 现有 `mcp_server.py` | 只暴露知识库 Tool | 不复用为 Billing MCP，避免额外 Tool 暴露。 |

## 4. 服务边界

| 服务 | 进程 | 对宿主机开放 | 职责 |
| --- | --- | --- | --- |
| `api` | FastAPI / WebSocket | `8000` | 客服 Agent、路由、Tool Runtime、最终答复。 |
| `billing-mcp` | Streamable HTTP MCP | 不开放，仅 `expose: 8011` | 只读套餐、用量、账单查询。 |
| `mysql` | MySQL | 开发模式可选 `3306` | Demo 业务数据、会话、工单和账单表。 |
| `worker` | Kafka consumer | 不开放 | 异步文档处理；仅 Kafka 模式启用。 |
| `frontend` | 静态 Web/Nginx | `9527` | 浏览器入口。 |
| `demo-seed` | 一次性初始化脚本 | 不开放 | 创建演示账单/API 数据并索引 9 份 Demo 知识文档。 |
| `redis` | Redis 7.4 | 不开放，仅内部访问 | 路由/记忆缓存、限流和 WebSocket 协调。 |
| `minio` | MinIO | 不开放，仅内部访问 | 上传对象持久化。 |
| `elasticsearch` | Elasticsearch 8.17 | 不开放，仅内部访问 | 混合向量/关键词 RAG 检索。 |
| `kafka` | Kafka 3.9 KRaft | 不开放，仅内部访问 | 文档异步处理队列、重试和 DLQ。 |

当前完整个人 Demo 使用这些镜像：`mysql:8.4`、`redis:7.4-alpine`、`minio/minio:latest`、`docker.elastic.co/elasticsearch/elasticsearch:8.17.0`、`apache/kafka:3.9.2`、本地构建的 `paismart-backend:dev` 和 `paismart-frontend:dev`。`migrate`、`demo-seed`、`api`、`billing-mcp` 和 `worker` 复用后端镜像；测试 profile 额外构建 `paismart-backend-test:dev`。

禁止把 `billing-mcp` 映射为宿主机端口；API 必须使用服务发现地址 `http://billing-mcp:8011/mcp`，不能使用 `localhost`。

## 5. 本地 Demo 的 MCP 配置

`api` 和 `billing-mcp` 使用同一个 Docker 网络以及同一个 MySQL 数据源。Billing MCP 只接受 API 注入的 `customer_id`，并使用它读取对应的 Demo 账单记录。

API 容器的环境变量：

```env
DATABASE_URL=mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
BILLING_MCP_ENABLED=true
BILLING_MCP_URL=http://billing-mcp:8011/mcp
BILLING_MCP_TIMEOUT_SECONDS=10
# Demo 内部网络默认不发送 bearer；变量名仍保留，以便日后升级鉴权。
BILLING_MCP_BEARER_TOKEN_ENV=BILLING_MCP_TOKEN
```

Billing MCP 容器的环境变量：

```env
DATABASE_URL=mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
```

个人 Demo 的安全边界是 Docker 内部网络加“不映射 Billing MCP 端口”。这不等同于生产认证：如果未来对宿主机或其他网络开放 `billing-mcp`，必须加入服务间 bearer/mTLS 验证，并由 MCP Server 验证调用方身份。

## 6. 当前 Compose 轮廓

```yaml
services:
  mysql:
    image: mysql:8.4

  redis:
    image: redis:7.4-alpine

  minio:
    image: minio/minio:latest

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0

  kafka:
    image: apache/kafka:3.9.2

  worker:
    image: paismart-backend:dev
    command: ["python", "-m", "app.workers.file_processor"]

  demo-seed:
    image: paismart-backend:dev
    command:
      - sh
      - -c
      - >-
        python -c "import asyncio; from app.db.init_db import init_db; asyncio.run(init_db())"
        && python scripts/seed_support_demo.py --username admin
        && python scripts/seed_demo_knowledge.py --username admin

  api:
    image: paismart-backend:dev
    environment:
      DATABASE_URL: mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
      REDIS_URL: redis://redis:6379/0
      STORAGE_BACKEND: minio
      MINIO_ENDPOINT: minio:9000
      SEARCH_BACKEND: elasticsearch
      ELASTICSEARCH_URL: http://elasticsearch:9200
      TASK_MODE: kafka
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      BILLING_MCP_ENABLED: "true"
      BILLING_MCP_URL: http://billing-mcp:8011/mcp
    ports: ["8000:8000"]
    depends_on:
      mysql:
        condition: service_healthy
      billing-mcp:
        condition: service_started

  billing-mcp:
    image: paismart-backend:dev
    command: ["python", "billing_mcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8011"]
    environment:
      DATABASE_URL: mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
    expose: ["8011"]
    depends_on:
      mysql:
        condition: service_healthy

  frontend:
    image: paismart-frontend:dev
    ports: ["9527:80"]
```

最终文件使用 Compose `env_file` 或 Docker secrets 传递密钥；示例不写入真实 LLM Key 或 JWT Secret。

## 7. 当前实现组成

### 容器基础

1. 根级 `compose.yaml` 是当前入口；`compose.infra.yml` 仅作为手动基础设施来源。
2. MySQL、Redis、MinIO、Elasticsearch 和 Kafka 使用健康检查及命名数据卷。
3. API、Worker、RAG、对象存储和队列地址统一使用 Compose 服务名。
4. 后端和前端均有 `.dockerignore`；后端镜像使用非 root 用户，迁移和 Demo 数据初始化由一次性服务执行。

验收：`docker compose up --build` 后，宿主机可访问 API 健康检查；重启容器后 MySQL 数据仍存在。

### 独立 Billing MCP

1. `billing_mcp_server.py` 提供独立 MCP Server。
2. Server 只注册 `get_plan(customer_id)`、`get_usage(customer_id, month?)`、`get_invoice(customer_id, month?)`。
3. 每个 Tool 提供名称、描述和输入 Schema，并调用只读 billing domain service。
4. Billing Agent 被路由选中后，API Client 执行 `list_tools`，校验目录并把实时 Schema 提供给 Agent。
5. Shared Scheduler 使用发现到的 Tool 名和 Schema 执行 `call_tool`，不维护远端 Tool 的硬编码 Schema。
6. 知识库 `mcp_server.py` 不复用为 Billing MCP，Server 不注册退款、套餐变更、工单或知识库 Tool。
7. Compose 启动 `billing-mcp`，API 通过 `http://billing-mcp:8011/mcp` 调用它。

验收：Billing Agent 只能看到 `list_tools` 实际发现且校验通过的 Billing Tool；MCP 初始目录恰好列出三个远端 Tool；一个用户不能从另一个用户的 `customer_id` 读取账单（Demo 阶段通过 API 注入约束和测试覆盖）。

### 端到端验证

1. 独立 `test` Compose service 使用 Dockerfile 的 `test` target 安装 `requirements-dev.txt`，运行 Agent/MCP 回归。
2. Billing MCP → MySQL 的 Compose E2E 覆盖真实 `list_tools`、套餐、用量和账单查询，测试数据结束后清理。
3. 回归覆盖 Billing 高风险请求：先读事实，再形成证据，再创建人工工单。
4. 回归验证 `billing-mcp` 不暴露宿主机端口，API 容器不使用 `localhost:8011` 访问它。

架构 E2E 覆盖两个完整链路：

- 三个专业 Agent 同时命中时的并发调度、独立上下文和每个 Agent 的 Tool 所有权。
- 前端 WebSocket 从请求进入、Tool 事件、证据摘要、人工决策到最终回答的完整闭环。

这两类测试使用固定模型输出即可，不需要 `LLM_API_KEY`；真实 LLM 行为由独立的 `--live` 评测负责。

先执行已接入的 Agent/MCP/WebSocket 回归（当前 11 项核心用例）：

```bash
docker compose --profile test run --build --rm test
```

在同一 Compose 测试环境中运行所有现有 pytest：

```bash
docker compose --profile test run --build --rm test pytest -q tests
```

验收重点：MCP 不可用时客服答复诚实降级，并按证据规则转人工。

### 完整 Demo 服务

1. 前端使用多阶段 Dockerfile、Nginx API/WebSocket 代理与 `frontend` 服务。
2. `TASK_MODE=kafka` 使用独立 `worker` 服务，支持文档重试和 DLQ。
3. MinIO 和 Elasticsearch 为上传存储与父子切分 RAG 提供完整后端。
4. `demo-seed` 一次性服务自动初始化管理员关联的 Billing/API 演示数据并索引内置知识库。

验收：当前个人 Demo 启动 `mysql + redis + minio + elasticsearch + kafka + worker + migrate + demo-seed + api + billing-mcp + frontend`。

## 8. 不做事项

- 不把三个专业 Agent 拆成三个 Docker 服务；它们是同一 API 进程中的并发 LLM 规划单元。
- 不把 API 诊断、Knowledge、工单或退款能力接入 Billing MCP。
- 不让 Billing MCP 直接产生客服答复、决定路由或创建人工工单。
- 不把全部 API、Worker、MCP Server 塞进一个容器。
- 不把 LLM Key、JWT Secret 或未来 MCP 凭据提交到仓库。

## 9. 当前验收结果

当前实现满足以下条件：

1. 通过一条 Compose 命令启动完整个人 Demo；浏览器可访问前端，API 和内部依赖健康运行。
2. Billing Agent 在每次独立工作前，或在有缓存失效时，通过 MCP `list_tools` 获得可调用 Tool 目录；不是读取本地硬编码远端 Schema。
3. Billing Agent 已实际跨容器调用本地 Billing MCP，而非回退本地 Tool 实现；MCP 初始目录恰好为三个只读账单 Tool。
4. Agent 运行图、独立 Agent 取证、证据后转人工和最终答复顺序保持不变。
5. Compose 内 E2E 测试服务与现有 Agent/MCP/WebSocket 回归入口已配置；当前核心 11 项已通过，包含三 Agent 并发和前端 WebSocket 完整链路。

全量 pytest 已在无 `LLM_API_KEY` 环境通过 **114 项**，包含三 Agent 独立并发 E2E、前端 WebSocket 完整 E2E 和父子 RAG 指标回归。
