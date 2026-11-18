# DeepSeek、Qwen、GPT 官方正文采集与检索基线

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](README.md)。


日期：2026-10-19。此报告记录正文语料准备，不代表四阶段计划的 RAG 写入协调、条件发布与清理改造已完成。

后续变更：本报告中的本地哈希编码已从运行时删除，以下数字仅是当时的历史记录，当前代码不能通过清空 Key 重现该模式。实际建库与查询改用千问，新的重建/检索记录分别保存在 `backend/eval/vendor-full-qwen-build.json` 和 `vendor-full-qwen-retrieval.json`；以对应运行状态判断是否完成。

## 本轮成果

按用户指定选择三家：DeepSeek 官方 API、Qwen 阿里云百炼托管 API、GPT 对应的 OpenAI API。每家 20 篇，共 60 篇；不再以三家各三篇短摘要作为主资料集。

| 服务 | 正文数 | 正文字符数 |
| --- | ---: | ---: |
| DeepSeek | 20 | 89,969 |
| Qwen / 百炼 | 20 | 1,532,258 |
| GPT / OpenAI | 20 | 820,086 |
| 合计 | 60 | 2,442,313 |

已整理 Markdown 为 2,837,027 字节，约 2.84 MB；字符数包含英文、代码、表格和空白，不是中文汉字数或 Tokens。三家文档组织方式不同，篇数相同不表示覆盖深度或总文档量相同。此次是精选页面，不是官方全部文档。

正文与逐篇官方链接见 [资料目录](../../../backend/vendor_knowledge/README.md)，来源与校验和见 [manifest.json](../../../backend/vendor_knowledge/manifest.json)，采集统计见 [collection-report.json](../../../backend/vendor_knowledge/collection-report.json)。

## 正文保留与采集检查

- OpenAI、Qwen 使用官方提供的 Markdown，保留原始正文与多语言示例；前面仅添加来源、服务范围与核对日期。
- DeepSeek 从文档 article 提取并转换为 Markdown，排除导航，保留可提取标题、表格、参数、链接与代码；同时保存原始 HTML。
- 来源限制为官方域名/路径，逐次检查重定向；核对标题、最小正文长度与重复正文，不接受只有 HTTP 200 的首页回退或错误模板。
- 首轮发现一个旧 Qwen 环境变量入口与 API Key 页面正文重复，已改选独立批量接口资料；最后 60 篇成功，无失败和重复正文。
- 原始响应、正文、本地整理文件分别记录 SHA-256，导入前验证清单内容。核对日与快照标签不冒充厂商规则生效日。
- 当前主清单不包含上一批 Anthropic 服务摘要；DeepSeek 的 Anthropic 兼容协议文档仍属于 DeepSeek 产品资料。

## 本地验证结果

| 检查 | 结果 |
| --- | --- |
| 清单、原文一致性、转换、重定向边界、检索样本及既有摘要集回归 | 11 passed |
| 解析与父子切分 | 60 篇，1,531 个父块，5,888 个子块 |
| 隔离 SQLite 实际导入 | 60 篇全部 COMPLETED，未替换应用数据库内容 |
| 付费模型调用 | 0；使用 local-hash-v1，不调用远端 Embedding/LLM |

pytest 的 Windows 临时目录在沙箱内不可访问，最终在沙箱外执行同组离线测试通过；数据与网络边界仍由隔离 SQLite、本地存储、测试替身和清空进程级模型 Key 保持。

## 检索基线

固定 60 个主题问题，各执行带产品/分类过滤和不带过滤两种查询，共 120 条。使用现有数据库 fallback 与本地 hash 向量，`k=6`；按预期文件名评分。

| 分组 | 查询数 | 命中数 | Hit Rate@6 / Recall@6 | MRR | nDCG |
| --- | ---: | ---: | ---: | ---: | ---: |
| 带过滤烟雾 | 60 | 50 | 0.8333 | 0.7553 | 0.7742 |
| 不带过滤查询 | 60 | 42 | 0.7000 | 0.6103 | 0.6329 |
| 合计 | 120 | 92 | 0.7667 | 0.6828 | 0.7035 |

下方复跑命令会在本机生成 `backend/eval/vendor-full-local-report.json`。中文问题与原 JSONL 逐条核对，报告附环境、分组和局限说明。

结果说明当前检索面对更大的中英文正文、相似主题与长参数表仍有提升空间。上述数字不是远端语义向量、ES 混合检索或真实 LLM 答复的成绩；不将上一批 9 份摘要的满分结果外推到此语料。

120 条来自 60 个主题的配对查询，不是 120 个独立故障，也不是保留盲测集。精确文件评分可能将另一份相关文档中的等价信息记为未命中，后续需要块级相关性标注与答案评测。不带过滤时其他厂商仍可能进入候选，目标命中也不能证明最终上下文不混用规则。

## 复现方式

在 `backend/` 目录下执行文件检查与相关回归：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --validate-only
.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_demo_knowledge.py tests/knowledge/test_vendor_knowledge.py tests/knowledge/test_vendor_full_corpus.py -p no:cacheprovider --basetemp <新建且可访问的临时目录路径>
```

实际导入与检索前，将进程级 `DATABASE_URL`、`LOCAL_STORAGE_DIR` 指向新建隔离目录，设置 `DATABASE_AUTO_CREATE_DEV=true`、`STORAGE_BACKEND=local`、`SEARCH_BACKEND=database`、`REDIS_ENABLED=false`、`BOOTSTRAP_ADMIN_ENABLED=true`，清空进程级 `EMBEDDING_API_KEY` 和 `LLM_API_KEY`，再执行：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --username admin --private
.\.venv\Scripts\python.exe scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6 --output eval/vendor-full-local-report.json
```

未经隔离设置，导入会使用现有应用环境，远端 Embedding 配置可能产生费用。完整说明见 [导入指南](../../01-getting-started/VENDOR_KNOWLEDGE.md)。本轮未修改 `.env`，未启动 ES 或前端，未向正在运行的应用导入。

## 后续用途

此语料作为 RAG 第一阶段的新基线，保留旧 Demo 集作为兼容回归。先按既定计划修复写入并发和生命周期，再用这份语料评估结构分块、适用性过滤、召回、重排与引用。不要为了提高分数删掉难例或改写官方正文为预设答案。
