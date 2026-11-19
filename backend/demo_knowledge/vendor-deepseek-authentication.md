# DeepSeek API：接入地址与兼容协议

厂商：DeepSeek。适用产品：DeepSeek 官方 API；本文不代表第三方代理的规则。
整理核对日期：2026-10-19。本文为官方公开文档的中文摘要，不是完整镜像。
官方来源：[首次调用 API](https://api-docs.deepseek.com/zh-cn/)。

## 两种兼容入口

官方说明支持 OpenAI 和 Anthropic 兼容格式。OpenAI 格式的基础地址是 `https://api.deepseek.com`；Anthropic 格式使用 `https://api.deepseek.com/anthropic`。选定 SDK 后应配置匹配的入口与协议，不能只修改模型名。

## 认证与模型配置

OpenAI 格式示例使用 Bearer Key，SDK 需读取 DeepSeek 的凭据并设置对应 base URL。模型名称与可用能力应从该厂商当前文档确认，不把其他厂商模型名称原样搬过来。协议兼容不意味着所有参数、错误码和限流规则完全一致。

## Demo 使用边界

本项目约定：先收集 SDK、base URL、厂商和脱敏错误响应；不要向客服发送完整 Key。本地业务工具不具备查询 DeepSeek 生产 Key 状态的能力。本文没有保存账户余额、实时配额或任何真实凭据，不能据此确认用户具体故障。
