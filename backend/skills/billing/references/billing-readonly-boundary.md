# 计费只读边界

- 本地模式下：套餐和配额使用 `query_plan`，月度调用量使用 `query_usage`，账单、扣费和发票使用 `query_bill`。
- Billing MCP 模式下：只能使用本轮 MCP `list_tools` 返回、并由运行时标记为 `mcp__billing__*` 的只读 Tool；Tool 的实时 JSON Schema 是参数唯一来源。
- 这些 Tool 只能核实当前权限范围内的数据，不能替代退款审批或合同变更。
- 没有 SUCCESS 结果时，只能说明目前无法核实。
