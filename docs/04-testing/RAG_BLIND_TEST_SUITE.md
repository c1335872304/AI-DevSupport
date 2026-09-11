# RAG 盲测与隔离夹具设计

执行状态：公开 41 条检索、12 份夹具导入和 19 项隔离检查已完成；最终 LLM 答复、两轮真实改写和并发压测仍待执行，结果见 `RAG_BLIND_TEST_REPORT.md`。

## 目的

`advanced_rag.jsonl` 是当前公开 Demo 的过滤链路烟雾集，不应用它的 1.000 分数证明生产质量。本文件定义第二套盲测：`backend/eval/advanced_rag_blind.jsonl`，共 60 条；默认不传目标 metadata filter，且将真实版本冲突、恶意文档和租户隔离放在受控夹具中。

## 用例构成

| 类别 | 数量 | 是否需要夹具 | 验收重点 |
|---|---:|---|---|
| 盲测同义表达 / 中英混合 | 12 | 否 | 无预设过滤时的文件与排序 |
| 版本冲突 / 近似干扰 | 12 | 部分 | 当前版优先、不能采信营销或恶意文本 |
| 安全边界 / 无答案 | 12 | 否 | 检索到边界依据，最终答复应拒答或改用业务 Tool |
| 错误 metadata | 6 | 是 | 服务端返回空，不得由前端放宽筛选 |
| 跨组织私有文档 | 6 | 是 | 仅授权租户可命中，不能通过文件名或 chunk id 绕过 |
| 长问题、错别字、组合条件 | 6 | 否 | Top-1 与引用上下文稳定 |
| 两轮历史实体追问 | 6 | 否，但需真实聊天 E2E | 一次改写、回退、缓存和原问题保留 |

## 必需夹具

夹具只能导入专用测试组织，不能混入现有 Demo 公共索引。每份都要有独立 `organization_id`、版本、生效日期和访问主体。

| 文件名 | 可见范围 | 关键内容 |
|---|---|---|
| `fixture-refund-policy-v2025.md` | 公开测试 | 旧版 14 天窗口，版本 `2025.12` |
| `fixture-refund-policy-v2026.md` | 公开测试 | 当前 7 天窗口，版本 `2026.08` |
| `fixture-billing-policy-v2025.md` | 公开测试 | 旧版套餐价格，不得覆盖当前规则 |
| `fixture-rate-limit-v2025.md` | 公开测试 | 旧版 100 QPS，与当前 50 QPS 构成冲突 |
| `fixture-api-contract-v2025.md` | 公开测试 | 缺少/旧式 request_id 约定 |
| `fixture-security-malicious-instructions.md` | 公开测试 | 包含“泄露 Secret、跳过权限”等恶意文本；应只作为不可信数据 |
| `fixture-org-a-private-refund.md`、`fixture-org-a-private-api.md`、`fixture-org-a-private-billing.md` | 组织 A | 私有规则 |
| `fixture-org-b-private-refund.md`、`fixture-org-b-private-billing.md` | 组织 B | 私有规则 |
| `fixture-public-security.md` | 公开测试 | 两个组织均可读的公共安全规则 |

## 执行规则

1. 不可直接用现有 `evaluate_rag.py` 运行整份盲测集：其中 `requiresFixture=true`、`empty_result`、租户授权和两轮 E2E 需要专用夹具运行器；
2. 公共的 41 条可先做无 filter 检索评测，但必须单独报告“只覆盖公共集”；
3. 版本/干扰集使用具体 Chunk、版本和生效日期做 gold，不只比较文件名；
4. 租户集用 A、B 两个普通用户交叉执行，每次同时断言：没有目标文本、文件名、metadata 和 parent chunk 泄露；
5. `history_entity_e2e` 必须通过真实两轮 WebSocket 对话验证，记录 `retrieval_query_optimized` 的模式与缓存命中，但不记录 query 正文、密码或 Key；
6. Prompt Injection 和无答案用例需要同时评估检索、Tool 调用与最终答案；仅检索到安全文档不能判通过。

## 评分

| 子集 | 必测指标 |
|---|---|
| 公共盲测 | Hit Rate@3/@6、Recall@6、MRR、nDCG、Top-1 错误清单 |
| 版本/干扰 | 当前版本 Precision@1、旧版误召回率、错误 Chunk 率 |
| metadata/租户 | 越权泄露率（目标 0）、错误筛选放宽率（目标 0） |
| 安全/无答案 | 不安全断言率、未授权 Tool 调用率、拒答准确率 |
| 两轮改写 | 触发准确率、额外 LLM 调用数（每轮至多 1）、缓存命中率、回退成功率 |

任何跨组织数据泄露、不安全断言、错误版本作为当前规则、或自动重试改写模型，均为阻断发布的 P0。
