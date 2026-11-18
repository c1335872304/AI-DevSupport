# API 助手文档入口

更新：2026-10-20。四阶段核心迭代已完成，Docker Demo 已原地更新并保留知识库与配置；截图输入为未实施的可选项。

随后按明确替换要求，Docker知识库已迁移为三家各20份官方正文、5888条复用千问向量；见[官方语料迁移验收](04-testing/DOCKER_VENDOR_KNOWLEDGE_MIGRATION_2026-10-20.md)。前一份升级报告中的21份是替换前的历史状态。

后续已修复迁移验收暴露的厂商召回和账单安全门不一致，见[最新修复与Docker重验](04-testing/VENDOR_SCOPE_AND_BILLING_GATE_FIX_2026-10-20.md)。

随后补充了实际检索与生成的[独立端到端回答评测](04-testing/INDEPENDENT_ANSWER_EVALUATION_2026-10-20.md)及[逐题回答证据](04-testing/INDEPENDENT_ANSWER_CASES_2026-10-20.md)。新评测发现仍有诊断门误拦文档问答、引用错位等问题；检索命中率不能代表回答质量。

这些问题已按优先级修复并部署Docker，见[回答链路修复与新旧题重验](04-testing/ANSWER_QUALITY_FIX_2026-10-20.md)。原12题通过，新12题11通过、1部分通过；地域计费范围表达仍列为剩余问题。

## 从哪里开始

最新完成[按问题复杂度优化调用链及Docker验收](04-testing/COMPLEXITY_CHAIN_OPTIMIZATION_2026-10-20.md)：简单配置题减少模型规划，401/429保留完整诊断与复查；记录配对质量、耗时及费用。

随后完成[简单文档题上下文优化](04-testing/EVIDENCE_BUDGET_OPTIMIZATION_2026-10-20.md)：精简模型侧元数据、合并重叠证据并控制预算；同时记录缓存差异与失败重测，不用调用次数代替费用。

最新完成[稳定证据前缀与Docker缓存验收](04-testing/STABLE_PREFIX_OPTIMIZATION_2026-10-20.md)：选材后稳定排序、同步来源编号、文档前置问题后置；真实检索首轮和固定证据换问法实验分开报告。

随后完成[实时流式输出与Docker验收](04-testing/LIVE_STREAMING_ACCEPTANCE_2026-10-20.md)：生成期间检查并推送完整短句或代码块，展示真实工作流进度，结束后校准权威正文；保留现有知识库、向量和配置。

| 目的 | 文档 | 权威范围 |
| --- | --- | --- |
| 了解项目 | [项目简介](PROJECT_INTRO.md) | 产品能力与边界 |
| 启动开发环境 | [本地启动](01-getting-started/GETTING_STARTED.md) | 配置、迁移、启动 |
| 了解代码 | [架构总览](02-architecture/README.md) | 模块职责与依赖方向 |
| 理解 RAG | [知识流水线](02-architecture/KNOWLEDGE_PIPELINE.md) | 当前实现与一致性契约 |
| 导入官方资料 | [知识库说明](01-getting-started/VENDOR_KNOWLEDGE.md) | DeepSeek、Qwen、GPT 快照与来源 |
| 运行与恢复 | [RAG 操作手册](03-operations/RAG_OPERATIONS.md) | Docling、任务、修订、故障恢复 |
| 复跑客服演示 | [正式入口演示](03-operations/CUSTOMER_SERVICE_DEMO.md) | 无请求号诊断、工单写入和恢复 |
| 查看客服候选验收 | [性能、用量与预发布演练](04-testing/ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md) · [预发布手册](03-operations/CONTEXT_STAGING_ACCEPTANCE_RUNBOOK.md) | 同一候选的真实模型对照、依赖故障、通知门禁与回滚 |
| 运行退款沙箱演示 | [退款审批与执行方案](REFUND_APPROVAL_EXECUTION_PLAN.md) | 人工审批、落库退款、同编号查单和回执恢复 |
| 查看最新验收 | [Docker升级验收](04-testing/DOCKER_DEMO_UPGRADE_2026-10-20.md) · [最终验收](04-testing/FINAL_PROJECT_ACCEPTANCE.md) · [第三阶段验收](04-testing/DIAGNOSIS_LOOP_ACCEPTANCE.md) · [第二阶段验收](04-testing/DIAGNOSIS_STATE_ACCEPTANCE.md) · [RAG 验收](04-testing/RAG_PHASE_ONE_ACCEPTANCE.md) | 各阶段测试结果、指标和限制 |
| 查看进度 | [第四阶段检查点](04-testing/PHASE_FOUR_PROGRESS.md) · [第三阶段检查点](04-testing/PHASE_THREE_PROGRESS.md) · [第二阶段检查点](04-testing/PHASE_TWO_PROGRESS.md) · [RAG 检查点](04-testing/LONG_TASK_PROGRESS.md) | 状态和证据位置 |
| 安排后续迭代 | [四阶段计划](FOUR_PHASE_ITERATION_PLAN.md) · [客服 Agent 工程改进计划](ERP_AGENT_PRACTICES_ADOPTION_PLAN.md) | 迭代范围、写入边界与验收进度 |
| 维护项目 | [整理记录与剩余债务](MAINTENANCE.md) | 已清理事项、保留理由及后续债务 |

