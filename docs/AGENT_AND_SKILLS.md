# AI 客服 Agent、Skill、Tool 与 MCP

## 1. 概念分层

```text
Agent      = 决定下一步客服动作
Skill      = 一类客服问题应该遵循的工作方法
Reference  = Skill 按需读取的客服规范
Script     = 受控、确定性的分类/规划/质量检查
Tool       = LLM 可以调用的真实能力
MCP        = 外部业务 Tool 的标准发现/调用协议
Runtime    = 参数校验、权限、并行、超时、错误和 Trace
```

Skill 不直接拥有数据库权限；Tool 也不负责决定客服策略。

## 2. LangGraph Agent Workflow

主执行入口位于 `app/agent/graph/workflow.py`，使用 `StateGraph(CustomerServiceState)`：

```text
START
  ↓
load_context
  ↓
skill_route
  ↓
agent_decide
  ├─ final answer ───────────────→ safety → emit_final → persist_trace → END
  ├─ N normal tool_calls ────────→ execute_tools ─┐
  ├─ handoff tool_call ──────────→ handoff ───────┤
  └─ max steps ─────────────────→ force_finalize │
                                                  ↓
                                             agent_decide
```

LangGraph 负责共享状态和条件边；`app/agent/runtime.py` 不再持有主 `for step` Agent Loop，而是提供 Tool Schema 选择和并行执行能力。

同一轮多个无依赖 Tool Call 在 `execute_tools` 节点内并行；如果下一工具依赖前一结果，模型在下一次 `agent_decide` 中生成新的 Tool Call，因此形成动态 DAG。`AGENT_MAX_STEPS` 防止循环失控，`AGENT_MAX_PARALLEL_TOOLS` 控制并发宽度。

## 3. 三个客服 Skill

### customer-support：默认客服应答

任何正常客服请求都会激活。它负责：

```text
理解诉求
 -> 判断通用知识还是个人账户事实
 -> 必要时查客服知识库
 -> 给直接答案
 -> 给最有效下一步
 -> 判断是否需要 specialist
```

重要规则：

- 政策、FAQ、产品说明通过 `search_knowledge` 查证。
- 订单、支付、账户、退款到账等个人事实只能由真实业务 Tool/MCP 验证。
- 没有验证能力时明确说明边界，不能猜。
- 普通寒暄不为了“展示 Agent”而滥用 Tool。

它使用：

```text
references/service-response-policy.md
references/account-data-boundary.md
references/knowledge-policy.md
scripts/classify_support_intent.py
scripts/audit_support_answer.py
```

### troubleshooting：故障排查 specialist

在登录、上传、支付、网络、验证码、页面/功能异常等场景叠加：

```text
extract symptom
 -> classify_failure
 -> search current troubleshooting knowledge
 -> build 1–4 step diagnostic plan
 -> avoid unsafe/destructive action
 -> audit
 -> solved or escalate
```

它的目标不是“列十个可能原因”，而是让客户以最少轮次走到下一条有信息增益的诊断步骤。

### escalation：人工升级 specialist

在以下场景叠加：

```text
客户明确要求人工
投诉 / 争议
重复排障失败
支付/账户问题需要人工权限
关键事实无法安全验证
```

执行：

```text
assess_escalation
 -> build_handoff_summary
 -> create_support_handoff
 -> audit_handoff
```

`create_support_handoff` 是真实 DB 写操作。模型只能在 Tool 成功返回 `handoffId` 后说“已经创建工单”。

## 4. Skill 路由

路由分为两层：

```text
customer-support
= default_active，默认客服基线

troubleshooting / escalation
= Trigger + Negative Trigger + Priority 的 specialist
```

示例：

```text
“会员退款规则？”
 -> customer-support

“登录报错 E401”
 -> customer-support + troubleshooting

“别排查了，给我转人工”
 -> customer-support + escalation
```

LLM 仍可通过 `activate_skill` 动态激活 specialist，但 Tool 权限最终由 Runtime 决定。系统保持“默认客服 + 一个 specialist”的简洁组合；如果排障过程中需要转人工，更高优先级的 `escalation` 会替换 `troubleshooting`，而不是因为 Skill 数量上限阻止人工升级。

## 5. Reference 与 Script 的渐进披露

Agent 一开始只接收选中 Skill 的工作流和资源清单，不把全部 reference 塞进上下文。

