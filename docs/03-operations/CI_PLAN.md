# 质量门禁与 CI

状态核对至 2026-11-19。工作流已在 GitHub 执行，源码候选 `99e7485` 的 push、pull request Fast CI 和隔离集成均通过。当前分支与结果见[Git 操作记录](GIT_AND_FAST_CI.md)及[源码候选验收](../04-testing/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。

| 层级 | 入口 | 当前覆盖 |
| --- | --- | --- |
| Fast | [.github/workflows/ci-fast.yml](../../.github/workflows/ci-fast.yml) | 后端编译、离线回归、文档链接、关键 Ruff、冻结数据、诊断轨迹、退款与关单 HTTP 演示，前端类型、构建、双账号浏览器验收，Compose 校验 |
| Integration | [.github/workflows/ci-integration.yml](../../.github/workflows/ci-integration.yml) | 手动或相关 PR 路径触发，专用 MySQL / Elasticsearch，构建并发与跨进程领取、诊断恢复和真实 Billing MCP 协议，保存 JUnit |
| Live | `scripts/evaluate_phase4_diagnosis.py --live --model deepseek-flash` | 显式手动运行，使用合成业务数据和官方 Provider，受预算及用量审计约束 |

Fast 使用模型及向量替身验证工程行为，真实 Provider 调用通过显式入口运行。测试替身的成绩适用测试夹具条件，检索效果和模型质量由真实调用报告说明。

## 本地复跑

在 `backend` 目录运行以下命令。

```powershell
python -m compileall -q app scripts
python scripts/check_docs.py --checkout
python -m ruff check --select E9,F63,F7,F82 app scripts tests
python -m pytest tests -q
python scripts/check_phase4_inputs.py
python scripts/run_refund_sandbox_demo.py
```

前端运行 `pnpm typecheck`、`pnpm build`，浏览器演示命令见[审批方案](../REFUND_APPROVAL_EXECUTION_PLAN.md)。从项目根目录运行 `docker compose config --quiet` 检查编排。

远端安装 `requirements-dev.txt`。后端当前阻断 E9/F63/F7/F82，前端执行类型及生产构建。存量 ESLint 风格规则由[债务台账](../MAINTENANCE.md)跟踪。

## 冻结输入与结果解释

Phase 4 校验四份冻结输入的 SHA-256 和机制任务。Phase A 和官方知识快照由对应回归按原清单核验。受哈希约束的文件在 `.gitattributes` 设置 `-text`，检出和迁移时保留原字节。更改评测定义须更新其版本和依据，普通格式整理沿用既有清单。

外部条件造成的跳过需随结果披露。隔离集成的 MySQL、Elasticsearch 和 Billing MCP 结果与离线替身结果分别读取。每轮 CI 先核对 `headSha`，push 与 pull request 的两轮检查按同一提交判断。

现有大体量本地知识向量、模型缓存和历史 `backend/data` 证据由各验收报告指向。干净检出文档检查的 `--checkout` 允许缺少这些生成证据，源码、测试和运行入口的缺失仍会报错。
