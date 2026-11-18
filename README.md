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

## 交付与文档

当前源码候选已完成会话隔离、多副本生成恢复与结算、审批接手续办修复，验证范围见[源码候选验收](docs/04-testing/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。退款与关闭工单通过独立管理员审批入口处理，退款执行使用合成支付沙箱。

- [项目简介](docs/PROJECT_INTRO.md) · [架构与代码地图](docs/02-architecture/README.md) · [上下文系统](docs/02-architecture/CONTEXT_SYSTEM.md)
- [本地启动](docs/01-getting-started/GETTING_STARTED.md) · [Docker 操作](docs/03-operations/DOCKER_OPERATIONS.md) · [RAG 运维](docs/03-operations/RAG_OPERATIONS.md)
- [Git 与 PR](docs/03-operations/GIT_AND_FAST_CI.md) · [CI 门禁](docs/03-operations/CI_PLAN.md) · [预发布签验](docs/03-operations/CONTEXT_STAGING_ACCEPTANCE_RUNBOOK.md)
- [技术债务](docs/MAINTENANCE.md) · [完整文档导航](docs/README.md)

四阶段核心交付与 2026-10-20 的 Docker、官方知识库、回答质量和流式验收保留在文档索引中。现行 PDF/DOCX 解析使用独立 Docling 环境，扫描 OCR 与截图输入由后续范围跟踪。各报告的模型、镜像和语料结果适用于各自执行条件。