```text
selected Skill
   ↓
SKILL.md
   ↓
LLM decides reference is needed
   ↓
read_skill_reference
   ↓
active-skill / allowlist / path validation
```

Script 通过 `run_skill_script` 执行固定仓库代码，不允许 LLM 生成任意 shell/python 命令。

## 6. Tool Runtime

ToolRegistry 会统一处理：

```text
JSON Schema Validation
Authentication / User Context
Role / Scope Policy
Risk Metadata
Timeout
Parallel Safety
Resource Conflict
Partial Failure
Durable Trace
```

当前客服关键 Tool：

```text
search_knowledge
create_support_handoff
get_support_handoff
activate_skill
read_skill_reference
run_skill_script
```

`list_documents/get_document` 仍作为知识管理能力存在，但不再代表核心客服 Skill。

## 7. 并行 Tool

同一轮无依赖查询继续并行。例如接入业务 MCP 后：

```text
search_knowledge(refund policy) ─┐
get_payment(payment id) ─────────┼─ concurrent
get_refund(refund id) ───────────┘
```

写操作、存在资源冲突的 Tool 或依赖前序结果的 Tool 不会被无脑并发。

## 8. MCP 在客服里的定位

### PaiSmart 作为 MCP Client

这是客服业务最重要的 MCP 方向：

```text
PaiSmart Agent
   ↓
MCP Client Adapter
   ├── Order MCP
   ├── Payment MCP
   ├── Account MCP
   ├── Logistics MCP
   └── CRM MCP
```

这些 Tool 用于获取**客户特定事实**，弥补 RAG 不能查询实时账户状态的边界。

远程 MCP Tool 动态注册进同一个 ToolRegistry，所以仍使用统一的 validation、scope、timeout、parallel execution 和 trace。

#### Stable Business MCP Adapter

API 诊断和 Billing 使用稳定的 Agent-facing Tool 名，例如 `query_call_log / query_plan / query_bill`。开发环境默认查询 PaiSmart Demo DB；生产可以配置 `BUSINESS_TOOL_BACKEND=mcp`，由 Adapter 把同一个调用转发到指定 Business MCP Server。

```text
LangGraph / Skill
    ↓
query_bill(month)        # Tool contract 不变
    ↓
Business MCP Adapter
    ↓
remote get_invoice(customer_id, month)
```

因此业务系统替换、Tool 重命名或服务拆分不会迫使 Agent Prompt/Skill/Eval 跟着修改。

### PaiSmart 作为 MCP Server

PaiSmart 也可以把安全的自身 Tool 暴露给外部 MCP Client。stdio 使用显式 service principal；Streamable HTTP 使用 Bearer Token 映射真实 PaiSmart 用户和 scopes。

客服写操作不会因为“是 MCP”就绕过 Runtime 权限。

## 9. 新增客服能力的原则

新增能力时按这个顺序：

```text
真实业务逻辑
 -> 明确领域模块（support / knowledge / ...）
 -> 薄 Tool Adapter
 -> 严格 Schema + 权限 + risk metadata
 -> ToolRegistry
 -> 对应 Skill allowlist（如果需要）
 -> behavior / answer eval
```

不要为了展示 Agent 新增一个没有真实业务能力支撑的 Skill。


## API 技术支持能力

`troubleshooting` 不只是通用排障 Prompt。对 API 平台客户，它可以调用真实诊断 Tool：

```text
query_call_log(request_id)
query_api_key_status(app_id / api_key_id)
query_recent_call_stats(endpoint, minutes)
query_error_code(code)
search_knowledge(query)
```

如果只有 `request_id`，先读取日志，再根据返回的 `appId / errorCode / endpoint` 执行下一轮依赖查询；如果这些参数用户已经全部给出，则 Key 状态、429 统计、错误码说明与文档检索可以同轮并行。

## Billing 客服能力

`customer-support` 可直接读取当前登录客户的：

```text
query_plan   当前套餐 / QPS / 月配额 / 超额单价
query_usage  指定月份 API 调用量 / 超额量
query_bill   指定月份账单金额 / 费用构成
```

三者均为只读 Tool，参数已知时可以并行。涉及退款、调价、套餐变更、退订等高风险写操作时不会自动执行，而是切换 `escalation` 创建人工工单。
