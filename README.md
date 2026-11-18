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
- 文档和查询统一使用千问 `text-embedding-v4`；建库/检索必须配置 Embedding Key。已移除本地哈希向量和自动降级，仅对子块编码，父块不重复编码。
- 只有 Billing 接入 MCP；Billing Agent 通过本地 Compose `billing-mcp` 服务动态发现只读 Tool。
- API 诊断和 Knowledge 使用本地受控 Tool，不通过通用业务 MCP。

回答采用实时分段流式：供应商增量到达后，以完整短句或完整代码块为单位执行确定性质量检查，通过后立即经 WebSocket 推送。生成结束后仍进行整篇审计；最终内容发生变化时发送替换事件，完成事件携带权威正文以校准页面。质量门不调用 LLM 重新编写事实。实测与边界见[流式输出验收](docs/04-testing/LIVE_STREAMING_ACCEPTANCE_2026-10-20.md)。

## 文档

- [项目简介](docs/PROJECT_INTRO.md) · [架构与代码地图](docs/02-architecture/README.md)
- [本地启动](docs/01-getting-started/GETTING_STARTED.md) · [RAG 操作手册](docs/03-operations/RAG_OPERATIONS.md) · [Langfuse 链路追踪](docs/03-operations/LANGFUSE.md)
- [最终验收](docs/04-testing/FINAL_PROJECT_ACCEPTANCE.md) · [第三阶段验收](docs/04-testing/DIAGNOSIS_LOOP_ACCEPTANCE.md) · [第二阶段验收](docs/04-testing/DIAGNOSIS_STATE_ACCEPTANCE.md) · [第一阶段验收](docs/04-testing/RAG_PHASE_ONE_ACCEPTANCE.md) · [四阶段计划](docs/FOUR_PHASE_ITERATION_PLAN.md)
- [完整文档导航](docs/README.md) · [整理记录与剩余债务](docs/MAINTENANCE.md)

当前源码已完成四阶段核心迭代：可靠RAG、诊断状态、诊断闭环与恢复、分层评测及交付。2026-10-20 已更新 Docker Demo 并保留原知识库和配置，镜像包含独立 CPU Docling 环境，见 [Docker升级验收](docs/04-testing/DOCKER_DEMO_UPGRADE_2026-10-20.md)。截图输入、扫描 OCR 尚未纳入。测试结果统一见最新验收报告，历史材料从文档导航进入。

后续已按要求将Docker旧知识替换为DeepSeek、Qwen、GPT各20份官方正文，并复用5888条本地千问向量，配置保持不变；见[官方知识库迁移验收与限制](docs/04-testing/DOCKER_VENDOR_KNOWLEDGE_MIGRATION_2026-10-20.md)。

厂商召回与账单安全门不一致已修复并更新Docker，新增回归、检索对照及数据保护证据见[最新修复验收](docs/04-testing/VENDOR_SCOPE_AND_BILLING_GATE_FIX_2026-10-20.md)。
