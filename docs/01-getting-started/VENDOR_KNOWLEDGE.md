# DeepSeek、Qwen、GPT 官方文档知识库

整理日期：2026-10-19。当前主资料集按用户指定，仅收录 DeepSeek、Qwen、GPT 三家服务，各 20 篇官方正文，共 60 篇、2,442,313 个正文字符，约 2.84 MB 已整理 Markdown。字符数包含英文、代码、表格与空白，不等同于汉字数或 Tokens。

2026-10-20 已将同一份60篇官方语料及5888条现有千问向量迁入Docker，移除其中旧假想公司及测试资料；本地库保留，配置未变。迁移采用已有向量复用，未重新编码，见[实际验收及检索限制](../04-testing/DOCKER_VENDOR_KNOWLEDGE_MIGRATION_2026-10-20.md)。

GPT 指 OpenAI API，Qwen 指阿里云百炼托管 API。OpenAI 和 Qwen 使用官方原生 Markdown，完整保留所选页面正文；DeepSeek 提取文档 article 并转为 Markdown，排除站点导航，保留可提取的标题、表格、参数和代码。这里是人工选择的 60 篇正文快照，不是三家全站镜像。每篇首部添加来源和适用范围，正文未压缩为摘要。

## 文件与范围

- [正文目录与逐篇入口](../../backend/vendor_knowledge/README.md)：`backend/vendor_knowledge/*.md`。
- [导入清单](../../backend/vendor_knowledge/manifest.json)：厂商、产品、来源、正文与原始响应哈希、字符数及示例问题。
- [官方来源目录](../../backend/vendor_knowledge/sources.json)：可复查的 60 个官方 URL；`raw/` 保留原始响应，导入只读清单内正文，避免重复建库。
- [采集报告](../../backend/vendor_knowledge/collection-report.json)：60 篇成功、无失败与重复正文。
- 检索案例：`backend/eval/vendor_full_rag.jsonl`，60 个主题各一组带过滤/不带过滤查询，共 120 条。
- 默认导入清单已切换为 `vendor_knowledge/manifest.json`。旧假想公司 9 份文档已从当前应用知识库、父子块和上传存储移除；源码仅留作历史测试夹具。
- 上一批 `demo_knowledge/vendor-*.md`、`vendor-manifest.json` 和对应评测作为历史摘要集保留，当前主清单不导入它们，也不收录 Anthropic 服务摘要。

产品过滤值分别为 `OpenAI API`、`Qwen API`、`DeepSeek API`；本地模拟业务仍为 `API Platform`。核对日期放在来源记录和 `snapshot-2026-10-19` 版本标签中，不伪装成规则生效日或 API 版本。`sha256` 校验带来源首部的本地 Markdown，`bodySha256` 校验正文，`rawSha256` 校验原始下载响应。

## 内容覆盖

| 服务 | 正文数 | 覆盖范围 |
| --- | ---: | --- |
| DeepSeek | 20 | 接入、Chat/Responses/FIM 参数、错误码、限流、余额、模型、Token、思考、工具、JSON、多轮、缓存、视觉、文件及兼容协议 |
| Qwen / 百炼 | 20 | 接入、Key、SDK、地域、base URL、Chat/DashScope/Responses 参数、批量、流式、工具、结构化输出、思考、多轮、缓存、向量、限流、错误和提示工程 |
| GPT / OpenAI | 20 | 接入、文本、多轮、流式、工具、结构化输出、推理、提示、缓存、Embedding、检索、文件搜索、错误、限流、批量、后台、Webhook 与 Responses 迁移 |

## 先验证，再导入

以下命令从项目 `backend/` 目录执行。只做文件解析检查时，不连接数据库或调用模型：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --validate-only
```

确认当前应用数据库、存储、检索后端与 Embedding 配置后，向已有账号导入：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --username admin --private
```

`--private` 表示不公开，但现有组织授权仍可能允许同组织读取；严格按个人隔离可另外传 `--org-tag ""`。省略 `--private` 会按现有脚本默认公开。默认不使用 `--reset`；该参数现在保留逻辑身份并原地重建清单内文档。脚本按明确文件名更新已有文档的正文修订，因此导入目标应选择专门的 Demo 账号，避免与个人上传文件重名。

实际导入需要远端千问 Embedding，会调用 Provider 并消耗额度；仅验证文件与单测不代表已向应用导入。隔离测试使用进程级配置，不通过改写 Key 切换测试模式。

