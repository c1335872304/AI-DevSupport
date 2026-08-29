# API Diagnostic Playbook

## Evidence priority
1. `query_call_log(request_id)`：真实单次调用证据。
2. `query_api_key_status(app_id/api_key_id)`：401 鉴权问题。
3. `query_recent_call_stats(endpoint)`：429/限流趋势。
4. `query_error_code(code)`：平台标准错误码的确定性解释。
5. `search_knowledge`：补充公开 API 文档与操作说明。

## Dependency rule
- 如果只有 request_id，先查调用日志；日志返回 appId/errorCode/endpoint 后再执行依赖这些参数的工具。
- 如果用户已经直接给出 app_id + error_code + endpoint，则 Key 状态、限流统计、错误码解释与文档检索没有数据依赖，应并行。

## Safety
- 不输出完整 API Key；只能展示工具返回的脱敏 Key。
- 不把“可能原因”说成已证实根因。
- 查不到 request_id 或证据互相冲突时，减少结论强度并考虑人工升级。
