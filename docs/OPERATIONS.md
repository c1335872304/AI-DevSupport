# 运维

日常命令从相应 Git 检出的仓库根目录执行。应用升级、迁移与回滚的顺序见[发布](RELEASING.md)。

<a id="docker"></a>

## Docker

根目录 [compose.yaml](../compose.yaml) 启动 API、前端、Worker、Billing MCP、MySQL、Redis、MinIO、Elasticsearch、Kafka，以及一次性迁移和演示初始化任务。编排用于本机开发演示，生产配置按发布手册单独准备。

```powershell
docker version
docker compose version
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
```

前端为 `http://localhost:9527`，API 健康检查为 `http://localhost:8000/health`，Swagger 为 `http://localhost:8000/docs`。经 Nginx 的 WebSocket 为 `ws://localhost:9527/proxy-ws/chat`。`migrate`、`demo-seed` 成功退出后长期服务运行，API 显示健康。

```powershell
docker compose logs --tail 200 mysql migrate demo-seed api worker billing-mcp frontend
docker compose restart api
docker compose up --build -d api worker frontend
docker compose exec -T frontend nginx -t
```

仅重启会复用镜像，代码更新通过构建替换。Worker 或后台恢复未完成的入库任务时可以继续产生 Embedding 调用。API 重建后的短暂 502 先核对其健康状态和 Nginx DNS 更新，再检查前端日志。

停止并保留数据使用 `docker compose down`，再次启动使用 `docker compose up -d`。已有卷、知识和配置按部署保留策略维护。完整清空数据属于单独的重置操作。

宿主机开发可使用 `docker compose -f deploy/compose.infra.yml up -d` 启动基础设施，随后按[开发](DEVELOPMENT.md)启动后端。该编排的端口和连接配置与完整 Demo 分别使用。

<a id="knowledge"></a>

## 知识库

默认官方语料为 DeepSeek、Qwen、GPT 各 20 份快照，来源和哈希以 [manifest.json](../backend/vendor_knowledge/manifest.json) 为准。以下命令在 `backend` 运行。

```powershell
python scripts/seed_demo_knowledge.py --validate-only
python scripts/seed_demo_knowledge.py --username admin
python scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6
```

导入和检索会产生真实编码调用。重复普通导入跳过未变化的已完成文档，显式 `--reindex` 强制构建新版本。模型、维度和切分配置变更时按新 Profile 重建，活动索引与查询配置保持匹配。

新建独立文档使用 `POST /api/v1/documents/content`，更新正文使用 `POST /api/v1/documents/by-id/{documentId}/content-revisions` 并提交 `expectedRevision`。返回的兼容 `fileMd5` 用于既有接口，正文校验使用 `contentMd5`。

任务读取入口为 `/api/v1/documents/processing-jobs/{job_id}`。检查任务状态、输入修订、租约和活动构建。重建失败时先修复解析、模型、额度或依赖问题，再通过重试入口提交任务。维护器处理过期租约、补派和定向清理。

`POST /api/v1/documents/{md5}/reindex` 支持 `Idempotency-Key`。同键与同输入修订重放返回原任务，键复用于不同修订返回冲突。删除先落墓碑，清理可重试。`embedding_attempts` 中的 UNKNOWN 保留供应商消耗核对状态。

<a id="docling"></a>

## Docling

文字 PDF / DOCX 由独立环境解析。Windows 在 `backend` 下准备环境和固定模型缓存。

```powershell
uv venv .venv-docling --python .venv/Scripts/python.exe
uv pip install --python .venv-docling/Scripts/python.exe -r requirements-docling.lock
python scripts/cache_docling_models.py
python scripts/verify_docling.py
```

需要代理时设置实际可达的下载代理。解析器使用 `DOCLING_PYTHON` 或本地 `.venv-docling`，模型使用 `DOCLING_ARTIFACTS_PATH` 或 `backend/data/models/docling`。Docker 镜像带独立 CPU 解析环境，通过只读挂载使用固定模型缓存。

