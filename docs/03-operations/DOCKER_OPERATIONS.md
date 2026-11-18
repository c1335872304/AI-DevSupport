# Docker 操作手册

本文面向 PaiSmart 的本机 Docker Demo。根目录的 `compose.yaml` 是唯一的完整应用入口；它会启动前端、API、Billing MCP、Worker 以及 MySQL、Redis、MinIO、Elasticsearch、Kafka，并在首次启动时执行迁移和演示数据初始化。

> 这套编排固定为 `APP_ENV=dev`，默认凭据和端口仅适用于受信任的本机演示，不能直接作为生产部署配置。

> 升级已有 Demo 前先阅读 [RAG 迁移与恢复](RAG_OPERATIONS.md)：备份、隔离旧 API/Worker、迁移后再部署。2026-10-20 本机 Demo 已更新四阶段源码与独立 CPU Docling 环境，迁移及验收证据见 [升级报告](../04-testing/DOCKER_DEMO_UPGRADE_2026-10-20.md)。初始化会保留已有知识库，只有空库才导入官方资料并产生编码调用。

## 1. 前置条件

在项目根目录执行以下命令：

```powershell
docker version
docker compose version
docker compose config --quiet
```

前两条确认 Docker Engine 与 Compose 可用；最后一条只校验 Compose 配置，不创建容器。首次构建会拉取基础镜像，并需要足够的 CPU、内存和磁盘空间；Elasticsearch 与 Kafka 是资源占用最大的两个服务。

如果新开的 Windows PowerShell 显示“找不到 `docker`”，Docker Desktop 的 CLI 通常位于 `$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin`；可先为当前窗口补充路径：

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
docker compose ps
```

该设置只影响当前 PowerShell 窗口；也可以将 Docker Desktop CLI 目录加入用户级 `PATH` 后重新打开终端。

如需使用真实 LLM 或 Embedding，在启动前仅编辑本机的 `backend/.env`，填写相应 API Key。该文件已被 Git 忽略，切勿把密钥放入 `compose.yaml` 或提交到仓库。

PDF/DOCX 解析模型须事先准备在 `backend/data/models/docling`；API、Worker 以只读目录挂载，解释器位于镜像 `/opt/docling/bin/python`。此挂载保留固定模型缓存，构建不下载模型的 main 分支。宿主机代理从容器访问时需使用 `host.docker.internal`；Compose 默认保留当前 `7897` 代理，可设置 `DOCKER_EMBEDDING_HTTP_PROXY` 覆盖，显式空字符串表示直连。

网络、代理、Docker CLI 和远端 Provider 的专项检查见 [NETWORK_TROUBLESHOOTING.md](NETWORK_TROUBLESHOOTING.md)。

## 2. 启动完整 Demo

```powershell
docker compose up --build -d
docker compose ps
```

`--build` 会构建本地后端和前端镜像；`-d` 让服务在后台运行。第一次启动会依次等待基础设施健康、执行 `migrate`、运行 `demo-seed`，随后启动 API、Worker、Billing MCP 与前端。

访问入口：

| 用途 | 地址 |
| --- | --- |
| 前端 | http://localhost:9527 |
| API 健康检查 | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |
| WebSocket | `ws://localhost:8000/chat` |

经前端 Nginx 访问时，API 前缀为 `/api/v1`，WebSocket 为 `ws://localhost:9527/proxy-ws/chat`。

本机 Demo 管理员为 `admin / admin123`。仅用于本机演示；任何可被他人访问的部署都必须替换 JWT Secret 与管理员密码，并使用生产环境编排。

## 3. 观察启动状态与排障

```powershell
# 追踪全部服务日志；Ctrl+C 只停止查看日志，不停止容器
docker compose logs -f

# 只观察最常需要关注的服务
docker compose logs -f mysql migrate demo-seed api billing-mcp worker frontend

# 查看单个服务最近 200 行日志
docker compose logs --tail 200 api

# 查看容器、健康状态与端口映射
docker compose ps
```

成功条件是 `migrate` 和 `demo-seed` 显示为已完成（退出码 0），长期服务处于 `running` 或 `healthy`。若 API 未启动，优先查看 `migrate`、`demo-seed`、`elasticsearch`、`kafka` 的日志，因为 API 会等待这些依赖完成或健康。

旧 ES 向量可能缺少新版检索必需的模型名和维度。升级后若列表有文档但检索为空，先执行下列只读预检；只有数据库活动版本、ES文档身份、正文和真实向量逐条一致，才允许补齐缺失字段。此操作不编码、不改正文/向量/权限，也不改数据库；已有字段冲突或并发版本变化会停止。

```powershell
docker compose exec api python scripts/repair_legacy_embedding_metadata.py
# 预检匹配后才执行
docker compose exec api python scripts/repair_legacy_embedding_metadata.py --apply
```

常见问题：

| 现象 | 优先检查 |
| --- | --- |
| 9527 或 8000 无法访问 | `docker compose ps`，然后查看 `frontend` 或 `api` 日志；确认宿主端口未被占用。 |
| `demo-seed` 失败 | 查看 `mysql`、`minio`、`elasticsearch` 日志；不要只重启 API。 |
| 知识库无检索结果 | 先确认 `worker` 正常运行，再检查 `demo-seed` 是否完成及 Elasticsearch 健康状态。 |
| 账单查询无法核实 | 查看 `billing-mcp` 日志；它只能由 API 经内部地址 `http://billing-mcp:8011/mcp` 调用。 |
| 容器频繁退出 | 用 `docker compose logs --tail 200 <服务名>` 找到第一条错误；避免直接删除数据卷。 |

