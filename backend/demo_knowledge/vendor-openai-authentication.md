# OpenAI API：认证与请求追踪

厂商：OpenAI。适用产品：OpenAI API 官方直连；不代表其他厂商或本地 Demo 的业务规则。
整理核对日期：2026-10-19。本文为官方公开资料的中文摘要，不是完整镜像；日期表示核对时间，不代表 API 规则生效时间。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。

## 认证方式

OpenAI API 支持 Bearer 凭据；API Key 应由服务端环境或密钥管理服务读取。不要把凭据放进浏览器代码、公开仓库或客服消息。部分组织与项目选择场景使用 `OpenAI-Organization`、`OpenAI-Project` 请求头，应按实际凭据和项目配置核对。

## 请求追踪

响应中的 `x-request-id` 用于定位具体请求；保存状态码、请求时间和脱敏配置有助于排障。客户端也可以显式设置 `X-Client-Request-Id` 关联自己的追踪记录；它不能替代凭据或授权。

## Demo 使用边界

以下为本项目的使用约定：这份文档仅支持认证和追踪规则解释，不能证明某个用户的 Key 有效或请求确实失败。本地 `query_call_log` 查询的是 Demo 数据，不是 OpenAI 的生产日志。要分析外部事件，需要用户提供厂商、时间、请求号、HTTP 状态和脱敏错误响应；不索取完整 Authorization。
