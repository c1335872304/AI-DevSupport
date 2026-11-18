# 知识库与 RAG 流水线

状态：2026-10-19 当前实现。指标、故障覆盖和已知限制统一见 [第一阶段验收](../04-testing/RAG_PHASE_ONE_ACCEPTANCE.md)。设计背景见 [演进设计](RAG_EVOLUTION_DESIGN.md)，运行命令见 [操作手册](../03-operations/RAG_OPERATIONS.md)。

## 知识与身份

默认语料来自 `backend/vendor_knowledge/manifest.json`：DeepSeek、Qwen、GPT 官方正文快照。来源、版本及采集范围见 [语料说明](../01-getting-started/VENDOR_KNOWLEDGE.md)。`backend/demo_knowledge/` 的虚构公司手册和旧摘要仅作历史夹具，不默认导入。

RAG 提供文档知识证据，不证明某个用户的 Key、请求、用量或账单状态。文档同样属于不可信输入，不能指挥模型扩权调用工具。

文档 ID、输入修订、构建 ID 与业务知识版本分开管理：

| 标识 | 意义 |
| --- | --- |
| `FileUpload.id` | 稳定逻辑文档 ID；独立文档允许内容相同 |
| `file_md5` | 旧协议兼容 handle，新入口不将其等同于正文 MD5 |
| `source_md5` / `DocumentRevision` | 当前输入的内容校验与不可变正文、元数据快照 |
| `input_revision` | 正文或待发布元数据变更的递增修订，用于拒绝过期执行 |
| `IndexBuild` / `active_vector_version` | 一次构建与当前可检索版本 |
| Metadata 的 `version` | 文档适用的产品/政策版本，与构建编号不同 |

## 写入与发布

```text
新建正文 / 内容修订 / 旧分块上传 / 官方语料导入
  → 校验身份、输入、expectedRevision
  → 保存正文快照与待发布元数据
  → 同事务 ProcessingJob + IndexOutbox
  → 后台执行 / Kafka Worker
  → 原子领取任务 + 文档租约（owner、epoch、期限、input_revision）
  → 构建 Profile 与输入快照
  → 解析 → 父子分块 → 子块编码
  → 写入本次 build 的 DB / ES 数据
  → 校验数量、ID、文本与 Profile
  → 带执行权和输入修订条件切换活动指针
  → 后台定向 GC
```

上传 API 和脚本复用 `create_processing_job` / `run_processing_job`。`knowledge/indexer.py` 只是兼容门面，实际构建在 `build_pipeline.py`。

`job_runtime.py` 管任务领取、重试、Outbox 与过期扫描；`coordination.py` 管文档执行权。耗时解析、Provider 和 ES 调用不占长数据库写事务。定期续租失败后停止当前执行，晚返回的旧执行者无法发布。

重建幂等键用于同一输入修订的请求重放，不保证外部 Provider 恰好执行一次。输入变化须使用新请求；强制重建可能产生新的编码费用。

## 解析、分块与费用

- Markdown 保留标题、代码与表格边界；PDF/DOCX 使用独立 Docling 进程和固定模型缓存，生成结构块、来源定位、Markdown/JSON 产物。
- PDF/DOCX 有大小、页数、超时和内存边界；扫描/空文本明确返回 OCR_REQUIRED。其他格式的基础解析不等同于复杂版面验收。
- Parent 保存较完整的上下文；Child 承担编码和召回，再根据命中展开 Parent。同一父块不会另做一份向量。
- 子块 overlap 会重复编码重叠文本，完整重建也可能重新编码。恢复检查点减少无效工作，不承诺所有重试免费。
- 文档与查询统一使用千问 `text-embedding-v4`。缺少 Key、网络错误或模型/维度不匹配不能用哈希向量代替。
- 每批编码保存 EmbeddingAttempt、已知用量和 Provider 请求号。结算防重；超时等未知消耗保留待核对。

## 检索与证据

