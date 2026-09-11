# API 助手文档导航

项目 Markdown 按用途分目录管理。产品前端品牌为“API 助手”；代码包、Compose 项目名和数据库名中的 `PaiSmart` 属于内部技术标识。本导航只整理项目说明，不移动运行时会读取的 Demo 知识库或 Skill 文件。

## 文档维护规则

- `01-getting-started/`：第一次接手项目、启动和最小验收；
- `02-architecture/`：当前实现的架构基线，代码变化后必须同步更新；
- `03-operations/`：Docker、网络、CI 和生产运行边界；
- `04-testing/`：测试计划、执行报告和历史复验记录，全部保留，不因架构更新删除；
- `05-live-tests/`：真实模型、成本和 Provider 网络测试记录，保留为独立审计材料。

架构文档从 [02-architecture/README.md](02-architecture/README.md) 进入；测试结果不复制到架构文档，避免出现多个互相矛盾的数字。

## 本次整理结果（2026-09-10）

- 保留 `04-testing/` 和 `05-live-tests/` 下全部测试计划、报告及历史过程记录；
- 新增 [架构总览](02-architecture/README.md)，统一说明当前边界、架构决策、代码映射和测试关联；
- 更新客服 Agent 架构、RAG 架构和管理员工单台架构，删除过期的执行数字，改为链接到测试报告；
- 将质量门的稳定架构契约放回 `02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md`，把限流首次问答的具体过程保留在测试记录中；
- 修正根 README 中 Billing MCP 的描述，避免把 API 诊断误写成 MCP 路由。

```text
docs/
├── 01-getting-started/   # 第一次启动与本地验收
├── 02-architecture/      # Agent、RAG 与生产边界
├── 03-operations/        # Docker、Billing MCP、CI 与运维
├── 04-testing/           # 离线评测、RAG 专项与项目 E2E
└── 05-live-tests/        # 真实模型的限量测试记录
```

## 快速开始

适合第一次接手项目、启动 Docker Demo 或确认服务是否正常：

| 文档 | 用途 | 状态 |
|---|---|---|
| [GETTING_STARTED.md](01-getting-started/GETTING_STARTED.md) | 本地启动、账号、模型 Key、Demo 知识库和最小验收 | 当前入口 |

## Docker 与运维

| 文档 | 用途 | 状态 |
|---|---|---|
| [DOCKER_OPERATIONS.md](03-operations/DOCKER_OPERATIONS.md) | 启停、健康检查、日志、测试、重建和安全清理 | 当前入口 |
| [NETWORK_TROUBLESHOOTING.md](03-operations/NETWORK_TROUBLESHOOTING.md) | Docker CLI、Windows 代理、DashScope DNS、离线 Embedding 和 Provider 排障 | 当前入口 |
| [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](03-operations/DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md) | Docker 拓扑、本地 Billing MCP 与验收边界 | 当前实现 |
| [CI_PLAN.md](03-operations/CI_PLAN.md) | Fast / Integration / Live 分层 CI、RAG 门禁和外部模型成本控制 | Fast CI 已实现；Integration / Live 待补 |
| [PRODUCTION.md](03-operations/PRODUCTION.md) | 数据库迁移、工单、MCP Auth、Kafka、监控和生产边界 | 生产规划 |

## 架构与开发

| 文档 | 用途 | 状态 |
|---|---|---|
| [README.md](02-architecture/README.md) | 当前架构入口、决策、不变量、代码映射和测试关联 | 当前架构入口 |
| [CUSTOMER_SERVICE_ARCHITECTURE.md](02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md) | Agent、Skill、Tool、MCP、RAG、证据、质量门和安全边界 | 当前架构基线 |
| [ADMIN_TICKET_CONSOLE.md](02-architecture/ADMIN_TICKET_CONSOLE.md) | 管理员工单台、权限、分页接口、数据边界与验收方式 | 当前实现；跨用户页面夹具待补 |
| [KNOWLEDGE_PIPELINE.md](02-architecture/KNOWLEDGE_PIPELINE.md) | 知识文档、父子 Chunk、Qwen Embedding、Elasticsearch 与索引版本 | 当前实现 |
| [EVALUATION.md](04-testing/EVALUATION.md) | 路由、工具调用、引用、最终回答和安全质量评测 | 当前评测规范 |

## RAG 测试与结果

> 本节所有测试计划、执行报告和历史复验记录均保留。架构变更更新 `docs/02-architecture/`；测试结果只在对应报告中追加或修订，不删除历史过程。

| 文档 | 用途 | 状态 |
|---|---|---|
| [RAG_ADVANCED_TEST_PLAN.md](04-testing/RAG_ADVANCED_TEST_PLAN.md) | 高级 RAG 用例、指标、权限、安全、性能和发布门禁 | 计划已执行部分专项 |
| [RAG_ADVANCED_TEST_REPORT.md](04-testing/RAG_ADVANCED_TEST_REPORT.md) | 60 条带过滤 Demo 烟雾评测及其局限 | 已完成 |
| [RAG_BLIND_TEST_SUITE.md](04-testing/RAG_BLIND_TEST_SUITE.md) | 60 条无预设过滤盲测与隔离夹具定义 | 已设计并执行可执行子集 |
| [RAG_BLIND_TEST_REPORT.md](04-testing/RAG_BLIND_TEST_REPORT.md) | 41 条公开盲测、12 份夹具、19 项隔离检查的结果 | 已完成；最终答案/压测待补 |