## 4. 功能验收

启动稳定后，可先验证基础服务：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

然后登录前端并依次提出以下问题：

1. `你们的退款政策是什么？`：应走 Knowledge 检索。
2. `请求 req_demo_401 返回 401，帮我定位原因。`：应走 API 诊断与知识上下文。
3. `为什么 2026-08 的账单比套餐基础价高？`：应通过 Billing MCP 核实账单事实。
4. `不用继续排查了，帮我转人工。`：应在证据汇总后创建人工交接。

Billing MCP 不映射宿主机端口；不要尝试用 `localhost:8011` 调用它。这是刻意的网络边界，API 容器使用 Compose 服务名访问它。

## 5. 常用维护操作

从待发布源码的根目录执行。当前独立 Git 克隆位置见[Git 操作记录](GIT_AND_FAST_CI.md)。已有部署涉及结构变化时先备份并执行迁移，`alembic upgrade head` 应与待部署源码一致。Worker 或后台恢复未完成的入库任务时，可继续产生 Embedding 请求。

```powershell
# 重启一个长期服务，例如 API
docker compose restart api

# 代码或 Dockerfile 改动后，只重建并替换 API
docker compose up --build -d api

# 前端代理配置或页面改动后，同时替换 API 与前端
docker compose up --build -d api frontend

# 同时重建 API 与 Worker（适合后端、索引或任务处理改动）
docker compose up --build -d api worker

# 进入 API 容器排查；镜像为 slim，优先使用 Python 命令而不是假设有 bash
docker compose exec api sh

# 在 API 容器内执行一个只读健康探针
docker compose exec api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/health').read().decode())"
```

若为已有知识文档配置或更换了 Embedding 模型/维度，必须按 [本地启动说明](../01-getting-started/GETTING_STARTED.md) 的要求重新建立 Elasticsearch 索引并执行 Demo 知识库重建；不能只重启 API。

### API 重建后的前端代理检查

前端使用 Docker 内置 DNS 动态解析 `api` 服务名。API 刚重建且仍处于 `health: starting` 时，请求可能短暂返回 502；等待 API 变为 `healthy` 并超过约 10 秒的 DNS 缓存窗口后，无需重启 frontend。可用一个需要登录的接口确认代理已恢复（401 是未登录时的预期结果，不是 502）：

```powershell
docker compose up -d --force-recreate --no-deps api
docker compose ps api frontend
Invoke-WebRequest http://localhost:9527/api/v1/users/me
```

如果 API 已健康但持续返回 502，再查看 `docker compose logs --tail 100 frontend api`；重启 frontend 仅是旧镜像或紧急情况下的恢复手段。

## 6. Docker 内回归测试

以下命令使用 `test` profile 构建测试镜像，并在同一 Compose 网络中验证 Agent、Billing MCP 与 WebSocket 主链路：

```powershell
# 核心 Compose 回归
docker compose --profile test run --build --rm test

# 全量测试使用隔离 SQLite，避免测试夹具触碰 Demo 业务数据
docker compose run --rm --no-deps -e DATABASE_URL=sqlite+aiosqlite:////tmp/docker-tests.sqlite -e DATABASE_AUTO_CREATE_DEV=true -e REDIS_ENABLED=false -e BILLING_MCP_COMPOSE_E2E=false -e BILLING_MCP_ENABLED=false -e TASK_MODE=background -e STORAGE_BACKEND=local -e SEARCH_BACKEND=database -e LOCAL_STORAGE_DIR=/tmp/test-storage -e LLM_API_KEY= -e EMBEDDING_API_KEY= --entrypoint pytest test tests -q
```

`--rm` 只删除本次测试容器，不删除数据库、索引或其他命名卷。运行测试前建议确认没有同名的临时 Compose 项目在占用端口或卷。

## 7. 停止、保留数据与彻底重置

```powershell
# 停止并移除容器和网络；保留 MySQL、Redis、MinIO、Elasticsearch、Kafka 的命名卷
docker compose down

# 再次启动并复用保留的数据
docker compose up -d
```

下面的命令会删除所有命名卷，进而永久清空演示数据库、对象、检索索引、缓存和 Kafka 数据。只有确实需要从零开始时才执行：

```powershell
docker compose down -v
docker compose up --build -d
```

重置后 `migrate` 和 `demo-seed` 会再次创建 schema 并写入演示数据。生产数据绝不能用 `down -v` 清理；应遵循备份、迁移和保留策略。

## 8. 仅启动基础设施（高级）

`deploy/compose.infra.yml` 只适用于在宿主机直接运行后端时需要的依赖，不包含 API、前端、Worker 或 Billing MCP：

```powershell
docker compose -f deploy/compose.infra.yml up -d
docker compose -f deploy/compose.infra.yml ps
```

此模式把 MySQL、Redis、MinIO、Elasticsearch、Kafka 映射到宿主机端口，适合后端调试；不要与根目录完整 Demo 混用，以免端口和数据卷冲突。停止时也必须指定同一份文件：

```powershell
docker compose -f deploy/compose.infra.yml down
```

服务拓扑、MCP 边界和详细验收背景见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md)。
