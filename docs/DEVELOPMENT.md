# 开发

建议与 CI 对齐使用 Python 3.12、Node 20 和 pnpm 9.15.5，后端声明支持 Python 3.11 及以上。完整容器运行见[运维](OPERATIONS.md)，验证命令见[测试](TESTING.md)。

## 仓库与配置

日常变更在 Git 检出中完成。本机已有克隆为 `C:\codes\AI-DevSupport-publish`，原工作目录为 `C:\codes\AI_DevSupport`。现有交付分支为 `codex/support-demo-rag-ci`，对应 [PR #1](https://github.com/c1335872304/AI-DevSupport/pull/1)。

首次从 `backend/.env.example` 创建本机 `backend/.env`，已有配置逐项调整。Provider 密钥放在部署秘密或本机环境文件中。前端配置参考 `frontend/.env.example`。配置模板、锁文件和 [Compose](../compose.yaml)共同说明可用选项。

## 后端

从仓库根目录创建环境。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m alembic upgrade head
python run.py
```

Linux / macOS 使用 `source .venv/bin/activate` 激活环境，首次复制配置使用 `cp -n .env.example .env`。迁移前核对目标数据库，已有数据按[发布流程](RELEASING.md)备份。

| 入口 | 地址 |
| --- | --- |
| 健康检查 | `http://localhost:8000/health` |
| Swagger | `http://localhost:8000/docs` |
| WebSocket | `ws://localhost:8000/chat` |

最小开发模式使用 SQLite、本地存储、后台任务及数据库检索。真实建库和查询需要有效的千问 Embedding Key。仅做离线开发验证时使用[测试手册](TESTING.md)中的替身和隔离演示。

## 前端

在另一个终端从仓库根目录启动。

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

前端 REST 使用 `/api/v1`，聊天通过 `/proxy-ws/chat` 代理到后端 `/chat`。Vite 与 Nginx 的目标应对应实际后端地址。宿主机运行使用可达的本机地址，Compose 内使用服务名。

## 模型与解析

后端常用配置如下，实际 Key 由本机或部署环境提供。

```dotenv
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=<model-key>
LLM_MODEL=<provider-model>
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=<embedding-key>
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
```

模型名称以部署选定的供应商配置为准。索引和查询的 Embedding 模型及维度必须一致。更换模型、维度或切分配置后的构建与恢复见[知识库运维](OPERATIONS.md#knowledge)。PDF/DOCX 的独立解释器与模型缓存见[Docling](OPERATIONS.md#docling)。

<a id="git"></a>

## Git 与 PR

开始工作先确认目录、分支和已有改动。

```powershell
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log -5 --oneline
gh auth status --hostname github.com
```

本地缺少 `.git` 时先定位已有克隆。克隆或提交使用项目现有的远端配置，读取权限可用 `git ls-remote --symref <remote> HEAD` 核对。GitHub CLI 设备授权使用终端新生成的一次性代码。

按审过的路径暂存，检查差异后提交和推送。

```powershell
git add -- <reviewed-paths>
git diff --cached --check
git diff --cached
git commit -m "Describe the change"
git push -u origin <branch>
gh pr checks 1 --repo c1335872304/AI-DevSupport --watch
```

多行 PR 说明写入临时文件，通过 `gh pr edit --body-file <file>` 提交。推送后按提交 SHA 核对两轮 Fast CI 和隔离集成，具体覆盖见[测试](TESTING.md#ci)。

`.gitattributes` 对冻结评测和知识快照使用 `-text`。发生哈希失败时，从可信清单对应的 Git blob 恢复原字节，再验证清单。日志、数据库、密钥、依赖和模型缓存按现有忽略规则留在各自环境中。
