# Anthropic Claude API：认证、版本与请求号

厂商：Anthropic。适用产品：Anthropic 官方直连 Claude API；云平台托管接口需要对应平台文档。
整理核对日期：2026-10-19。本文为中文摘要，不是官方全文镜像；快照日期不等于 API 版本。
官方来源：[API overview](https://platform.claude.com/docs/en/api/overview)。

## 请求与认证

官方直连地址为 `https://api.anthropic.com`，Messages 使用 `POST /v1/messages`。当前文档支持 `Authorization: Bearer <token>`；`x-api-key` 仍可作为支持的兼容方式。请求还需 `anthropic-version` 与内容类型信息，SDK 会处理其支持的必要头。

## 工作区与追踪

多工作区 Key 需选择相应工作区；不能仅更换模型名就假定授权范围相同。响应的 `request-id` 可供定位事件。云平台的 IAM 与官方直连认证需要分别核对。

## Demo 使用边界

本项目约定：文档只解释厂商接入，不代表已接入 Anthropic 账户查询。排查前先确认是官方直连、云平台还是第三方网关，再检查脱敏认证方式、版本头和请求号。不能据此断言用户 Key 当前有效；不要上传完整 Key 或未脱敏请求头。