## 使用千问重新编码

实际完成情况与费用见 [千问替换验收报告](../04-testing/history/QWEN_EMBEDDING_REPLACEMENT_2026-10-19.md)：当时应用库 69 份文档完成真实编码；随后清理旧假想公司 9 份，当前为 60 份官方文档、5,888 条千问向量。该报告中的 69 份评测是清理前结果，历史哈希成绩也不作为现行效果。清理记录见 `backend/eval/legacy-removal-report.json`。

运行时已移除本地哈希编码和空 Key 降级。建库、查询都需要有效 `EMBEDDING_API_KEY`，默认模型 `text-embedding-v4`、256 维；没有 Key 或 Provider 失败会报错，不生成替代向量。测试只允许显式测试替身，不能作为检索效果证据。

需要把目标账号现有的不兼容向量和官方正文一起重建，并运行真实查询评测时：

```powershell
.\.venv\Scripts\python.exe scripts/rebuild_qwen_knowledge.py --reindex-existing --evaluate --max-tokens 4000000
```

这个命令使用配置的应用数据库，先备份 SQLite、检查运行任务并发送小请求验证连接，然后重建目标账号不兼容文档、导入 60 篇正文并评测。其他账号文档不参与迁移；默认只给目标资料设置非公开可见性，组织授权仍按现有规则。

`--max-tokens` 采用提交文本 UTF-8 字节数作保守 Token 上界，所有请求累计预留后才发送，失败也保留已提交额度；实际 Provider 用量另行记录。默认 400 万上界对应北京地域 0.5 元/百万 Tokens 原价下的约 2 元输入预算，实际以账单为准；不是先发请求再事后检查。报告输出到 `eval/vendor-full-qwen-build.json` 与 `eval/vendor-full-qwen-retrieval.json`，日志不应包含 Key。

父块只存上下文，5,888 个子块才提交 Embedding；本语料的子块输入比未重叠父块文本约多 17.17%，主要来自 overlap，并非父子各编码一遍。完整重建和重复相同内容仍可能产生新用量。

## 检索与演示

导入后运行检索评测：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6 --output eval/vendor-full-report.json
```

可演示的问题：

- OpenAI 返回 429，为什么不能直接认定只是请求太快？
- Qwen OpenAI 兼容流式输出如何取得 usage 信息？
- GPT 的工具调用和 Structured Outputs 分别适合什么场景？
- Qwen 的地域、base URL 与 API Key 如何匹配？
- DeepSeek 的 402 和 429 分别表示什么？
- DeepSeek 同账号换一把 Key，是否就能提高账号并发限额？

先确认服务厂商再解释规则；未说明厂商的“401/429 怎么办”不应混合三家结论。知识库只提供规则依据，本地业务工具仍查询本地模拟状态，不能据此声称查询了厂商生产账户。来源链接已放在正文中，现有检索返回的文件引用可回溯这些材料；机器可读的来源字段需要后续 RAG 设计落地，不冒充已经实现。

## 更新方式

维护 `sources.json` 中的官方来源，使用采集脚本重新下载；刷新时建议指定新的快照目录，校验通过后再导入，避免覆盖正在使用的快照。示例从 `backend/` 执行，日期应填写本次实际核对日期：

```powershell
.\.venv\Scripts\python.exe scripts/collect_vendor_knowledge.py --catalog vendor_knowledge/sources.json --output-dir vendor_knowledge/snapshot-new --checked-at YYYY-MM-DD
```

脚本限制官方域名与路径，核对重定向、正文标题、最小长度、重复内容并保存失败报告；全部成功才生成可导入清单，不以 HTTP 200 当作正文有效的充分条件。更新后重新运行解析与检索验证。正文长度不代表知识质量，长表格、跨语言检索和接口兼容性仍需专项评测。

## 官方来源

| 厂商 | 接入与认证 | 错误 | 限流 |
| --- | --- | --- | --- |
| OpenAI | [API Overview](https://developers.openai.com/api/reference/overview) | [Error codes](https://developers.openai.com/api/docs/guides/error-codes) | [Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) |
| Qwen | [首次调用](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen) | [错误码](https://help.aliyun.com/zh/model-studio/error-code) | [限流](https://help.aliyun.com/zh/model-studio/rate-limit) |
| DeepSeek | [首次调用 API](https://api-docs.deepseek.com/zh-cn/) | [Error Codes](https://api-docs.deepseek.com/quick_start/error_codes/) | [限速与隔离](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit/) |
