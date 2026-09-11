# PaiSmart 简单 CI 规划

状态：Fast CI 已实现为 `.github/workflows/ci-fast.yml`；Docker 集成与真实模型 Live CI 仍保持规划状态。当前工作区尚未初始化 Git，推送到 GitHub 后工作流才会触发。  
目标：每次提交先阻止明显回归；真实模型与高成本 RAG 测试保持手动、受预算控制。

## 1. 结论

项目适合先上一个三层 CI，而不是一开始把所有 Docker 服务和外部模型都塞进每个提交：

| 层级 | 触发 | 预计耗时 | 外部模型/费用 | 是否阻断合并 |
|---|---|---:|---|---|
| Fast | 每次 Push、PR | 5～10 分钟 | 无 | 是 |
| Integration | 手动或主分支每日一次 | 15～25 分钟 | 默认无 | 主分支失败时是 |
| Live provider | 仅手动批准 | 不固定 | Qwen / DeepSeek，受预算控制 | 否，先作为报告 |

推荐使用 GitHub Actions；若代码不在 GitHub，也可把同一套命令放到 GitLab CI、Jenkins 或本机自托管 Runner。Fast 工作流现已接入 `.github/workflows/ci-fast.yml`；它只跑离线检查，不读取 `.env`、Qwen 或 DeepSeek Key。

## 2. Fast：每次提交必跑

运行环境：Ubuntu + Python 3.12 + Node 20 + pnpm 8/9。不要启动 MySQL、Elasticsearch、Kafka，也不要读取真实 `.env`。

| 检查 | 建议命令 | 目的 |
|---|---|---|
| 后端编译 | `python -m compileall -q backend/app backend/scripts` | 阻止导入、类型注解和语法错误 |
| 后端离线测试 | `python -m pytest backend/tests/agent backend/tests/architecture backend/tests/skills backend/tests/security backend/tests/evaluation -q` | 路由、实体、权限、工具契约与评测回归 |
| 前端类型检查 | `cd frontend && pnpm typecheck` | 路由、接口字段、Vue 类型回归 |
| 前端构建 | `cd frontend && pnpm build` | 保证 Vite 产物可构建 |
| Docker 配置 | `docker compose config -q` | Compose 变量、引用与 YAML 合法性 |
| 数据集校验 | 下一阶段加入 | 防止 RAG 测试集被误删或变成假样本 |

已实现：CI 单独安装 `backend/requirements-dev.txt`，不把开发依赖塞进生产镜像；后端 Ruff 先只拦截语法/致命规则，避免 517 条既有风格告警阻断首次接入。前端暂跑类型检查与构建；全量 ESLint 当前有 73 条存量错误，留待单独清理后再设为门禁。

## 3. Integration：受控本地依赖测试

运行在自托管 Runner 或具备 Docker 的 CI Runner，使用独立 Docker volume/项目名，绝不连接开发机正在使用的 `paismart-demo` 数据卷。

### 必跑项

1. `docker compose up -d --build`，等待 API、MySQL、Redis、MinIO、Elasticsearch、Kafka 健康；
2. 数据库迁移和 Demo 入库成功；
3. 基础 14 条 RAG 回归；
4. 公开盲测 41 条无预设 filter，输出 Hit Rate@6、Recall@6、MRR、nDCG；
5. 导入 `fixture-*` 文档，运行 19 项版本、metadata 与组织 A/B 隔离检查；
6. 完成后导出 JSON 报告和容器日志为 CI artifact，并销毁该次 CI 的测试 volume。

### 预算与模型策略

默认 Integration 使用本地 hash embedding：

```env
EMBEDDING_API_KEY=
LLM_API_KEY=
```

这样测试的是索引、权限、metadata、路由和回归流程，不产生供应商费用。它不能作为 Qwen 质量结论；Qwen 质量见第三层。

### 初始门槛

| 项目 | 门槛 |
|---|---|
| API / 核心依赖健康 | 全部通过 |
| 组织隔离与错误 metadata | 0 泄露、0 错误放宽 |
| 基础 RAG 14 条 | Hit Rate@6 = 1.0 |
| 公开盲测 41 条 | Hit Rate@6 ≥ 0.95；MRR ≥ 0.75；nDCG ≥ 0.82 |
| Docker / 后端 / 前端检查 | 全部通过 |

当前公开盲测基线是 MRR 0.795、nDCG 0.847。因此不要把 1.000 写成合并门槛，否则 CI 只会鼓励“带答案过滤”的测试集。

## 4. Live provider：手动、限额、只产出报告

触发方式：GitHub Actions `workflow_dispatch` 或人工在自托管 Runner 执行。必须从 CI Secret 读取 Key，日志、测试报告和 artifact 禁止出现 Key、密码、Bearer Token、完整客户数据。

| 测试 | 上限 | 通过条件 |
|---|---:|---|
| Qwen 公开盲测 | 41 条查询向量 | 与基线比较，MRR/nDCG 下降超过 0.03 则标黄 |
| Qwen 版本/权限夹具 | 12 入库 + 19 查询 | 0 跨组织泄露 |
| DeepSeek 两轮改写 | 最多 2 个会话、每次改写 ≤160 Tokens | 至多一次改写、缓存/回退正常 |
| DeepSeek 最终答复安全 | 最多 10 条 | 注入、个人状态、无答案不产生不安全断言 |

任何网络失败不得自动重试整批；单条失败写入报告并停止同类 live 测试。Live workflow 默认不阻断 PR，人工审阅报告后决定是否发布。

## 5. 建议目录与工作流拆分

```text
.github/workflows/
  ci-fast.yml                 # Push / PR：无服务启动、无外部 Key
  ci-integration.yml          # 手动 / nightly：Docker、本地 hash embedding
  ci-live-rag.yml             # workflow_dispatch：Qwen/DeepSeek，需批准
scripts/
  ci_validate_datasets.py     # 校验 JSONL、ID、类别、fixture 标记
  seed_advanced_rag_fixtures.py
  evaluate_rag_blind_fixtures.py
```

每个 workflow 都应设置：并发取消旧任务、固定依赖版本、超时、最小权限、artifact 保留期（建议 7 天）和失败时日志收集。

## 6. 实施顺序

1. 已建立 `ci-fast.yml`：后端编译、致命规则检查、离线测试，前端类型检查/构建和 Compose 配置校验；
2. 连续观察 5～10 次提交，修复环境不稳定与误报后，将 Fast 设为主分支合并门禁；
3. 单独清理前端 73 条 ESLint 存量错误，并加入只读 lint 门禁；
4. 新增数据集校验脚本；
5. 建立独立 Compose 集成环境与 fixture 清理流程；
6. 最后才添加手动 live provider 工作流及成本阈值。

## 7. 完成定义

- [x] Fast workflow 已加入仓库；推送 GitHub 后，PR 会看到检查及失败原因；
- [ ] CI 不读取开发机 `.env` 或真实 Key；
- [ ] Integration 数据与本地 Demo 数据隔离，失败后仍能清理；
- [ ] RAG 报告保留总体和按类别指标，以及 Top-1 错误样本；
- [ ] 权限泄露、语法/构建失败、测试失败能阻断合并；
- [ ] Qwen/DeepSeek 只在显式手动触发下运行，费用和失败均可追溯。
