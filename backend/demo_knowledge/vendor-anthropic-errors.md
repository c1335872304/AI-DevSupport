# Anthropic Claude API：错误类型与流式失败

厂商：Anthropic。适用产品：官方直连 Claude API。
整理核对日期：2026-10-19。本文为官方资料中文摘要，非完整镜像。
官方来源：[Claude API errors](https://platform.claude.com/docs/en/api/errors)。

## 常见错误

- 401 `authentication_error`：认证信息有问题，需要核对凭据。
- 403 `permission_error`：资源访问授权不满足。
- 429 `rate_limit_error`：可能涉及速率或相关使用上限，需要继续检查错误详情。
- 500 `api_error`：服务内部异常。
- 504 `timeout_error`：处理超时。
- 529 `overloaded_error`：API 暂时过载。

## 证据与流式响应

错误响应包含错误类型、消息与请求追踪信息。流式请求即使已收到 HTTP 200，后续 SSE 中仍可能出现错误，因此不能把“收到 200”直接当成完整生成成功。

## 重试与 Demo 边界

临时故障可以按 SDK 配置和服务端提示有限重试。以下为本项目约定：诊断需保存脱敏错误详情与流式终止状态；不能仅凭 429 断言瞬时速率超限，也不能把本地日志当成 Anthropic 生产核查结果。此文中的 529 含义不外推为所有厂商通用约定。