<a id="billing"></a>

## Billing MCP

Billing MCP 读取同一 Demo 业务库的套餐、用量和账单，属主由已认证上下文注入。完整 Compose 内 API 使用 `http://billing-mcp:8011/mcp`，该服务仅在内部网络访问。环境配置指定 URL、令牌环境变量及超时，相关模板见 [backend/.env.example](../backend/.env.example)。

账单核实失败时先检查 MCP 健康、网络和调用身份，再核对工具错误与业务记录。客户账号事实按实际工具结果返回，合成数据按演示范围解释。

<a id="diagnosis"></a>

## 诊断与生成恢复

生成查询以持久终态和正文为准。活动生成持续更新心跳，失去心跳后由恢复扫描标记中断并释放预留。跨副本停止、迟到完成及结算规则见[架构](ARCHITECTURE.md#chat)。

诊断恢复入口、工单及执行记录按原诊断 ID 查询。失效的执行者由租约与 epoch 拒绝继续写入。工单提交结果未知时先查持久回执，再补齐诊断状态。使用隔离演示复现恢复问题的命令见[测试](TESTING.md#demos)。

<a id="observability"></a>

## 追踪与发布探测

Langfuse v4 使用可达的实例根地址和项目密钥，通过 OTLP/HTTP 异步导出。

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=<instance-root-url>
LANGFUSE_PUBLIC_KEY=<project-public-key>
LANGFUSE_SECRET_KEY=<project-secret-key>
```

在 Tracing 中按 `generation_id` 查 `customer_service.question`，核对路由、工具、模型用量、首段时间及质量门动作。原 `/metrics` 和 `/agent-runs` 接口已退役。业务正文和敏感参数按既有脱敏与隐私保留策略处理。

本机 Demo 使用 Langfuse 覆盖文件时，命令为 `docker compose -p paismart-demo -f compose.yaml -f deploy/compose.langfuse.local.yaml up -d --no-deps api`。该配置需要已准备的相邻 Langfuse 环境、项目密钥及共享网络。

`observe_rollout.py` 在独立进程中用合成账号探测业务和追踪，状态保存在专用 SQLite。配置 `PROBE_APP_URL`、探测账号、Langfuse 查询参数及通知目标后，从 `backend` 执行。

```text
python scripts/observe_rollout.py --state probe.sqlite probe
python scripts/observe_rollout.py --state probe.sqlite status
python scripts/observe_rollout.py --state probe.sqlite ack --incident <ID> --operator <operator>
python scripts/observe_rollout.py --state probe.sqlite resume --incident <ID> --operator <operator>
python scripts/observe_rollout.py --state probe.sqlite hold --reason duplicate_charge
```

每分钟串行探测，放量前 `status` 要求健康记录在 300 秒内且无暂停锁。连续三次失败或追踪不可核验时通知并锁定，确认严重业务事件时立即 `hold`。值守接手、连续两次健康和显式恢复共同支持解锁，目标平台的接线及阈值在[发布](RELEASING.md)确认。

<a id="network"></a>

## 排障顺序

| 现象 | 首先核对 |
| --- | --- |
| API 启动失败 | MySQL、迁移、初始化任务及第一条异常 |
| 页面 502 | API 健康状态、前端代理和服务名解析 |
| 知识无结果 | Worker、活动构建、权限、模型维度及索引版本 |
| 账单工具失败 | Billing MCP 网络、身份与工具回执 |
| Provider 失败 | 进程所在环境的 DNS、代理、Key 和实际错误 |
| 生成或审批结果未知 | 原生成 / 申请 ID 的持久状态与账本，再选择恢复入口 |

宿主机与容器分别核对可达的代理地址。Provider 故障使用单条受控请求验证，再核对实际用量。离线替身验证工程流程，真实检索和模型效果沿用有版本的评测证据。

专用工具的参数由[脚本说明](../backend/scripts/README.md)和各命令的 `--help` 提供。
