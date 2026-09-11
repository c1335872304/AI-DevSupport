# API 助手架构文档

> 状态：当前实现基线（2026-09-10）。
>
> 产品展示名称为 **API 助手**；代码包、Docker Compose 项目名、数据库名中仍可能保留 `PaiSmart`，它们是内部技术标识，不代表前端品牌。

## 1. 架构文档的唯一入口

| 文档 | 负责回答的问题 | 权威范围 |
|---|---|---|
| [CUSTOMER_SERVICE_ARCHITECTURE.md](CUSTOMER_SERVICE_ARCHITECTURE.md) | 客服 Agent、路由、Tool、证据、质量门和最终答复如何协作 | 客服运行时主架构 |
| [KNOWLEDGE_PIPELINE.md](KNOWLEDGE_PIPELINE.md) | 文档上传、父子 Chunk、Embedding、检索、权限和引用如何工作 | Knowledge/RAG |
| [ADMIN_TICKET_CONSOLE.md](ADMIN_TICKET_CONSOLE.md) | 工单创建边界、管理员页面、API、权限和脱敏 | SupportHandoff/管理员工单台 |
| [../03-operations/DOCKER_OPERATIONS.md](../03-operations/DOCKER_OPERATIONS.md) | 本地 Docker 如何启动、更新和验收 | 运行与部署 |
| [../03-operations/PRODUCTION.md](../03-operations/PRODUCTION.md) | 哪些能力仍属于生产化规划 | 生产边界 |

测试计划和测试结果保留在 `docs/04-testing/` 与 `docs/05-live-tests/`，不在架构文档中重复维护测试数字。测试结果以对应报告为准。

## 2. 当前系统边界

```text
浏览器 :9527
  → frontend（API 助手管理台 / 客服界面）
  → api :8000（FastAPI + WebSocket + LangGraph 目标工作流）
       → RoutingPolicy
       → 专业 Agent 规划
       → Shared Scheduler / Tool Runtime
       → Evidence Summary / Handoff / Answer / Safety
       → MySQL / Redis / MinIO / Elasticsearch / Kafka
       → billing-mcp:8011（仅 Billing 只读 MCP，Compose 内部可见）
```

系统有三个专业事实 Agent：

- `api_diagnostic`：API 日志、鉴权、错误码、限流和接口诊断；
- `billing`：套餐、用量、账单和退款相关的只读业务核验；
- `knowledge`：政策、FAQ、产品说明、错误码释义和通用排障文档。

`customer-support` 和 `escalation` 是后置共享 Skill，不是额外的专业 Agent。只有 `create_support_handoff` 成功返回真实 `handoffId`，系统才允许向客户确认工单已经创建。

## 3. 必须保持的架构决策

1. `RoutingPolicy` 是唯一的 Agent 选择器，LLM 不能改写路由、风险等级和人工条件。
2. 专业 Agent 只规划自己 Skill 声明的 Tool，不执行 Tool、不创建工单、不直接生成客户最终答复。
3. 所有事实必须经过 `AgentEvidence` 和 `Evidence Summary`，再进入人工决策和答复生成。
4. 知识库只能支持通用规则，不能证明客户个人的账单、订单、用量、Key 或 API 请求事实。
5. 质量门是确定性审计和内容过滤层，不调用 LLM，不编造新事实；它只能放行、删除无事实依据的主张，或发送受控安全说明。
6. Billing 是唯一允许接入 MCP 的领域，MCP 服务只提供只读 Tool，个人身份由服务端上下文注入。
7. 管理员工单台不是新的工单创建渠道，管理员处理说明不自动暴露给客户。

## 4. 代码映射

| 领域 | 主要实现 |
|---|---|
| 工作流 | `backend/app/agent/graph/workflow.py` |
| 路由与实体 | `backend/app/agent/routing_policy.py`、`backend/app/agent/entities.py` |
| 专业 Agent | `backend/app/agent/target_agents.py`、`backend/app/agent/agent_skill_policy.py` |
| 证据汇总 | `backend/app/agent/evidence.py`、`backend/app/agent/types.py` |
| 调度与 Tool Runtime | `backend/app/agent/shared_scheduler.py`、`backend/app/tools/` |
| Skill 与质量门 | `backend/skills/**/SKILL.md`、`backend/skills/**/scripts/` |
| RAG | `backend/app/knowledge/`、`backend/app/documents/` |
| 工单 API | `backend/app/api/v1/support.py`、`backend/app/support/handoff.py` |
| 管理员工单台 | `frontend/src/views/support-handoff/index.vue` |
| 前端品牌 | `frontend/src/locales/`、`frontend/src/layouts/modules/global-logo/` |

## 5. 架构变更与测试的关系

架构改动必须补充对应测试计划或报告中的用例，不删除历史测试记录：

- Agent、证据、质量门：见 [PROJECT_E2E_TEST_PLAN.md](../04-testing/PROJECT_E2E_TEST_PLAN.md) 和 [QUALITY_GATE_REDESIGN_2026-09-09.md](../04-testing/QUALITY_GATE_REDESIGN_2026-09-09.md)；
- RAG：见 [RAG_ADVANCED_TEST_PLAN.md](../04-testing/RAG_ADVANCED_TEST_PLAN.md) 和 [RAG_BLIND_TEST_REPORT.md](../04-testing/RAG_BLIND_TEST_REPORT.md)；
- 工单台：见 [ADMIN_TICKET_CONSOLE_TEST_PLAN.md](../04-testing/ADMIN_TICKET_CONSOLE_TEST_PLAN.md) 和 [ADMIN_TICKET_CONSOLE_TEST_REPORT.md](../04-testing/ADMIN_TICKET_CONSOLE_TEST_REPORT.md)；
- 真实模型和网络：见 `docs/05-live-tests/` 与 [NETWORK_TROUBLESHOOTING.md](../03-operations/NETWORK_TROUBLESHOOTING.md)。

