# RAG 批次 A：写入安全验收

> 阶段验收记录，按本页执行日期、语料和部署范围阅读。后续源码与发布状态见[候选验收](RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。

日期：2026-10-19。实现已完成，真实服务验收证据见总报告。

- 起点归档：`backend/data/checkpoints/phase1-start/source.zip`，411 个源文件；同目录保存 SQLite 一致性备份与文件摘要，未归档 `.env`。
- 基线：60 份官方文档、5,888 子块向量、1,531 父块。120 条真实千问查询总体 Hit@6 为 95%，MRR 0.773611、nDCG 0.816786；查询编码 1,872 Tokens，未重编文档。
- 写入口：上传/元数据/重试创建请求；后台和 Kafka 使用原子 job 领取；历史 Kafka envelope、两个 seed 脚本、Qwen 重建脚本的直接 `process_file` 调用统一进入 fenced build。
- 主要实现：`documents/coordination.py`、`documents/job_runtime.py`、`knowledge/build_pipeline.py`；旧 jobs/indexer 模块保留兼容入口，不再保留旧写逻辑。
- 领取与发布：数据库时钟、owner、租约、单调 epoch、输入修订；独立进程竞争不依赖 asyncio 锁；失效任务不能发布或释放新执行者的租约。
- 构建按批持久化，解析、Provider 和 ES 操作不处于数据库写事务内；发布前检查 DB 块 ID/内容、ES 数量及逐块身份/内容/Profile。
- 去除全部非自身版本的清理；提交结果不明时先查活动指针，禁止在异常分支删除可能已发布的 ES 数据。

迁移：0007～0013；修复原有 0004 在新装时重复加列的问题。SQLite 副本演练升级 → 回退 0006 → 再升级，知识摘要不变；MySQL 新装及增量升级均执行成功。

命令（backend 目录）：

```powershell
$env:RAG_TEST_MYSQL_URL='mysql+aiomysql://root:rag-test-only@127.0.0.1:13316/rag_acceptance'
$env:RAG_TEST_REAL_ES='1'
.\.venv\Scripts\python.exe -m pytest tests/knowledge/test_build_coordination.py tests/knowledge/test_multi_process_claim.py -q
```

验收采用隔离 MySQL 8.4 / ES 8.17；编码为显式测试替身，仅验证工程行为。真实 Provider 的效果和消耗另外记录，不将这些测试当检索成绩。
