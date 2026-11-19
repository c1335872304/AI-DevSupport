# Anthropic Claude API：速率与支出上限

厂商：Anthropic。适用产品：官方直连 Claude API，具体规则受组织、工作区与接口影响。
整理核对日期：2026-10-19。本文为中文摘要，不固定套餐限额；以官方当前说明和账户配置为准。
官方来源：[Rate limits](https://platform.claude.com/docs/en/api/rate-limits)。

## 速率维度

Messages 的限制包括 RPM、输入 Tokens 每分钟 ITPM、输出 Tokens 每分钟 OTPM。组织限制与工作区配置需要一起考虑。响应可以提供 `anthropic-ratelimit-*` 信息；带有 `retry-after` 时按其等待后再尝试。

## 支出限制不能一概当作临时限流

当前文档区分层级支出上限和用户设置的支出上限：前者可能返回没有 `retry-after` 的 429；用户配置的支出限制可返回 400。Claude Code 工作区还有特定差异。需要结合接口、错误详情与账户配置判断，不能仅按状态码给出统一答案。

## Demo 使用边界

本项目约定：知识库不证明用户的使用层级、剩余额度或恢复时间。问答应先确认具体入口和错误信息；不要将其他厂商的 TPM 定义、余额状态码或本地 Demo 套餐套用于此处。
