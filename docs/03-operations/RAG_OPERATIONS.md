# RAG 构建、解析与恢复操作

## 启动与迁移

从 backend 目录运行应用前先执行 `python -m alembic upgrade head`。当前本地 SQLite 与 Docker Demo 均为 0015；Docker 已于 2026-10-20 更新四阶段源码，原知识库保留，见 [升级验收](../04-testing/DOCKER_DEMO_UPGRADE_2026-10-20.md)。升级其他部署时先备份、在副本检查迁移，再停止/隔离旧 Worker 后部署，禁止新旧写入逻辑同时运行。

源码入口：`documents/job_runtime.py` 管请求和投递，`documents/coordination.py` 管文档执行权，`knowledge/build_pipeline.py` 管构建与发布，`documents/lifecycle.py` 管清理和用量对账。只通过这些入口写索引，不直接更新活动版本。

## Docling 环境

Windows 本地使用独立环境，不修改当前 API 的依赖：

```powershell
uv venv .venv-docling --python .venv/Scripts/python.exe
uv pip install --python .venv-docling/Scripts/python.exe -r requirements-docling.lock
$env:MODEL_DOWNLOAD_PROXY='http://127.0.0.1:7897' # 仅当本机确有该代理时设置；直连环境省略
.\.venv\Scripts\python.exe scripts/cache_docling_models.py
.\.venv\Scripts\python.exe scripts/verify_docling.py
```

解析器优先使用 `DOCLING_PYTHON`，否则查找 backend/.venv-docling；模型优先 `DOCLING_ARTIFACTS_PATH`，否则使用 backend/data/models/docling 的固定缓存。启动前预下载，解析时不在线获取 main 模型。当前 Docker 镜像内置 `/opt/docling` 独立 Linux CPU 环境，通过只读挂载使用现有固定缓存；不能直接使用 Windows 专属 lock 包。

## 状态与恢复

- `/documents/processing-jobs/{job_id}` 区分任务状态、租约与活动索引是否可用；构建 manifest 保存 Profile、阶段、完成块数、摘要和耗时。
- 默认租约 120 秒、最多 3 次执行、每用户最多 2 个活跃文档。API 后台维护扫描器恢复过期请求、补派及清理；Kafka 投递可重复，消费按 job 执行权防重。
- Worker 正常运行时不要把 RUNNING 手工改 PENDING。确认租约过期后由协调入口接管；不手工将旧 build 重新激活。
- 重建失败保留活动版。先处理模型、存储、额度或解析原因，再用文档重试接口提交强制重建；旧 build 发布权不能恢复。
- 对 `POST /documents/{md5}/reindex` 携带 `Idempotency-Key`：相同文档/输入修订的同一键在完成后重放仍返回原 job，不再次编码。键复用于不同输入修订返回 409；新的强制重建使用新键。
- 删除先落墓碑，后续读取立即隐藏，后台清理失败会重试。普通 GC 默认保留 1 小时；不会无条件清空其他版本。
- `embedding_attempts` 的 UNKNOWN 表示外部用量未知；不要按零费用结清。已知且未结算记录由维护器补结算，外部不明记录依据账单核对。

## 隔离验收

```powershell
docker compose -f deploy/compose.rag-test.yaml up -d
```

从仓库根目录启动，使用专属项目 `paismart-rag-acceptance`，MySQL 13316、ES 19216、Kafka 19092；HTTP 验收 API 18016、前端 19527。MySQL 数据库 `rag_acceptance`、`rag_http_acceptance`、`rag_kafka_acceptance` 分开；索引和 topic 同样独立。测试脚本中的账号密码仅用于本机隔离验收。

执行脚本前核对目标 URL，不对当前 Demo volume 执行 down -v。结束后可停止此验收 Compose 项目，保留数据以供复查；不清理用户已有项目。

## 提交正文新修订

新建独立文档使用 `POST /api/v1/documents/content`，multipart 字段为 file、可选 metadata JSON 字符串。新文档默认仅拥有者可读。返回 documentId / fileMd5（兼容 handle）/ contentMd5 / inputRevision / processingJobId。

更新正文使用 `POST /api/v1/documents/by-id/{documentId}/content-revisions`，multipart 字段 file、expectedRevision、可选 metadata。先从文档状态取得当前 inputRevision；409 表示已被更新，应读取新状态再决定下一步。接口不复用内容 MD5 作为新文档身份；不要把返回的兼容 handle 当正文校验值。

原有分块上传协议继续支持，独立但相同内容的文档应改用上述新建入口。导入脚本 `--reset` 改为保留身份原地重建；清理操作使用墓碑，不直接删除活跃指针或清空其他版本。

## 诊断状态升级

第二阶段增加0014诊断会话、轮次、证据和状态变更表，不重建知识索引。诊断详情和只读API见 [诊断架构](../02-architecture/DIAGNOSIS_STATE.md)。`verify_phase2_migration.py`仅在副本演练；`--apply`才备份并迁移本地应用库。中断诊断暂不自动续跑工具，此能力归第三阶段。
