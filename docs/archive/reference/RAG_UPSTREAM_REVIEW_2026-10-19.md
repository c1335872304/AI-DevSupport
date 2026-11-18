# RAG 上游实现核对

> 整编前资料快照。现行指南从[日常文档](../../README.md)进入。

核对日期：2026-10-19。固定 commit 与源文件副本清单保存在 `backend/data/checkpoints/upstream/manifest.json`。以下是读取源码后的本地采用判断，不表示复制了上游完整实现或取得同等规模的保障。

| 项目 | 固定版本与实际入口 | 确认的做法 | 本地采用与边界 |
| --- | --- | --- | --- |
| Onyx | `f189d4987e54008ba0ffbf9d7d3f6b30c178eb1a`；[IndexingCoordination.try_create_index_attempt](https://github.com/onyx-dot-app/onyx/blob/f189d4987e54008ba0ffbf9d7d3f6b30c178eb1a/backend/onyx/db/indexing_coordination.py)、[DefaultDocumentIndexingAdapter.lock_context](https://github.com/onyx-dot-app/onyx/blob/f189d4987e54008ba0ffbf9d7d3f6b30c178eb1a/backend/onyx/indexing/adapters/document_indexing_adapter.py) | 尝试级协调与文档写冲突分开；数据库事务/约束控制重复尝试，文档修改上下文使用行锁 | 本地分开 job 原子领取与文档租约，并以 epoch 和条件发布拒绝迟到执行者。租约/epoch 是本地方案，不能声称上游使用完全相同机制 |
| Dify | `823f40e71fc9e045a9ff2aa903a74b5b001dff33`；[document_indexing_task.py](https://github.com/langgenius/dify/blob/823f40e71fc9e045a9ff2aa903a74b5b001dff33/api/tasks/document_indexing_task.py) 中 `_document_indexing` 及租户队列入口 | 先在短事务写解析状态，再执行慢速解析/向量操作；存在租户隔离队列 | 本地网络/解析操作不持有写事务；按用户限制活跃文档，Outbox 与请求同事务创建，扫描恢复通知。首期没有照搬 Celery 或承诺严格加权公平调度 |
| RAGFlow | `7eb673bfc3ab1cc22532fe23a1e9bb85c34e48bd`；[Office RawBlock](https://github.com/infiniflow/ragflow/blob/7eb673bfc3ab1cc22532fe23a1e9bb85c34e48bd/internal/deepdoc/parser/office/types.go)、[PDF parser](https://github.com/infiniflow/ragflow/blob/7eb673bfc3ab1cc22532fe23a1e9bb85c34e48bd/internal/deepdoc/parser/pdf/parser.go)、[分块与原文定位说明](https://github.com/infiniflow/ragflow/blob/7eb673bfc3ab1cc22532fe23a1e9bb85c34e48bd/docs/guides/dataset/chunk_parsing_results_and_knowledge_fragment_management.md) | Office 保留段落样式、表格行及图片信息；PDF 保留页信息和版面相关数据；分块检查可回到源文档位置 | 本地统一内容块、标题路径、顺序和可用页码/坐标；保存原始对象、JSON、Markdown。当前固定版本已采用 Go 路径，旧 `rag/svr/task_executor.py` 路径不存在，未继续引用旧入口 |
| Docling | Python `2.58.0`；本地安装源码 `document_converter.py`、`layout_model.py`、`table_structure_model.py` | PDF 管线支持关闭 OCR、开启表格结构，Word 走结构化解析；可指定离线模型目录 | 独立解析环境和子进程；不将依赖装入现有 API 环境；固定模型和校验摘要，扫描件明确返回 OCR_REQUIRED |

## 固定解析模型

- 布局：`ds4sd/docling-layout-heron`，提交 `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`。
- 表格：`ds4sd/docling-models`，提交 `fc0f2d45e2218ea24bce5045f58a389aed16dc23`，accurate TableFormer。
- 模型文件摘要见 `backend/data/models/docling/manifest.json`，其摘要进入构建 Profile；解析子进程设置离线模式。
- 完整 Windows 解析环境版本见 `backend/requirements-docling.lock`。跨平台安装不能盲用其中 Windows 专属包，基础需求见 `requirements-docling.txt`。

## 本地验证证据

数据库/ES 竞争与独立进程验收、Kafka 重复通知、8 份真实解析样本、同内容三格式真实编码与引用、版本失效、源数据迁移摘要，见 [第一阶段验收报告](../reports/RAG_PHASE_ONE_ACCEPTANCE.md)。上游源码核对不代替这些本地验收。
