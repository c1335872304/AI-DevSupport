# 网络、代理与 Provider 连通性排障

本文记录 PaiSmart 在 Windows、Docker、Clash/代理和外部 LLM/Embedding Provider 组合下的网络前置条件与排障方法。

## 1. 当前结论

项目已经支持两种 Embedding 模式：

| 模式 | 条件 | 行为 |
|---|---|---|
| 本地离线 | `EMBEDDING_API_KEY` 为空 | 使用确定性的 `local-hash-v1`，不访问 DashScope |
| 远端 Provider | `EMBEDDING_API_KEY` 非空 | 访问 `EMBEDDING_BASE_URL/embeddings`，需要 DNS、代理和 Key 均可用 |

不要把“远端请求失败”自动降级为本地向量。两种向量空间可能不同，静默切换会造成索引和查询向量不一致。因此切换模式后应重新建立 Demo 知识库或完整重建索引。

## 2. Docker CLI 检查

在项目根目录执行：

```powershell
Get-Command docker -ErrorAction SilentlyContinue
docker version
docker compose version
docker compose config --quiet
```

如果 PowerShell 显示找不到 `docker`：

1. 安装并启动 Docker Desktop；
2. 关闭并重新打开 PowerShell；
3. 如果 Docker Desktop 已安装但 CLI 不在 `PATH`，临时执行：

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
docker compose version
```

当前仓库只能提供检测和启动说明，不能替代 Docker Desktop 安装、Windows 服务启动或管理员权限配置。

## 3. Windows 宿主机网络检查

检查 DashScope DNS 和 HTTPS：

```powershell
Resolve-DnsName dashscope.aliyuncs.com
Test-NetConnection dashscope.aliyuncs.com -Port 443
```

如果使用 Clash，检查本机 HTTP 代理端口。下面以 `7897` 为例：

```powershell
Test-NetConnection 127.0.0.1 -Port 7897
```

如果上述检查失败，优先处理 DNS、Clash 是否运行、端口是否正确和防火墙规则，不要反复执行 Live 评测。

## 4. Docker 容器访问外部 Provider

Docker 容器不能自动继承 Windows 系统代理。使用 Clash 时：

1. Clash 选择“规则”模式；
2. 为 `dashscope.aliyuncs.com` 配置 `DIRECT` 或可用的稳定线路；
3. 确认 Clash HTTP 端口；
4. 在 `backend/.env` 设置：

```env
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
EMBEDDING_HTTP_PROXY=http://host.docker.internal:7897
```

端口不是 `7897` 时必须替换为实际端口。不要把 `localhost:7897` 写给容器使用；容器内的 `localhost` 指向容器自身。

Docker 服务重建后，可以从 API 容器检查解析和 HTTPS：

```powershell
docker compose run --rm --no-deps api python -c "import socket; print(socket.gethostbyname('dashscope.aliyuncs.com'))"
```

如果配置了显式代理，再检查容器到宿主机代理端口是否可达：

```powershell
docker compose run --rm --no-deps api python -c "import socket; s=socket.create_connection(('host.docker.internal',7897),5); print('proxy reachable'); s.close()"
```

## 5. 本地离线测试模式

没有 Docker 或外部 Embedding 网络时，可以显式使用本地向量。下面的环境变量只影响当前 PowerShell 窗口，不修改 `.env`：

```powershell
$env:EMBEDDING_API_KEY = ""
$env:SEARCH_BACKEND = "database"
```

然后重建 Demo 知识库并执行检索评测：

```powershell
cd backend
python scripts/seed_demo_knowledge.py --username admin --reset
python scripts/evaluate_rag.py eval/demo_knowledge_rag.jsonl --username admin -k 6
```

输出中应看到：

```text
embedding: local-hash-v1
```

如果当前 `.env` 中存在非空 `EMBEDDING_API_KEY`，程序会按远端模式运行，不会自动使用本地 fallback。

## 6. 真实 Provider 测试顺序

真实模型测试必须遵循以下顺序：

```text
Docker CLI / 服务检查
  → DNS / 代理检查
  → 管理后台 Provider 连接测试
  → 单条受控请求
  → 核对余额与 Trace
  → 再决定是否扩大样本
```

任何网络失败都不应自动重试整批请求。DeepSeek、Qwen 和 Docker 网络问题分别记录，不能把 Provider 失败误判成 Agent 或 RAG 质量失败。

## 7. 本轮实际问题记录

2026-09-09 的本机复验中：

- `docker`、`docker compose` 不在当前 PATH，无法运行 Compose 集成测试；
- `.env` 中 Embedding Key 非空，因此评测尝试访问远端 Qwen；
- 当前环境无法解析或连接 DashScope，远端 RAG 评测失败；
- 临时清空 `EMBEDDING_API_KEY` 后，本地 hash embedding 建库和 14 条 RAG 评测全部通过；
- 这说明本地 RAG 代码可用，剩余问题是 Docker 安装/启动和外部 Provider 网络配置。

相关说明：[本地启动](../01-getting-started/GETTING_STARTED.md)、[Docker 操作](DOCKER_OPERATIONS.md)、[DeepSeek 真实测试方案](../05-live-tests/DEEPSEEK_LIVE_TEST_PLAN.md)。
