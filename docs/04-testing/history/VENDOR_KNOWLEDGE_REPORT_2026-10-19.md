# 厂商资料 Demo 知识库验证报告

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](README.md)。


日期：2026-10-19。

历史说明：随后已删除运行时哈希编码。本文描述当时的摘要与本地测试结果，不能作为千问效果结论；现在清空 Embedding Key 会报错。当前正文集与千问重建方式见[导入指南](../../01-getting-started/VENDOR_KNOWLEDGE.md)。

## 本轮变更

- 新增 OpenAI、Anthropic、DeepSeek 共 9 份官方资料中文摘要，每份保留来源、核对日期、厂商与适用范围。
- 新增独立 `vendor-manifest.json`，记录来源和本地摘要 SHA-256；不将核对日伪装成 API 规则生效日。
- 导入脚本增加 `--manifest` 参数，按清单所在目录读取文档，并验证可选校验和；默认仍使用原有 9 份本地业务手册。
- 增加 18 条检索案例及清单、校验和、来源、产品过滤和私有文档授权回归。

## 验证结果

| 检查 | 结果与范围 |
| --- | --- |
| 原有 Demo 文档测试基线 | 3 passed |
| 厂商清单解析与分块 | 9 份、9 个父块、15 个子块 |
| 本轮相关回归 | 7 passed；包含原有 3 项和新增 4 项 |
| 隔离库导入 | 9 份全部 COMPLETED，未替换应用数据库内容 |
| 带产品/分类过滤烟雾检索 | 9 条，Hit Rate@6、Recall@6、MRR、nDCG 均为 1.0 |
| 不带过滤查询 | 9 条，同上指标均为 1.0，目标文档均排在首位 |
| 付费模型调用 | 0；本地 hash 向量，不调用远端 Embedding 或 LLM |

下方复跑命令会在本机生成 `backend/eval/vendor-knowledge-local-report.json`。JSON 包含环境与局限说明。中文问题与原数据逐条核对，避免终端编码显示影响记录。

## 环境与复现

Python 3.12.14，项目现有 `.venv`。实际执行导入脚本与检索脚本，数据库为项目内新建的隔离 SQLite，存储为对应独立目录；未启动或验收 Elasticsearch，未写入正在运行的应用知识库，未修改 `.env`。

文件验证：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest demo_knowledge/vendor-manifest.json --validate-only
```

相关回归：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_demo_knowledge.py tests/knowledge/test_vendor_knowledge.py -p no:cacheprovider --basetemp <新建且可访问的测试临时目录路径>
```

本轮 pytest 临时目录的 Windows 权限问题通过在沙箱外执行同一本地离线测试解决，最终 7 项通过；测试仍仅连接隔离 SQLite，并使用本地存储与向量。

隔离导入和检索需先将进程级 `DATABASE_URL`、`LOCAL_STORAGE_DIR` 指向独立测试目录，设置 `STORAGE_BACKEND=local`、`SEARCH_BACKEND=database`、`REDIS_ENABLED=false`，清空进程级 `EMBEDDING_API_KEY`、`LLM_API_KEY`，启用开发建表和测试管理员，再执行：

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo_knowledge.py --manifest demo_knowledge/vendor-manifest.json --username admin --private
.\.venv\Scripts\python.exe scripts/evaluate_rag.py eval/vendor_knowledge_rag.jsonl --username admin -k 6 --output eval/vendor-knowledge-local-report.json
```

直接在已有配置下执行导入会使用该配置对应的数据库、存储和 Embedding；操作说明见 [厂商资料导入指南](../../01-getting-started/VENDOR_KNOWLEDGE.md)。

## 结论与局限

文档集、独立导入和本地检索链路可用。18 条由 9 个主题问题的带过滤/不带过滤版本组成，不是 18 种独立故障，也不是保留盲测集；成绩只代表这个小型固定语料的检索结果。

不带过滤时，Top-6 仍可能包含其他厂商的候选。目标首位正确不能证明上下文不会混用厂商规则，后续需要实现厂商识别、适用性过滤与答案验收。未验证生产索引、真实 Embedding、真实 LLM 回答和前端效果；本地工具仍不具备查询三家厂商生产账户的权限。
