# OpenAPI 常见错误码

本页是 Demo 客服知识库中的错误码速查。对于具体请求，应优先结合 `request_id` 查询真实调用日志。

## AUTH_KEY_EXPIRED

- HTTP：401
- 含义：API Key 已经过期。
- 常见原因：应用仍在使用已过有效期的旧 Key。
- 建议：通过 `query_api_key_status` 确认 Key 状态，轮换为有效 Key 后再请求。

## AUTH_KEY_INVALID

- HTTP：401
- 含义：API Key 无效或不可用于当前应用。
- 常见原因：Key 被禁用、复制错误、使用了其他应用的 Key。
- 建议：确认 app 与 Key 的对应关系，并使用 ACTIVE Key。

## RATE_LIMIT_EXCEEDED

- HTTP：429
- 含义：请求速率超过套餐允许的 QPS。
- 常见原因：客户端瞬时并发或突发流量过高。
- 建议：查询近期请求统计和套餐 QPS；采用指数退避与并发控制。如确需提升限额，应走套餐升级或人工支持流程。

## 5xx 与未知错误码

如果出现本文档未列出的错误码或服务端 5xx，请提供 `request_id`。客服应先查调用日志，再结合知识库和业务监控判断；证据不足时不要编造根因。