当前可复核的检索基线是：公开盲测 41 条、`k=6` 时 `Hit Rate@6=1.000`、`Recall@6=1.000`、`MRR=0.795`、`nDCG=0.847`。带目标 metadata 的 60 条烟雾集全命中，但不能替代盲测成绩。

## 真实模型与成本受控测试

| 文档 | 用途 | 状态 |
|---|---|---|
| [DEEPSEEK_LIVE_TEST_PLAN.md](05-live-tests/DEEPSEEK_LIVE_TEST_PLAN.md) | DeepSeek 真实聊天、RAG、权限、余额和用量监控的限量测试方案 | 可复用方案 |
| [DEEPSEEK_LIVE_TEST_REPORT.md](05-live-tests/DEEPSEEK_LIVE_TEST_REPORT.md) | 小样本真实调用的脱敏执行记录 | 已完成小样本；未跑批量 live |
| [PROJECT_E2E_TEST_PLAN.md](04-testing/PROJECT_E2E_TEST_PLAN.md) | 浏览器主链路、真实用户提问、RAG、工单、后台、失败回退的总控验收方案 | 已执行；存在待修复问题 |
| [USER_QUESTION_SIMULATION.md](04-testing/USER_QUESTION_SIMULATION.md) | 60 条真实用户问题模拟，覆盖口语、追问、混合意图、安全和无答案边界 | 已设计；7 条 Live 已执行 |
| [PROJECT_E2E_TEST_REPORT.md](04-testing/PROJECT_E2E_TEST_REPORT.md) | 完整项目实际执行过程、真实用户问题、权限、工单、用量和缺陷结果 | 已执行；存在待修复问题 |
| [PROJECT_E2E_REMEDIATION_PLAN.md](04-testing/PROJECT_E2E_REMEDIATION_PLAN.md) | E2E 已发现问题的隔离、质量、成本、部署与界面修复计划 | 第一轮已实施；Live 待复验 |
| [PROJECT_E2E_REMEDIATION_REPORT.md](04-testing/PROJECT_E2E_REMEDIATION_REPORT.md) | E2E 修复代码、离线回归、构建与容器重建验证记录 | 第一轮已完成；Live 待复验 |
| [PROJECT_TEST_REPORT_2026-09-09.md](04-testing/PROJECT_TEST_REPORT_2026-09-09.md) | 本轮后端、前端、离线评测、RAG 与环境问题复验 | 已完成；Docker/远端 Provider 待环境恢复 |
| [ADMIN_TICKET_CONSOLE_TEST_PLAN.md](04-testing/ADMIN_TICKET_CONSOLE_TEST_PLAN.md) | 管理员工单台的 API、页面、权限、脱敏与恢复测试用例 | 已执行；结果见测试报告 |
| [ADMIN_TICKET_CONSOLE_TEST_REPORT.md](04-testing/ADMIN_TICKET_CONSOLE_TEST_REPORT.md) | 管理员工单台本轮真实 API、浏览器、权限与恢复执行结果 | 已执行；跨用户夹具待补 |
| [QUALITY_GATE_REDESIGN_2026-09-09.md](04-testing/QUALITY_GATE_REDESIGN_2026-09-09.md) | 质量门过滤、证据判断与首次限流问答的历史验收记录 | 测试记录；架构以 02-architecture 为准 |

## 推荐阅读路线

```text
第一次启动：README -> 01-getting-started/GETTING_STARTED -> 03-operations/DOCKER_OPERATIONS
理解架构：02-architecture/README -> 02-architecture/CUSTOMER_SERVICE_ARCHITECTURE -> 02-architecture/KNOWLEDGE_PIPELINE -> 02-architecture/ADMIN_TICKET_CONSOLE
复核 RAG：04-testing/RAG_ADVANCED_TEST_PLAN -> 04-testing/RAG_ADVANCED_TEST_REPORT -> 04-testing/RAG_BLIND_TEST_REPORT
准备 CI：03-operations/CI_PLAN -> 03-operations/DOCKER_OPERATIONS -> 各专项测试脚本
```

## 不要混入项目说明导航的 Markdown

- `backend/demo_knowledge/*.md`：运行时 Demo 知识库正文，`demo-seed` 会读取并写入 Elasticsearch；修改它会改变检索结果。
- `backend/skills/**/SKILL.md` 及其 `references/*.md`：Agent 运行时 Skill / 参考资料，属于可执行提示和约束；不要为了整理文档而移动或合并。
- `backend/eval/*.jsonl`：评测数据集，不是说明文档；对应的用例解释放在 `04-testing/` 的 RAG 测试文档中。
