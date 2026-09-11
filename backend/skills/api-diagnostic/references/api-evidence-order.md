# API 诊断证据顺序

## 优先级

1. `request_id` 对应的 `query_call_log`：确认本次调用的 HTTP 状态、错误码、endpoint 和 app。
2. `query_api_key_status`：只在已有 app_id 且问题涉及 401/API Key 时使用。
3. `query_error_code`：解释标准错误码及建议动作。
4. `query_recent_call_stats`：只在已有 endpoint 且问题涉及 429、限流或 QPS 时使用。
5. `search_knowledge`：补充产品文档和公开配置规则，不能替代调用日志或账户状态。

有依赖关系时按顺序分轮；没有依赖关系的只读查询可以并行。