```text
查询 + 当前用户 + 可选产品/版本/分类/地域/时间过滤
  → 查询编码
  → Elasticsearch BM25 + KNN / 本地数据库检索
  → 融合与候选收集
  → SQL 当前权限、活动构建与模型维度复核
  → 重排 → 父块展开 → 再次复核 → 去重与预算裁剪
  → 带 build、块和来源位置的知识证据
```

ES 在召回阶段应用权限及元数据限制；应用再读取最新 SQL 状态复核，避免旧索引或旧事务快照放行已删除、已撤权或过期内容。数据库检索服务于本地小规模模式，不能把其测试直接描述为 ES 混合召回效果。

业务知识元数据包括产品、分类、地域、渠道、版本、生效时间和替代关系。待发布元数据与旧活动版分开，重建失败不会给旧正文提前换标签。默认检索当前适用知识；明确历史版本查询另行限定。

结构化结果区分 OK、NO_EVIDENCE、NEEDS_CLARIFICATION、CONFLICT 和 BACKEND_UNAVAILABLE。显式 `rag-claim` 可检测同范围值冲突，普通自然语言矛盾不视为已自动证明。

明确厂商问题先经`product_scope.py`约束规范产品，再走ES/SQL召回和最新DB复核；比较问题允许被明确提到的多家，OpenAI兼容协议/SDK不等于OpenAI托管服务。显式产品过滤冲突时澄清，不扩大范围。知识Agent保留原用户问题的厂商约束，查询改写不能切换厂商。实现与同条件ES对照见[修复验收](../04-testing/VENDOR_SCOPE_AND_BILLING_GATE_FIX_2026-10-20.md)。

引用使用绑定用户、文档 handle、build 和块的签名 ID；读取时再次授权。引用指向的 build 不再活动时返回 410，不把旧引用静默解析成新正文。

引用读取保留子块`textContent`，另返回相同活动版本的`contextText`，与检索使用的父上下文对齐。全文读取签名额外绑定document范围与长度；前端预览优先显示该上下文。来源名称及编号由持久化映射统一生成，同文件不同块不重排编号。知识证据按文档轮转保留最多12段、每段1600字符，文档规则仍不进入个人已核验事实。通用文档问答与实际故障先分流；厂商不明的Schema配置问题先澄清。实现及已知范围缺陷见[回答链路重验](../04-testing/ANSWER_QUALITY_FIX_2026-10-20.md)。

## 更新、删除与恢复

更新期间仍读取旧活动正文和索引；只有新构建发布成功才切换正文来源与活动元数据。构建失败记录原因和检查点，恢复由统一任务入口执行。

删除先写墓碑、使当前输入和租约失效，读取立即隐藏。GC 后续按明确 build 和正文引用删除，失败可重试，不执行“删除所有非当前任务版本”的宽泛清理。发布提交后响应丢失时复核已发布历史，避免将真实成功当失败清除。

## 实现定位

| 契约 | 代码 |
| --- | --- |
| 正文新建/修订、不可变快照 | `documents/revisions.py`、`revision_snapshot.py` |
| 持久任务、Outbox 与恢复 | `documents/job_runtime.py`；`jobs.py` 为兼容导出 |
| 文档租约与执行权 | `documents/coordination.py` |
| 构建与条件发布 | `knowledge/build_pipeline.py`；`indexer.py` 为兼容导出 |
| 墓碑、定向 GC、对账 | `documents/lifecycle.py` |
| 解析、Docling、分块 | `knowledge/parser.py`、`docling_adapter.py`、`docling_worker.py` |
| 编码、ES、检索 | `knowledge/embedding.py`、`elasticsearch.py`、`rag.py` |
| 版本引用与适用范围 | `knowledge/citations.py`、`metadata.py` |
| 用量与迁移 | `app/accounting/`、`backend/alembic/versions/` |

扫描 OCR、大规模调度与压测、普通自然语言冲突证明仍待后续扩展。当前能力的验证范围以验收报告为准。
