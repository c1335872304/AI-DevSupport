# Git 迁移与 Fast CI 排障

命令以 PowerShell 为例。把仓库路径、PR 编号和运行编号替换为本次交付的值。

## 本机目录核对记录

2026-11-19 核对时，当前源目录为 `C:\codes\AI_DevSupport`，独立 Git 克隆为 `C:\codes\AI-DevSupport-publish`。上个会话的交付位于 [PR #1](https://github.com/c1335872304/AI-DevSupport/pull/1)，分支为 `codex/support-demo-rag-ci`，本轮接续时远端 HEAD 为 `6eacc49`。本地克隆初始停在 `main` 的 `4d5c87b`，随后已切到 PR 分支。

本轮三个 P1 的修复与新增回归先在当前源目录验证，再按文件对照迁入该 PR 分支。同时对照迁入当前源目录已有的注册与邀请码移除改动，包括 `0020` 迁移和对应注册测试。冻结文件按原清单核验字节，并补齐 Phase A 数据集和厂商知识快照的 `-text` 属性。

## 先确认仓库和登录

```powershell
$repo = 'YOUR_OWNER/YOUR_REPO'
$remote = "git@github.com:${repo}.git"
git rev-parse --show-toplevel
ssh -T git@github.com
git ls-remote --symref $remote HEAD
gh auth status --hostname github.com
```

- 本地缺少 `.git` 时，先查项目是否已有 GitHub 仓库。已有仓库就独立克隆，保留已有提交和分支。原目录留作比对。
- SSH 成功时会显示 `successfully authenticated`，同时提示 GitHub 不提供 shell。用 `git ls-remote` 确认对目标仓库的读取权限，并从 `refs/heads/…` 识别默认分支。
- SSH 用于克隆和推送。开 PR 和看 CI 需要 GitHub CLI 另行授权。

```powershell
gh auth login --hostname github.com --git-protocol ssh --web
```

浏览器设备授权页填写的是**终端显示的一次性代码**。终端已关闭或代码已过期时，重新运行登录命令。分享日志和截图前删掉设备码、令牌、账号、本机用户目录，以及含 `email_token` 的通知链接。验收记录使用普通 PR 和 Actions 链接。

## 在独立克隆中迁移

```powershell
git clone $remote YOUR_REPO-review
Set-Location YOUR_REPO-review
git status --short
git log -5 --oneline
$branch = 'work/describe-the-change'
git switch -c $branch
```

逐项核对代码、迁移、依赖锁文件、测试和工作流。两边都改过的文件，先查远端提交，再合并重叠改动。原目录缺少的文件，先确认是否迁移或废弃。按审过的路径暂存。运行时 `.env`、密钥、数据库、缓存、依赖目录、日志和本机验收产物留在本地。示例配置只放占位值。

```powershell
git add -- PATH_TO_REVIEWED_FILE
git diff --cached --name-status
git diff --cached --check
git diff --cached
```

在独立检出中准备项目 Python 环境，再从仓库根目录检查文档链接和冻结评测输入。

```powershell
python backend/scripts/check_docs.py --checkout
python backend/scripts/check_phase4_inputs.py
```

检查完成后提交、用 SSH 推送分支并开 PR。

```powershell
git commit -m "Describe the change"
git push -u origin $branch
gh pr create --repo $repo --head $branch --fill
```

## 跟到 Fast CI 出结果

```powershell
gh pr checks PR_NUMBER --repo $repo --watch
gh run list --repo $repo --workflow ci-fast.yml --branch $branch --limit 8 --json databaseId,event,headSha,status,conclusion,url
gh run view RUN_ID --repo $repo --log-failed
```

先核对 `headSha` 是否为 PR 最新提交。同一提交可能分别触发 `push` 和 `pull_request`，两轮完成时间可以不同。验收看最新提交的 PR 检查。看到旧失败邮件时，用运行编号核对它对应的提交。修好后推送新提交，再跟踪新的运行。

验收记录包含 PR 链接、提交 SHA 和 Fast CI 链接。检查后端回归、退款和关单 HTTP 演示、前端构建、双账号浏览器验收及 Compose 是否通过。退款演示和诊断评测产物可在对应运行页查看。[Fast CI 工作流](../../.github/workflows/ci-fast.yml) · [审批演示复跑命令](../REFUND_APPROVAL_EXECUTION_PLAN.md)

## 已遇到的失败

| 日志表现 | 处理方式 |
| --- | --- |
| `check_phase4_inputs.py` 对 JSONL 报 `AssertionError` | 从可信源恢复原始字节，包括换行符。确认 `.gitattributes` 对清单中的文件设了 `-text`，再从干净检出验哈希。保留清单中的原始 SHA-256。 |
| Playwright 1.52 不支持 Ubuntu 26.04，或浏览器依赖安装迟迟无输出 | 当前前端作业固定在 Ubuntu 24.04，复用运行器预装的 Chrome，并打印浏览器版本。Python 依赖安装和浏览器测试分开显示，先确认停在哪一步。 |
| 本地文档检查通过，干净检出报缺文件 | 用 `check_docs.py --checkout` 复现。引用被 Git 忽略的本地生成报告时，在文档写出生成命令和输出路径。 |

浏览器断言失败时，从该次运行下载 `approval-browser-failure`，用追踪定位失败步骤和页面状态。分享追踪前检查会话内容、认证请求和本机路径。[Git 属性](../../.gitattributes) · [冻结输入清单](../../backend/eval/phase4/manifest.json)
