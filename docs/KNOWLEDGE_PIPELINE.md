# AI 客服知识库与 RAG

## 1. RAG 在客服系统里的职责

RAG 用于回答**企业可沉淀为文档的知识**：

```text
FAQ
产品说明
退款/订阅/售后政策
服务流程
错误码
故障排查手册
客服 SOP 中适合模型读取的部分
```

RAG 不负责查询实时客户状态：

```text
“退款规则是什么？”      -> RAG
“我的退款到账了吗？”      -> Payment/Refund Tool or MCP
“订单一般多久发货？”      -> RAG
“我的订单发货了吗？”      -> Order Tool or MCP
```

这是防止 AI 客服幻觉的核心业务边界。

## 2. 模块边界

```text
app/documents/
  客服知识文档上传、合并、存储、处理任务

app/knowledge/
  解析、分块、Embedding、索引、Retrieval、Rerank
```

## 3. 上传与处理

```text
Admin / Knowledge Maintainer
  ↓ chunk upload
api/v1/upload.py
  ↓
documents/upload.py
  ↓
file name / md5 / chunk / size / org permission validation
  ↓
Local Storage or MinIO
  ↓
ProcessingJob
  ↓
knowledge/indexer.py
```

大文件采用流式/临时文件合并，避免整文件进入 RAM。

`TASK_MODE=kafka` 时 ProcessingJob 通过 Kafka worker 执行，支持 retry、exponential backoff 和 DLQ。

## 4. Parent-Child Chunking

```text
Customer-service Document
  ↓
Parent chunk：保留完整政策/排障上下文
  ├── Child 1：负责 retrieval
  ├── Child 2
  └── Child 3
```

原则：

```text
Child -> embedding / retrieval
Parent -> answer context
```

这样错误码或某个条款可以细粒度命中，同时最终回答仍拿到完整上下文。

## 5. 版本化索引

客服知识不能因为一次重建失败就整体不可用：

```text
active version A
   ↓
build version B
   ↓
DB B + ES B
   ↓
verify B
   ↓
atomic active pointer switch
   ↓
garbage collect A
```

如果 B 构建失败，检索继续使用 A。

## 6. Metadata Filter

客服知识不再只有纯文本。每份文档可以携带：

```text
category       authentication / rate_limit / billing / refund / ...
product        API Platform / ...
region         GLOBAL / CN / APAC / ...
channel        api / billing / web / mobile / ...
effective_date 生效日期
version        政策/知识版本
error_code     精确错误码（适用时）
plan           Professional / Enterprise / ...
```

这些字段保存在 `FileUpload`，建库时被反规范化写入每个 Elasticsearch Child document。`search_knowledge` 支持 `filters` 参数，并在 BM25 与 KNN 召回**之前**加入 Metadata Filter。

例如：

```json
{
  "query": "429 怎么处理",
  "filters": {
    "category": ["rate_limit", "error_code"],
    "product": "API Platform",
    "channel": "api",
    "effective_at": "2026-08-01"
  }
}
```

这样检索先限定正确产品/知识域，再做语义与关键词召回。数据库 fallback 使用同一组 `FileUpload` 字段做 SQL 过滤。修改已建库文档的 Metadata 时，`PUT /documents/{file_md5}/metadata` 默认触发重新索引，使 ES 中的反规范化字段保持一致。

## 7. Retrieval

```text
customer question
   ↓
query embedding
   ↓
Vector + BM25/lexical recall
   ↓
RRF / fusion
   ↓
Reranker
   ↓
Parent expansion
   ↓
deduplicate + context budget
   ↓
search_knowledge Tool Result
```

生产大规模知识库优先 Elasticsearch；DB fallback 用于本地开发和小数据集。

## 8. 权限

知识检索在 Tool/Retrieval 层执行 ACL，不能“先搜全库，再让 LLM 决定能不能看”。

可访问范围由：

```text
user ownership
organization membership
public visibility
```

共同决定。

客户私有订单/支付等业务数据应由专门 Tool/MCP 做更严格的业务权限校验，不应塞进公共知识索引。

## 9. 内置 Demo Knowledge Base

仓库提供 `backend/demo_knowledge/`，用于让读者在没有外部 PDF/FAQ 的情况下直接体验真实客服 RAG：

```text
api-getting-started.md   API 调用、request_id 与基础重试
authentication.md        401、API Key 轮换与 Secret 安全
rate-limit.md            429、QPS 与月额度边界
billing-policy.md        套餐、用量与超额费用计算
refund-policy.md         退款政策与个人退款状态边界
error-codes.md           401/429 常见错误码
troubleshooting-faq.md   API 故障排查与人工升级条件
```

`manifest.json` 是 Demo 文档清单，并为每份文档提供客服 Metadata（category/product/region/channel/effectiveDate/version/plan 等）；`scripts/seed_demo_knowledge.py` 将这些字段写入标准 `FileUpload` 后直接复用 `knowledge/indexer.py`，因此 Demo 建库与用户上传文档使用同一条索引链，而不是单独维护一套假数据。

```text
Demo Markdown
  -> StorageService
  -> FileUpload
  -> process_file()
  -> DocumentParser
  -> Parent / Child
  -> Embedding
  -> Versioned DB / Elasticsearch
  -> active_vector_version
```

运行：

```bash
cd backend
python scripts/seed_demo_knowledge.py --username admin --reset
python scripts/evaluate_rag.py eval/demo_knowledge_rag.jsonl --username admin -k 6
```

注意：Demo 文档只代表知识事实。`req_demo_401` 的真实日志、某个客户的 API Key 状态、月度实际用量与账单继续来自 API/Billing Tool。这种“知识与业务状态分离”是客服 RAG 的固定边界。

## 10. Reranker 与后续扩展

当前 `knowledge/reranker.py` 是可替换的 post-retrieval reranker。以后引入 BGE/Cross-Encoder 时，不需要修改 Skill、Agent 或 WebSocket 层。

评测时重点关注客服问题的 Recall/MRR/nDCG，而不是仅看向量相似度。
