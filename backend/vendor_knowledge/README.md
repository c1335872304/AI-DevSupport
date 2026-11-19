# DeepSeek、Qwen、GPT 官方正文资料集

采集核对日期：2026-10-19。仅选择这三家服务的官方接入、功能指南与 API 参数正文；不是全站镜像，也不是简短摘要。

GPT 指 OpenAI API 文档，Qwen 指阿里云百炼托管 API，DeepSeek 指官方 API；DeepSeek 的 Anthropic 兼容协议仍属于 DeepSeek 资料，不代表收录第四家服务。

## 实际规模

| 服务 | 文档数 | 正文字符数 |
| --- | ---: | ---: |
| DeepSeek | 20 | 89,969 |
| Qwen / 百炼 | 20 | 1,532,258 |
| GPT / OpenAI | 20 | 820,086 |

合计 60 篇，2,442,313 个正文字符；字符数包含代码、表格和空白，不等同于汉字数或 Tokens。

## 文件说明

- `manifest.json`：实际导入清单，包含正文/原始响应校验和、来源与产品范围。
- `sources.json`：人工选择的官方 URL，可用采集脚本重新核对。
- `raw/`：原始 Markdown 或 HTML 响应，保留采集依据；导入只使用清单中的已整理 Markdown，避免重复建库。
- `collection-report.json`：采集数量、字符数和失败记录。
- 同目录正文 Markdown：OpenAI、Qwen 使用官方原生 Markdown；DeepSeek 将文档 article 转为 Markdown，移除导航，保留可提取标题、表格和代码。
- 首部来源与范围说明由本项目添加，下面正文来自官方；没有把采集日期当作规则生效日。

## 导入与校验

