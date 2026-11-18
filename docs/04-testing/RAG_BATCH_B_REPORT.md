# RAG 批次 B：生命周期与恢复验收

日期：2026-10-19。实现已完成，结果文件索引见总报告。

| 能力 | 实现与验收 |
| --- | --- |
| 不可变修订 | SHA256 正文、逻辑文档 ID、元数据快照确定 revision；源文件写入独立 revision 对象；Profile 包含解析、模型、维度和切分配置 |
| 请求与投递 | 请求绑定 input_revision；同修订在途合并，等价已发布 Profile 可复用；强制重建显式提交。Outbox 与任务同事务；元数据更新与请求同事务；旧上传提交窗口由扫描补派 |
| 恢复 | 原子接管过期 job；健康 RUNNING 不重置；批次进度、失败与调用尝试持久化。接管创建新 build，首期允许重新计算而不冒险复用半成品 |
| 删除 | tombstone、输入修订与 epoch 失效、取消任务；后续读取立即隐藏；重复后台清扫处理迟到残留，逻辑身份不复用 |
| 清理 | 仅清理已终结且不活动的指定 build；DELETING/收集状态可重试，COLLECTED 后仍可重复扫描残留；不再删除所有其他版本 |
| 解析缓存 | JSON/Markdown 按 revision/Profile 共享保存，普通 build GC 不删除其他构建可能复用的缓存；文档删除时精确清理已登记 revision/Profile 的缓存及原始对象 |
| 费用 | 每次 Provider 尝试有唯一记录、输入摘要、请求号、已知/未知用量；按唯一尝试结算，已知错误响应用量仍结算；超时未知用量不估造为零或重复已知结算 |

真实 Kafka 验收：专用 broker / topic / 数据库，2 条重复通知只形成 1 个 build；没有即时发送的请求由扫描器补派并完成。脚本 `scripts/verify_kafka_indexing.py` 使用显式编码替身，实际 Kafka、MySQL、ES 均参与；结果 `backend/data/checkpoints/kafka-report.json`。

边界：扫描首期按用户限并发和有限批次调度，不承诺严格加权公平；未知外部消耗需要依据 Provider 账单/请求号人工对账。新增真实 Provider 重试可能产生真实费用，不宣称 exactly-once 外部执行。墓碑保留，重新上传相同已删除逻辑身份会明确拒绝。

## 正文修订与独立文档

- `POST /documents/content` 创建稳定逻辑文档，即使正文完全相同也不会合并为同一文档；返回 documentId、兼容 handle 和实际 contentMd5。
- `POST /documents/by-id/{documentId}/content-revisions` 携带 expectedRevision 更新正文，文档 ID 保持不变；旧修订请求返回 409。不可变源快照与任务同事务登记，源和知识元数据在新 build 发布时切换。
- 新文档中的 fileMd5 是兼容旧路由的 32 位 opaque handle，不能再当作实际内容校验值；contentMd5 才是正文 MD5，修订记录另外保存 SHA256。旧文档的原 handle 不改变。
- 重建期间预览/下载仍读取活动源；成功后切换，失败保留旧源及旧索引。原有分块上传遇到同内容不同文件名会拒绝静默合并，应使用独立文档入口。
- 官方导入脚本按账号与明确文件名更新同一逻辑文档，reset 原地重建而非先删除；脚本和旧 Kafka envelope 均转换为统一 job，防止后台扫描与直接索引重复执行。
- 上述逻辑已通过真实 HTTP 与 MySQL/ES 验证，脚本 reset 的内容更新也有独立回归。保留原文件名的旧接口继续兼容。
