# API 助手

API 助手是面向企业场景的 AI 客服系统。当前运行时只有一条目标架构路径：确定性路由选择专业 Agent，Agent 独立找事实，统一汇总证据后再决定是否转人工。

> 说明：`PaiSmart` 仍可能出现在代码包、Docker Compose 项目名和数据库名中，属于内部技术标识；产品前端品牌统一为“API 助手”。

## 当前架构

```text
Customer → FastAPI / WebSocket → LangGraph
  → load_context → extract_entities → routing_policy
  → 最多 3 个并发 LLM 专业 Agent
  → Shared Scheduler / Tool Runtime
  → Evidence Summary → Handoff Decision → Customer Response
  → Safety / Evidence Quality Gate → Trace
```

三个专业 Agent：

- `api_diagnostic`：API 日志、鉴权、限流和错误码诊断。
- `billing`：套餐、用量和账单的只读核实。
- `knowledge`：政策、FAQ、产品说明和通用故障指引。

`RoutingPolicy` 是唯一的 Agent 选择器。Agent 彼此独立，不直接回复客户或创建工单；最终证据汇总后才允许进入人工转接节点。

质量门是确定性“主张—证据—范围”验证层：文档和错误码释义只能支持通用说明，只有当前用户的业务 Tool 结果才能支持个人事实。它只过滤无依据内容或阻断不安全答复，不重写出新的“已核验”结论。

## RAG 与 MCP

- Knowledge RAG 使用父子切分：子块召回，父块补充上下文。
- 只有 Billing 接入 MCP；Billing Agent 通过本地 Compose `billing-mcp` 服务动态发现只读 Tool。
- API 诊断和 Knowledge 使用本地受控 Tool，不通过通用业务 MCP。

质量门位于最终答复生成之后、向客户端发送之前：它基于结构化证据审计回答，删除无事实依据的主张或发送受控安全说明，不调用 LLM 重新编写事实。

## 文档

- 入门与运维：[本地启动](docs/01-getting-started/GETTING_STARTED.md)、[Docker 操作](docs/03-operations/DOCKER_OPERATIONS.md)
- 架构与实现：[架构总览](docs/02-architecture/README.md)、[客服 Agent 架构](docs/02-architecture/CUSTOMER_SERVICE_ARCHITECTURE.md)、[知识库与 RAG](docs/02-architecture/KNOWLEDGE_PIPELINE.md)、[管理员工单台](docs/02-architecture/ADMIN_TICKET_CONSOLE.md)、[评测规范](docs/04-testing/EVALUATION.md)
- 测试结果：[完整 E2E 方案](docs/04-testing/PROJECT_E2E_TEST_PLAN.md)、[完整 E2E 执行报告](docs/04-testing/PROJECT_E2E_TEST_REPORT.md)、[E2E 修复计划](docs/04-testing/PROJECT_E2E_REMEDIATION_PLAN.md)、[E2E 修复复验](docs/04-testing/PROJECT_E2E_REMEDIATION_REPORT.md)、[用户问题模拟库](docs/04-testing/USER_QUESTION_SIMULATION.md)、[RAG 盲测报告](docs/04-testing/RAG_BLIND_TEST_REPORT.md)、[真实模型测试记录](docs/05-live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)
- 本轮复验与网络排障：[项目复验报告](docs/04-testing/PROJECT_TEST_REPORT_2026-09-09.md)、[网络/代理/Provider 排障](docs/03-operations/NETWORK_TROUBLESHOOTING.md)
- 工程规划：[生产边界](docs/03-operations/PRODUCTION.md)、[CI 计划](docs/03-operations/CI_PLAN.md)

完整导航、阅读路线以及 Demo 知识库 / Skill 文档边界见 [docs/README.md](docs/README.md)。
