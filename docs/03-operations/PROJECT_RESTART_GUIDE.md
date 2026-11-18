# PaiSmart 项目重启指南

本文用于在本机 Windows + Docker Desktop 环境中停止旧的 PaiSmart Demo 容器、重新构建当前工作区镜像并启动完整项目。默认项目目录为 `C:\\codes\\AI_DevSupport`。

> 适用范围：根目录 `compose.yaml` 对应的 Compose 项目 `paismart-demo`。本文不会停止无关 Docker 项目，也不会删除数据库、对象存储、检索或消息队列数据卷。

> 当前源码升级边界：第一阶段 RAG 改动已隔离验收，既有 Demo 尚未自动重建。已有部署升级先备份、停止旧 API/Worker 写入、执行迁移，再启动新代码，具体见 [RAG 操作手册](RAG_OPERATIONS.md)。现有镜像不含独立 Docling 环境；PDF/DOCX 还需准备解析解释器与固定模型缓存。

## 1. 服务与访问地址

完整 Demo 包含以下服务：

| 类型 | 服务 |
|---|---|
| 应用 | `api`、`frontend`、`worker`、`billing-mcp` |
| 基础设施 | `mysql`、`redis`、`elasticsearch`、`minio`、`kafka` |
| 一次性任务 | `migrate`、`demo-seed` |

启动成功后访问：

| 用途 | 地址 |
|---|---|
| 前端 | http://localhost:9527 |
| API 健康检查 | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |

## 2. 日常重启（不重新构建镜像）

仅服务临时异常、机器重启或需要重新加载容器状态时使用：

```powershell
cd C:\\codes\\AI_DevSupport
docker compose restart
docker compose ps
```

该方式复用现有镜像和数据卷，不重新安装依赖。启动恢复可能继续未完成的建库任务并产生 Embedding 请求；不要把重启视为无费用操作。

只重启单个服务的示例：

```powershell
docker compose restart api
docker compose restart frontend
docker compose restart worker
```

## 3. 代码改动后的标准更新

仅代码、依赖、Dockerfile 或前端代理变化且没有迁移时，可重新构建受影响服务。涉及第一阶段 schema 和索引写入逻辑的升级，先按上述操作手册隔离旧写入者并完成迁移，不直接执行滚动替换：

```powershell
cd C:\\codes\\AI_DevSupport
docker compose up --build -d api worker billing-mcp frontend
docker compose ps
```

如果修改了基础镜像、依赖锁定文件或希望确保不使用 BuildKit 缓存，使用第 4 节的完整更新流程。

## 4. 完整替换旧容器和镜像

当需要“停止所有旧项目容器，并全部改成当前工作区最新版本”时，按以下顺序执行：

```powershell
cd C:\\codes\\AI_DevSupport

# 1. 停止并移除当前 Compose 项目的容器和网络；不删除命名卷
docker compose down --remove-orphans

# 2. 用当前工作区无缓存重建应用镜像
docker compose build --no-cache

# 3. 强制创建最新容器
docker compose up -d --force-recreate

# 4. 测试镜像也同步重建（不启动测试服务）
docker compose --profile test build --no-cache test

# 5. 查看最终状态
docker compose ps -a
```

说明：

- `down --remove-orphans` 只针对当前 Compose 项目，不会动其他项目容器。
- `--no-cache` 确保 Python 依赖、前端构建产物和项目代码都从当前状态生成。
- `--force-recreate` 确保即使 Compose 判断配置未变化，也重新创建容器。
- `migrate` 和 `demo-seed` 是一次性任务，成功后显示 `Exited (0)` 属于正常状态。
- 测试镜像只构建、不常驻运行，避免后台留下测试进程。

## 5. 启动后的健康检查

先查看 Compose 状态：

```powershell
docker compose ps
```

预期结果：

- `api` 显示 `healthy`。
- `mysql`、`redis`、`elasticsearch`、`minio`、`kafka` 显示 `healthy`。
- `frontend`、`worker`、`billing-mcp` 处于 `Up`。
- `migrate`、`demo-seed` 显示 `Exited (0)`。

再执行 HTTP 和 Nginx 检查：

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-WebRequest http://localhost:9527/ -UseBasicParsing
docker compose exec -T frontend nginx -t
```

API 应返回类似以下内容，前端状态码应为 `200`，Nginx 应报告 syntax is ok：

```json
{"status":"ok","service":"PaiSmart Python"}
```

如果刚启动时前端短暂返回 `502`，先等待 API 变为 `healthy`；API 依赖完成后再重试，不要立即反复重建容器。

## 6. 日志与故障定位

```powershell
# 查看全部服务最近日志
docker compose logs --tail 200

# 按启动依赖顺序检查
docker compose logs --tail 200 mysql elasticsearch kafka migrate demo-seed api frontend

# 持续观察单个服务；Ctrl+C 只退出日志查看
docker compose logs -f api
```

常见判断：

| 现象 | 检查方向 |
|---|---|
| `api` 未健康 | 先看 `migrate`、MySQL、Elasticsearch、Kafka 日志 |
| 页面 502 | 确认 `api` 已 healthy，再检查 `frontend` 日志 |
| 知识库无结果 | 确认 `demo-seed` 成功、`worker` 运行、Elasticsearch 健康 |
| 账单工具失败 | 检查 `billing-mcp`；API 通过 Compose 服务名访问它，不使用宿主机 `localhost:8011` |
| 容器反复退出 | 找到日志中的第一条错误，不要直接删除数据卷 |

## 7. 停止项目与数据安全

只停止并移除容器、保留数据：

```powershell
docker compose down
```

再次启动并复用原数据：

```powershell
docker compose up -d
```

以下命令会永久删除本项目的命名卷，清空数据库、Elasticsearch 索引、MinIO 对象、Redis 缓存和 Kafka 数据，仅在明确需要“从零初始化”时使用：

```powershell
docker compose down -v
docker compose up --build -d
```

日常重启和完整镜像更新都不需要 `down -v`。

## 8. Windows Docker CLI 不在 PATH 时

如果 PowerShell 提示找不到 `docker`，可在当前窗口临时补充 Docker Desktop CLI 路径：

```powershell
$env:Path += ";$env:LOCALAPPDATA\\Programs\\DockerDesktop\\resources\\bin"
docker compose ps
```

## 9. 重启边界

重启、重建和健康检查本身不会调用 DeepSeek、Qwen 或其他 LLM/Embedding 接口，因此不会消耗 Token。只有登录后发送聊天问题、重新编码知识库或执行真实评测时，才会产生相应模型消耗。

