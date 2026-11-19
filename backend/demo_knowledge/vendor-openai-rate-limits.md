# OpenAI API：限流维度与重试

厂商：OpenAI。适用产品：OpenAI API 官方直连。
整理核对日期：2026-10-19。本文为公开文档摘要；具体账户限额应查询官方控制台，不在知识库中固定。
官方来源：[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)。

## 限额维度

请求数和 Tokens 等维度可分别触发限制，低请求量也可能耗尽 Tokens 预算。响应可携带 `x-ratelimit-remaining-requests`、`x-ratelimit-remaining-tokens` 及对应 reset 信息。不能把某个示例上限认定为所有用户的实时额度。

## 临时限流恢复

存在 `Retry-After` 时至少等待其要求的时间，再加入随机抖动；否则采用有上限的指数退避。减少突发流量与并发，逐步恢复。失败请求也可能消耗速率预算，因此无限重试会恶化问题。

## 避免重试放大

SDK 和业务代码各自重试可能叠加，应统一次数与总时限。余额、支出或用量上限需要用户处理，不能套用临时限流的恢复策略。

## Demo 使用边界

本项目约定：文档描述限制维度和恢复原则，不证明当前用户触发了哪项限制；需要结合该次响应和账户信息。此文不沿用本地 Professional 示例套餐的 50 QPS。