在 `backend/` 下执行：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --validate-only
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --username admin --private
```

实际导入使用当前应用数据库与 Embedding 配置；先核对目标环境，远端 Embedding 可能产生费用。原有 Demo 与上一批 9 份摘要为独立清单，本清单不包含 Anthropic 服务摘要。

## 主题与正文入口

| 文档 | 官方原文 | 正文字符数 |
| --- | --- | ---: |
| [GPT / OpenAI API：接入认证与请求追踪](gpt-overview.md) | [来源](https://developers.openai.com/api/reference/overview) | 8,257 |
| [GPT / OpenAI API：快速开始](gpt-quickstart.md) | [来源](https://developers.openai.com/api/docs/quickstart) | 54,811 |
| [GPT / OpenAI API：文本生成](gpt-text.md) | [来源](https://developers.openai.com/api/docs/guides/text) | 19,253 |
| [GPT / OpenAI API：多轮会话状态](gpt-conversation-state.md) | [来源](https://developers.openai.com/api/docs/guides/conversation-state) | 24,941 |
| [GPT / OpenAI API：流式响应](gpt-streaming.md) | [来源](https://developers.openai.com/api/docs/guides/streaming-responses) | 7,108 |
| [GPT / OpenAI API：工具调用](gpt-function-calling.md) | [来源](https://developers.openai.com/api/docs/guides/function-calling) | 77,540 |
| [GPT / OpenAI API：结构化输出](gpt-structured-outputs.md) | [来源](https://developers.openai.com/api/docs/guides/structured-outputs) | 136,308 |
| [GPT / OpenAI API：推理模型](gpt-reasoning.md) | [来源](https://developers.openai.com/api/docs/guides/reasoning) | 70,761 |
| [GPT / OpenAI API：推理最佳实践](gpt-reasoning-practices.md) | [来源](https://developers.openai.com/api/docs/guides/reasoning-best-practices) | 17,069 |
| [GPT / OpenAI API：提示工程](gpt-prompt-engineering.md) | [来源](https://developers.openai.com/api/docs/guides/prompt-engineering) | 37,398 |
| [GPT / OpenAI API：提示缓存](gpt-prompt-caching.md) | [来源](https://developers.openai.com/api/docs/guides/prompt-caching) | 48,144 |
| [GPT / OpenAI API：文本向量](gpt-embeddings.md) | [来源](https://developers.openai.com/api/docs/guides/embeddings) | 58,091 |
| [GPT / OpenAI API：检索](gpt-retrieval.md) | [来源](https://developers.openai.com/api/docs/guides/retrieval) | 56,467 |
| [GPT / OpenAI API：文件搜索](gpt-file-search.md) | [来源](https://developers.openai.com/api/docs/guides/tools-file-search) | 28,111 |
| [GPT / OpenAI API：错误码](gpt-errors.md) | [来源](https://developers.openai.com/api/docs/guides/error-codes) | 32,170 |
| [GPT / OpenAI API：速率限制](gpt-rate-limits.md) | [来源](https://developers.openai.com/api/docs/guides/rate-limits) | 22,734 |
| [GPT / OpenAI API：批量请求](gpt-batch.md) | [来源](https://developers.openai.com/api/docs/guides/batch) | 21,469 |
| [GPT / OpenAI API：后台执行](gpt-background.md) | [来源](https://developers.openai.com/api/docs/guides/background) | 19,988 |
| [GPT / OpenAI API：Webhook 回调](gpt-webhooks.md) | [来源](https://developers.openai.com/api/docs/guides/webhooks) | 16,426 |
| [GPT / OpenAI API：Responses 迁移](gpt-responses-migration.md) | [来源](https://developers.openai.com/api/docs/guides/migrate-to-responses) | 63,040 |
| [Qwen / 阿里云百炼：首次调用](qwen-quickstart.md) | [来源](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen) | 42,389 |
| [Qwen / 阿里云百炼：获取 API Key](qwen-api-key.md) | [来源](https://help.aliyun.com/zh/model-studio/get-api-key) | 10,845 |
| [Qwen / 阿里云百炼：批量推理](qwen-batch.md) | [来源](https://help.aliyun.com/zh/model-studio/batch-interfaces-compatible-with-openai) | 102,399 |
| [Qwen / 阿里云百炼：安装 SDK](qwen-sdk.md) | [来源](https://help.aliyun.com/zh/model-studio/install-sdk) | 4,255 |
| [Qwen / 阿里云百炼：接入地址](qwen-base-url.md) | [来源](https://help.aliyun.com/zh/model-studio/base-url) | 7,700 |
| [Qwen / 阿里云百炼：地域说明](qwen-regions.md) | [来源](https://help.aliyun.com/zh/model-studio/regions) | 16,384 |
| [Qwen / 阿里云百炼：Chat Completions 参数](qwen-chat-completions.md) | [来源](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions) | 103,745 |
| [Qwen / 阿里云百炼：DashScope 参数](qwen-dashscope.md) | [来源](https://help.aliyun.com/zh/model-studio/qwen-api-via-dashscope) | 124,344 |
| [Qwen / 阿里云百炼：Responses 参数](qwen-responses.md) | [来源](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses) | 92,787 |
| [Qwen / 阿里云百炼：流式输出](qwen-streaming.md) | [来源](https://help.aliyun.com/zh/model-studio/stream) | 56,170 |
| [Qwen / 阿里云百炼：Function Calling](qwen-function-calling.md) | [来源](https://help.aliyun.com/zh/model-studio/qwen-function-calling) | 165,025 |
| [Qwen / 阿里云百炼：结构化输出](qwen-structured-outputs.md) | [来源](https://help.aliyun.com/zh/model-studio/qwen-structured-output) | 80,337 |
| [Qwen / 阿里云百炼：深度思考](qwen-thinking.md) | [来源](https://help.aliyun.com/zh/model-studio/deep-thinking) | 96,439 |
| [Qwen / 阿里云百炼：多轮对话](qwen-multi-round.md) | [来源](https://help.aliyun.com/zh/model-studio/multi-round-conversation) | 46,647 |
| [Qwen / 阿里云百炼：上下文缓存](qwen-context-cache.md) | [来源](https://help.aliyun.com/zh/model-studio/context-cache) | 49,957 |
| [Qwen / 阿里云百炼：向量接口](qwen-embedding-api.md) | [来源](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api) | 47,559 |
| [Qwen / 阿里云百炼：text-embedding-v4](qwen-embedding-v4.md) | [来源](https://help.aliyun.com/zh/model-studio/text-embedding-v4) | 5,858 |
| [Qwen / 阿里云百炼：限流](qwen-rate-limits.md) | [来源](https://help.aliyun.com/zh/model-studio/rate-limit) | 349,893 |
| [Qwen / 阿里云百炼：错误码](qwen-errors.md) | [来源](https://help.aliyun.com/zh/model-studio/error-code) | 99,518 |
| [Qwen / 阿里云百炼：提示工程](qwen-prompt-engineering.md) | [来源](https://help.aliyun.com/zh/model-studio/prompt-engineering-guide) | 30,007 |
| [DeepSeek API：首次调用](deepseek-quickstart.md) | [来源](https://api-docs.deepseek.com/zh-cn/) | 2,704 |
| [DeepSeek API：错误码](deepseek-errors.md) | [来源](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/) | 502 |
| [DeepSeek API：限速与隔离](deepseek-rate-limits.md) | [来源](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit/) | 2,061 |
| [DeepSeek API：Token 用量](deepseek-token-usage.md) | [来源](https://api-docs.deepseek.com/zh-cn/quick_start/token_usage/) | 657 |
| [DeepSeek API：模型与价格](deepseek-models-pricing.md) | [来源](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) | 1,911 |
| [DeepSeek API：Chat Completions 参数](deepseek-chat-completions.md) | [来源](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/) | 22,233 |
| [DeepSeek API：Responses 参数](deepseek-responses.md) | [来源](https://api-docs.deepseek.com/zh-cn/api/create-response/) | 12,761 |
| [DeepSeek API：补全接口参数](deepseek-fim-api.md) | [来源](https://api-docs.deepseek.com/zh-cn/api/create-completion/) | 4,224 |
| [DeepSeek API：余额查询](deepseek-balance.md) | [来源](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/) | 800 |
| [DeepSeek API：模型列表](deepseek-models.md) | [来源](https://api-docs.deepseek.com/zh-cn/api/list-models/) | 3,224 |
| [DeepSeek API：思考模式](deepseek-thinking.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/) | 9,548 |
| [DeepSeek API：工具调用](deepseek-tool-calling.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/) | 7,033 |
| [DeepSeek API：JSON 输出](deepseek-json-output.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/json_mode/) | 1,382 |
| [DeepSeek API：多轮对话](deepseek-multi-round.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/) | 1,283 |
| [DeepSeek API：上下文缓存](deepseek-context-cache.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/) | 2,117 |
| [DeepSeek API：视觉输入](deepseek-vision.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/vision/) | 6,873 |
| [DeepSeek API：文件使用](deepseek-files.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/files_api/) | 5,167 |
| [DeepSeek API：前缀续写](deepseek-prefix-completion.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/chat_prefix_completion/) | 876 |
| [DeepSeek API：FIM 补全指南](deepseek-fim-guide.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/) | 849 |
| [DeepSeek API：Anthropic 兼容协议](deepseek-anthropic-protocol.md) | [来源](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api/) | 3,764 |

## 检索与使用边界

- `backend/eval/vendor_full_rag.jsonl` 包含 60 个主题各一组带过滤/不带过滤查询，共 120 条；不是 120 个独立故障，也不是保留盲测集。
- 运行时本地哈希编码已删除，实际建库与查询必须使用千问；以前的本地检索报告只保留为历史记录，不代表千问效果。真实重建可运行 `scripts/rebuild_qwen_knowledge.py --reindex-existing --evaluate`，见导入指南。
- 版本、价格、限额和模型目录会变化，回答时保留来源与快照时间，需要当前状态时重新核对官网或授权业务工具。
- 本地工具只查询模拟业务；协议兼容不代表错误码、参数、账号状态或权限相同。
