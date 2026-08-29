# API 认证与 API Key 管理

PaiSmart OpenAPI Demo 使用 API Key 进行认证。本文档描述通用认证规则；某个客户当前 Key 是否有效，必须通过 `query_api_key_status` 查询真实业务数据。

## 1. 常见 401 原因

### AUTH_KEY_EXPIRED

表示调用使用的 API Key 已经过期。处理方式：确认应用身份，创建或轮换一个仍在有效期内的 Key，并更新服务端或客户端配置后重新调用。

### AUTH_KEY_INVALID

表示 API Key 无效、被禁用、格式错误，或并不属于当前应用。处理方式：确认使用了正确应用对应的有效 Key；不要仅凭旧日志继续重复请求。

## 2. 安全要求

- 不要在聊天、工单描述或日志截图中发送完整 API Key。
- 客服只应请求 `request_id`、`app_id` 或脱敏 Key 标识。
- 轮换 Key 后，应先在低风险请求上验证，再逐步切换流量。
- 如果怀疑 Key 泄露，应立即停用旧 Key 并创建新 Key，而不是仅修改客户端代码。

## 3. 诊断顺序

当客户提供 `request_id` 且请求返回 401 时，推荐顺序：

1. 用 `query_call_log` 查询该请求对应的 `app_id`、HTTP 状态和错误码；
2. 用 `query_api_key_status` 检查 Key 是否 ACTIVE、EXPIRED 或 DISABLED；
3. 用 `query_error_code` 获取错误码的标准原因与修复步骤；
4. 若仍无法确认，整理上下文并转人工，而不是猜测账户状态。
