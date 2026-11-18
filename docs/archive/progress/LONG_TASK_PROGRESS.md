# 第一阶段长任务检查点

> 历史执行检查点。当前源码与剩余工作分别见[候选验收](../reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)和[债务台账](../../MAINTENANCE.md)。

状态更新：2026-10-19，A～D 本地实现与隔离验收完成。总报告：[第一阶段验收](../reports/RAG_PHASE_ONE_ACCEPTANCE.md)。当前应用知识库与配置保留；第二阶段未启动。

| 检查点 | 状态 | 证据与下一步 |
| --- | --- | --- |
| A-00 环境/快照 | PASSED | Python 3.12.14；Docker 29.7.2 / Compose 5.5.0。源码 411 文件起点归档和 SQLite 备份位于 `backend/data/checkpoints/phase1-start/` |
| A-01 基线/复现 | PASSED | 写入口统一；120 条真实查询基线 Hit@6 95%，查询用量 1,872 Tokens；竞争案例使用事件/屏障 |
| A-02～A-05 实现 | PASSED | 原子 job、文档租约/epoch、构建记录、逐块验证、条件发布；取消宽泛清理 |
| A-06 集成验收 | PASSED | 独立 MySQL/ES 24 项用例，包括两个独立进程竞争；现有 Docker Demo 不修改 |
| B 生命周期 | PASSED | 不可变修订/Profile、请求/Outbox、恢复、墓碑、定向 GC、结算防重及重建幂等键；真实 Kafka 验收通过 |
| C 解析与检索 | PASSED | Docling 8/8 样本、三格式真实 RAG、短事务授权复核、来源/版本引用、范围过滤、显式规则冲突 |
| D 综合交付 | PASSED | 全后端 167 passed / 2 skipped；前端类型检查及浏览器状态验证；HTTP 全流程、迁移演练及报告已交付 |

## 关键执行与证据

- `backend/data/checkpoints/phase1-final-idempotency.log`：最终全后端回归。
- `backend/data/checkpoints/rag-final-idempotency.log`：真实 MySQL/ES/独立进程 24 项。
- `backend/data/checkpoints/kafka-report.json`：真实消息重复与扫描恢复。
- `backend/data/checkpoints/docling/report.json`、`crossformat-rag.json`：真实解析及千问检索。
- `backend/data/checkpoints/e2e-report.json`：真实 HTTP 完整流程和完成后同键重放。
- `backend/data/checkpoints/migration-report.json`：副本升级/回退/再升级至 0013。
- `backend/data/checkpoints/application-upgrade-report.json`：应用库已备份升级，60/5888/1531 与知识摘要不变，配置未变。
- `backend/data/checkpoints/retrieval-final-comparison.json`：冻结真实向量回放指标不变，新增 Provider 调用为零。

遇到并已解决：Docker 管道需提权；原 0004 新装重复列；Hugging Face requests TLS 失败（改为固定模型预下载和离线解析）；前端依赖链接不完整（离线恢复）；HTTP 与竞争测试曾共用验收库（已拆分专用库）；测试响应替身缺少新增请求号读取所需 headers（已更新并全量回归）。

未作为首期保证：扫描 OCR、旧 DOC、任意自然语言冲突证明、断电/大集群压测、严格加权调度。详细边界见总报告和 C/B 报告。

下一步：总计划 P2-01，独立诊断对象与证据状态。恢复或复查从本文证据与源码归档开始，不再重复改造前基线编码。

环境观察：现有 paismart-demo API、前端、MySQL、Redis 正在运行，Worker 处于重启状态；这是已有环境状态，未对其操作。隔离验收使用另外的服务名和端口。普通沙箱无法访问 Docker 管道，提权后的只读检查成功。

最终检查点：重复运行产生的历史测试记录曾阻塞全局首批 GC 屏障，已将故障用例按文档、账号隔离，并补充过期输入请求不阻塞当前修订的回归。最终全量 167 passed / 2 skipped，真实 MySQL/ES 24 passed。独立验收容器已停止并保留数据，原 Demo 未操作。
