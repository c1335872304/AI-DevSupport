# 测试与验收

日常修改先运行相关检查，完整交付由 CI 记录提交 SHA 和结果。最新代码基线的范围与成绩见[候选验收](archive/reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)，原始样本和过程从[历史索引](archive/README.md)查阅。

## 本地检查

在 `backend` 的已准备环境运行。

```powershell
python -m compileall -q app scripts
python scripts/check_docs.py --checkout
python -m ruff check --select E9,F63,F7,F82 app scripts tests
python -m pytest tests -q
python scripts/check_phase4_inputs.py
```

已有本地证据时可省略文档检查的 `--checkout`，检查全部目标。干净检出通过该选项允许缺少 `backend/data` 生成证据，源码、日常手册和已归档文档仍需完整。

在 `frontend` 使用 Node 20、pnpm 9.15.5，运行 `pnpm lint`、`pnpm typecheck`、`pnpm test:stream`、`pnpm build`。lint 为只读且要求零警告，显式修复使用 `pnpm lint:fix`。`.npmrc` 缩短 Windows 虚拟依赖路径。从仓库根目录运行 `docker compose config --quiet` 校验编排。

针对会话、结算和审批的专项回归为以下文件。

```powershell
python -m pytest -q tests/e2e/test_release_p1_regressions.py tests/agent/test_token_reservation.py tests/e2e/test_refund_approval_preview.py
```

这些测试使用合成数据。MySQL P1 专项支持 `P1_MYSQL_TEST_URL`，目标库名需以 `p1_release_` 开头，由专门临时数据库承接创建与清理。实际 MySQL 测试结果和 SQLite 结果分别记录。

<a id="demos"></a>

## 可复现演示

| 入口 | 命令与结果 |
| --- | --- |
| 退款与关单 HTTP | 在 `backend` 运行 `python scripts/run_refund_sandbox_demo.py`，临时 API 与合成支付服务验证同一回执及原工单关闭 |
| 退款与关单浏览器 | 在 `frontend` 运行 `pnpm exec playwright test -c approval-demo.playwright.config.ts`，使用双账号验证原会话刷新与结果 |
| 正式客服入口 | 在根目录运行 `docker compose -f deploy/compose.customer-demo.yaml run --rm --build demo`，核对无请求号澄清、统计与工单失败恢复 |
| 三条诊断演示 | 在 `backend` 启动 `python scripts/phase4_demo_server.py`，另一终端运行 `python scripts/verify_phase4_demos.py` |

Windows 浏览器演示可设置 `REFUND_DEMO_PYTHON` 为实际 Python 解释器路径，`REFUND_DEMO_BROWSER` 为已有 Chrome 可执行文件。Linux CI 复用运行器 Chrome。演示入口使用临时库或专用数据目录，正式客服演示每轮使用新的空证据目录。

`CUSTOMER_DEMO_EVIDENCE` 可指定正式客服演示的证据目录，已有候选镜像通过 `CUSTOMER_DEMO_IMAGE` 传入。退款浏览器验收配置见 [approval-demo.playwright.config.ts](../frontend/approval-demo.playwright.config.ts)。三条诊断演示使用独立回环服务和合成日志，修正后的新请求需在夹具有效窗口内复查。

<a id="ci"></a>

## CI

| 工作流 | 触发与覆盖 |
| --- | --- |
| [Fast CI](../.github/workflows/ci-fast.yml) | 主分支 push / pull request / 手动，后端编译、离线回归、文档、Ruff、冻结输入、业务演示与轨迹评分，前端零警告 lint、类型、流式重放、构建和浏览器，Compose |
| [隔离集成](../.github/workflows/ci-integration.yml) | 相关 PR 路径或手动触发，真实 MySQL / Elasticsearch / Redis、跨进程领取与诊断恢复、共享审批、事件与用量对账、Billing MCP 协议，保存 JUnit |
| 真实模型 | 显式 CLI 和受控预算运行，记录模型配置、题集、Provider 用量及失败 |