## 按主题查阅

- Agent：[诊断闭环](02-architecture/DIAGNOSIS_LOOP.md)、[诊断状态与证据](02-architecture/DIAGNOSIS_STATE.md)、[客服运行时架构](02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md)、[管理员工单台](02-architecture/ADMIN_TICKET_CONSOLE.md)。
- RAG：[设计与实施对照](02-architecture/RAG_EVOLUTION_DESIGN.md)、[企业开源参考](02-architecture/RAG_UPSTREAM_REVIEW.md)。当前行为以知识流水线为准，设计文档保留演进背景。
- 运维：[三条演示](03-operations/PROJECT_DEMOS.md)、[诊断恢复](03-operations/DIAGNOSIS_OPERATIONS.md)、[Docker 操作](03-operations/DOCKER_OPERATIONS.md)、[重启指南](03-operations/PROJECT_RESTART_GUIDE.md)、[网络排障](03-operations/NETWORK_TROUBLESHOOTING.md)、[Billing MCP 拓扑](03-operations/DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md)。
- 工程规划：[生产边界](03-operations/PRODUCTION.md)、[CI 计划](03-operations/CI_PLAN.md)。这里的待办不视为已经完成的能力。
- 评测：[六层评测规范](04-testing/EVALUATION.md)、[用户问题集](04-testing/USER_QUESTION_SIMULATION.md)、[A 写入验收](04-testing/RAG_BATCH_A_REPORT.md)、[B 生命周期验收](04-testing/RAG_BATCH_B_REPORT.md)、[C 解析检索验收](04-testing/RAG_BATCH_C_REPORT.md)。
- 历史：[旧测试与语料演进索引](04-testing/history/README.md)、[真实模型测试计划](05-live-tests/DEEPSEEK_LIVE_TEST_PLAN.md)、[历史真实模型报告](05-live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)。历史成绩只能按原报告条件解读。
- 脚本：[用途与运行边界](../backend/scripts/README.md)。

## 维护规则

1. `02-architecture/` 描述当前实现；`03-operations/` 说明如何运行；计划只安排未来工作；报告记录一次具体执行。
2. 当前测试数字只维护在最新验收报告，不复制到简介和导航。旧语料、哈希编码或不同部署的成绩不得沿用。
3. 历史报告归档后保留原结论，追加状态说明。移动文档须更新相对链接，运行 `python backend/scripts/check_docs.py`。
4. `backend/vendor_knowledge/` 是当前官方语料快照；`backend/demo_knowledge/` 是旧测试夹具；`backend/skills/` 是运行时提示约束。三者不为整理说明文档而移动。
5. `.env`、知识库、模型缓存、数据备份与验收证据不属于普通清理对象。源码归档位于 `backend/data/checkpoints/`，具体证据见验收报告。
