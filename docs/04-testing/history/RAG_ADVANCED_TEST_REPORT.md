# 高级 RAG 检索测试记录

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](README.md)。


日期：2026-09-09  
范围：内置 Demo 知识库、Qwen Embedding、Elasticsearch；60 条公开检索样本。  
模型费用：**0**。本记录只执行 `rag_service.search`，未调用 DeepSeek 或任何生成模型。

## 1. 前置检查

| 项目 | 结果 |
|---|---|
| 数据集 | `backend/eval/advanced_rag.jsonl`，60 条、10 类、每类 6 条；JSON、ID 唯一性及分组校验通过 |
| 索引基础 | 9 份 Demo 文档、29 个已用 Qwen `text-embedding-v4` 编码的 Chunk |
| 服务 | Docker `api` 重建后为 `healthy` |
| 评测身份 | 本机 Demo `admin`；仅用于权限感知检索，不涉及登录或密钥输出 |

## 2. 执行过程

依次运行以下命令。每一档都独立对 60 个问题调用 Elasticsearch 检索，结果由 `evaluate_rag.py` 按 `expectedFileName` 与可选 metadata filter 计算；脚本同步输出总体和 `byCaseType` 分类结果。

```powershell
docker compose exec api python scripts/evaluate_rag.py eval/advanced_rag.jsonl --username admin -k 3
docker compose exec api python scripts/evaluate_rag.py eval/advanced_rag.jsonl --username admin -k 6
docker compose exec api python scripts/evaluate_rag.py eval/advanced_rag.jsonl --username admin -k 10
```

## 3. 总体结果

| Top-K | 查询数 | Hit Rate@K | Recall@K | MRR | nDCG | 未命中 |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 60 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| 6 | 60 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| 10 | 60 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

所有三档均没有失败样本；每个相关文档首次出现的位置都是第一名，因此 MRR 和 nDCG 也为 1.000。

## 4. 分类别结果

三个 Top-K 下以下十类均为 6/6 命中，Hit Rate、Recall、MRR、nDCG 都是 1.000：

| 类别 | 用例数 | 覆盖内容 |
|---|---:|---|
| `paraphrase` | 6 | 中文口语/同义表达 |
| `multilingual` | 6 | 中英混合、错误码和术语 |
| `metadata_filter` | 6 | category、channel、plan 等过滤 |
| `distractor` | 6 | 退款规则/到账、429/QPS/额度等易混主题 |
| `version_policy` | 6 | 版本、兼容性和生效规则 |
| `parent_child_context` | 6 | 跨段处理步骤与引用上下文 |
| `boundary_no_answer` | 6 | 需要业务 Tool 或受控拒答的个人状态问题 |
| `prompt_injection` | 6 | 不可信文档与敏感信息边界 |
| `robustness` | 6 | 长问题、拼写错误和组合条件 |
| `history_entity` | 6 | 历史请求 ID、错误码、接口、账单/订单实体的追问补全 |

## 5. 结论与边界

结论：在当前 **内置公开 Demo 文档 + 既定 metadata** 的范围内，60 条样本的检索正确文档被稳定排在 Top-1，达到高级计划给出的 `k=6` 初始门槛（Hit Rate ≥ 0.95、Recall ≥ 0.90、MRR ≥ 0.80、nDCG ≥ 0.85）。

这不是完整的生产 RAG 验收，以下项目仍未通过本次测试证明：

1. 本报告不包含跨组织/私有文档权限隔离；该项已由 `RAG_BLIND_TEST_REPORT.md` 的 12 份夹具和 19 项检查补充验证，未发现跨组织检索泄露；
2. Prompt Injection 与“个人状态”样本：本次只证明检索到正确的安全/边界文档，尚未验证真实 LLM 最终答复是否拒绝注入；
3. 父子 Chunk 引用审计：需逐条检查 `parentChunkId`、文本片段与最终回答引用；
4. 性能基准：本次为顺序质量评测，不包含并发 1/3/5、P50/P95、CPU 或错误率压测；
5. 历史实体改写：这 6 条验证的是已补全的检索语义；真实两轮对话下的 DeepSeek 改写只做过离线缓存/回退冒烟验证，尚未做额外付费 E2E 调用。

后续盲测执行结果见 `RAG_BLIND_TEST_REPORT.md`。它已补充无预设过滤的公开排序、版本夹具、错误 metadata 与 A/B 组织隔离；本报告中的 1.000 结果仍只应作为过滤烟雾测试记录。

## 6. 后续建议

下一优先级应为 A6 并发性能测试，以及单独批准、不超过 10 条的真实答案忠实度与 Prompt Injection 评测。前者不需要调用 DeepSeek，后者需要单独控制预算。