```powershell
gh pr checks 1 --repo c1335872304/AI-DevSupport --watch
gh run list --repo c1335872304/AI-DevSupport --branch codex/support-demo-rag-ci --limit 6 --json databaseId,event,headSha,status,conclusion,url
gh run view <run-id> --repo c1335872304/AI-DevSupport --log-failed
```

先核对 `headSha`，开发分支通过 PR 跑完整检查，主分支 push 与手动入口保留，避免同一 PR 提交重复跑 push 和 PR 两轮。失败修复后以最新提交为准。跳过项随结果披露，隔离集成与离线替身的范围分别解释。

## 债务关闭回归

`tests/e2e/test_debt_closure.py` 覆盖共享检查点、审批自动恢复、重试暂停、Provider 未知用量与收据去重、工单状态及角色权限。默认跑 SQLite，`DEBT_MYSQL_TEST_URL` 指向独立 `/rag_acceptance` 库时同时跑真实 MySQL。`tests/e2e/test_shared_generation_events.py` 通过 `GENERATION_TEST_REDIS_URL` 验证真实 Redis 与独立进程接收及取消。

集成用例有创建合成业务数据的行为，只能指向专用测试实例。ES 集成通过 `ELASTICSEARCH_URL` 指定测试实例。实际 API 复验需显式 `--live`，本轮用量和原回答见候选验收，默认 CI 不调用供应商模型。

## 题库

| 测试输入 | 位置与范围 |
| --- | --- |
| 当前成对题集 | `backend/eval/customer_service/phase_a_regression.jsonl` 48 条、`phase_a_release.jsonl` 12 条，原清单固定哈希 |
| 扩展客服题 | `backend/eval/customer_service/benchmark.jsonl` 与 `benchmark_extended.jsonl` |
| 检索题 | `backend/eval/vendor_full_rag.jsonl`、`advanced_rag*.jsonl` |
| 诊断机制题 | `backend/eval/phase4/diagnosis.jsonl`，由冻结清单约束 |
| 回答质量与复杂度 | `backend/eval/independent_answers_v1.json`、`answer_quality_new_v1.json`、`complexity_chain_v1.json` |
| 手工问法候选 | [manual_question_candidates.json](../backend/eval/customer_service/manual_question_candidates.json)，从旧文档提取的 60 条未复核输入 |
| 回归与夹具 | `backend/tests`，沿用已有用例和测试数据 |

候选问法保留原预期边界，需对照当前实现复核后再纳入正式题集。它们的保存与执行结果分别记录，默认 CI 沿用现有冻结题集。

N12 地域专项的离线回归位于 `tests/knowledge/test_region_context.py`、`tests/agent/test_answer_quality_regression.py` 和 `tests/agent/test_document_context.py`。真实复验使用 `python scripts/retest_n12_scope.py --live --output data/checkpoints/n12-fresh-run`，同四题及人工判分见[修复记录](archive/evidence/N12_SCOPE_FAILURE_2026-10-20.md)。显式入口会发送检索片段并产生实际模型用量，默认 CI 不执行。

## 冻结与产物

Phase 4 校验四份冻结输入及机制任务，Phase A 和官方知识快照由各自回归核验原 SHA-256。`.gitattributes` 保留受哈希约束的文件字节，普通文档整理沿用既有清单。

[验收索引](archive/README.md)保留当前代码、真实模型性能及核心机制的最终结论。供应商请求流水和原始运行结果按报告指向的 `backend/data` 路径核对。

历史汇总脚本的默认输出为 `backend/data/reports/2026-10-20`，按需生成。比较时固定问法、语料、模型、配置和判分规则，披露引用、事实范围、失败及用量。默认 CI 使用离线模型和工具替身，真实模型由显式入口和受控预算运行。

## 编排与业务进度

`tests/agent/test_orchestration_improvements.py` 覆盖参考材料按需读取与复用、越界/跨 Skill 访问拒绝、补查次数和预算、失败不重试、账期与文档锚点保留，以及完整运行时中的依赖补齐。默认使用隔离工具和模型替身。

前端 `pnpm test:stream` 同时验证阶段白名单、任务隔离、迟到事件和完成后的保护。浏览器演示包含业务进度的展示与“等待补充信息”的完成状态，使用模拟 WebSocket，不调用真实模型。
