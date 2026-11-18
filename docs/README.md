# API 助手文档入口

更新于 2026-11-19。当前源码候选已完成会话隔离、多副本生成恢复与结算、审批接手续办修复。源码与 CI 的验收以[当前候选验收](04-testing/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)为准，生产发布环境的签验按[预发布手册](03-operations/CONTEXT_STAGING_ACCEPTANCE_RUNBOOK.md)执行。

## 当前入口

| 目的 | 文档 |
| --- | --- |
| 了解能力与范围 | [项目简介](PROJECT_INTRO.md) |
| 启动与更新 | [本地启动](01-getting-started/GETTING_STARTED.md) · [Docker 操作](03-operations/DOCKER_OPERATIONS.md) |
| 查看代码职责 | [架构总览](02-architecture/README.md) · [客服运行时](02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md) |
| 理解检索与入库 | [知识流水线](02-architecture/KNOWLEDGE_PIPELINE.md) · [官方语料](01-getting-started/VENDOR_KNOWLEDGE.md) · [RAG 运维](03-operations/RAG_OPERATIONS.md) |
| 理解会话与诊断 | [上下文系统](02-architecture/CONTEXT_SYSTEM.md) · [诊断闭环](02-architecture/DIAGNOSIS_LOOP.md) · [诊断恢复](03-operations/DIAGNOSIS_OPERATIONS.md) |
| 查看工单与审批 | [管理员工单台](02-architecture/ADMIN_TICKET_CONSOLE.md) · [退款与关单审批](REFUND_APPROVAL_EXECUTION_PLAN.md) |
| 运行演示 | [三条演示](03-operations/PROJECT_DEMOS.md) · [客服正式入口演示](03-operations/CUSTOMER_SERVICE_DEMO.md) |
| 查看当前验证 | [源码候选验收](04-testing/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md) · [真实模型与性能对照](04-testing/ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md) |
| Git 与持续集成 | [仓库与 PR 操作](03-operations/GIT_AND_FAST_CI.md) · [现行 CI 门禁](03-operations/CI_PLAN.md) |
| 发布与观测 | [生产运行边界](03-operations/PRODUCTION.md) · [预发布签验](03-operations/CONTEXT_STAGING_ACCEPTANCE_RUNBOOK.md) · [Langfuse](03-operations/LANGFUSE.md) |
| 排查环境问题 | [网络与 Provider](03-operations/NETWORK_TROUBLESHOOTING.md) · [Billing MCP](03-operations/DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md) |
| 查看剩余工作 | [技术债务台账](MAINTENANCE.md) · [客服工程改进](ERP_AGENT_PRACTICES_ADOPTION_PLAN.md) |
| 复跑评测 | [六层评测规范](04-testing/EVALUATION.md) · [评测样本库](04-testing/USER_QUESTION_SIMULATION.md) · [脚本说明](../backend/scripts/README.md) |

## 历史设计与执行记录

[四阶段计划](FOUR_PHASE_ITERATION_PLAN.md)及其[最终验收](04-testing/FINAL_PROJECT_ACCEPTANCE.md)记录四阶段核心交付。[RAG 演进设计](02-architecture/RAG_EVOLUTION_DESIGN.md)和[开源参考](02-architecture/RAG_UPSTREAM_REVIEW.md)保留设计依据。上下文实施过程见[上下文计划](CONTEXT_SYSTEM_PLAN.md)。

2026-10-20 的 Docker 升级、语料替换、回答质量、上下文预算、缓存和流式报告属于各自执行日期的验证记录。旧题失败、历史成绩和当时的镜像信息应连同原条件阅读。较早的测试与语料演进从[历史索引](04-testing/history/README.md)进入，真实模型历史记录见[测试计划](05-live-tests/DEEPSEEK_LIVE_TEST_PLAN.md)与[执行报告](05-live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。

## 维护方式

架构文档描述代码行为，运维手册提供操作，计划跟踪未完成事项，验收报告保留具体版本和执行证据。当前测试数字集中在候选验收中维护。知识快照、运行时 Skill、业务数据和历史验收原文各自保留其输入或证据用途。

修改路径后从项目根目录运行 `python backend/scripts/check_docs.py`。干净 Git 检出使用 `--checkout`，允许缺少留在本地的 `backend/data` 验收产物。文档整理沿用既有知识向量和配置。
