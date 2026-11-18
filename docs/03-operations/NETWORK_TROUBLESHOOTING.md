# 网络、代理与 Provider 连通性排障

本文记录 PaiSmart 在 Windows、Docker、Clash/代理和外部 LLM/Embedding Provider 组合下的网络前置条件与排障方法。

## 1. 当前结论

2026-10-19 起，实际建库与检索仅使用远端千问 Embedding，本地哈希编码已移除：

| 模式 | 条件 | 行为 |
|---|---|---|
| 未配置 | `EMBEDDING_API_KEY` 为空 | 明确报错，不生成本地向量 |
| 远端 Provider | `EMBEDDING_API_KEY` 非空 | 访问 `EMBEDDING_BASE_URL/embeddings`，需要 DNS、代理和 Key 均可用 |

远端失败不会切换编码方式。切换模型或维度后重新建立索引，禁止新查询混用旧向量。历史报告中的本地哈希结果仅保留为历史工程记录，不能用作千问效果结论。

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

## 5. 离线验证与 Windows 直连

无外部网络时，只执行文件解析、分块及使用显式测试替身的单测；不能运行真实编码、建库或查询并声称效果通过。

```powershell
cd backend
python scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --validate-only
python -m pytest -q tests/knowledge
```

Windows 宿主机不能直接照搬容器专用的 `host.docker.internal` 代理地址。先检查 Provider 直连；可以直连时将宿主机配置的 `EMBEDDING_HTTP_PROXY` 留空，必须走本机代理时使用实际可达的主机地址与端口。容器配置按第 4 节单独设置。

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

## 7. 结果记录

每轮记录宿主机或容器、Provider 域名、代理方式、失败阶段和实际错误。离线替身测试证明的工程行为与真实 Provider 的连通结果分别记录。历史本地哈希编码已退出运行时，排障完成后通过受控的真实请求核对连接及用量。

[本地启动](../01-getting-started/GETTING_STARTED.md) · [Docker 操作](DOCKER_OPERATIONS.md) · [历史真实模型记录](../05-live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)
