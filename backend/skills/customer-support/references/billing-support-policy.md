# Billing Support Policy

- 套餐、QPS、月配额：使用 `query_plan` 查询当前客户真实数据。
- 月度调用量/超额量：使用 `query_usage`，不要从账单金额反推调用量。
- 账单金额/费用构成：使用 `query_bill`；需要解释计费规则时再并行 `search_knowledge`。
- `query_plan`、`query_usage`、`query_bill` 都是只读工具，没有数据依赖时应并行执行。
- 退款、调价、套餐变更、取消订阅属于高风险商业动作，本项目的 AI 只解释与采集上下文，必须进入 `escalation`，不能声称已经修改。
- 回答中出现的金额、配额、QPS、调用次数必须来自成功 Tool Result。
