# 运维细节参考快照

整编日期为 2026-11-19。本页汇集整编前的详细说明及阶段记录，日常维护见[现行手册](../../OPERATIONS.md)。


<a id="docker"></a>

## Docker 操作

原文档为 `DOCKER_OPERATIONS.md`。

本文面向 PaiSmart 的本机 Docker Demo。根目录的 `compose.yaml` 是唯一的完整应用入口；它会启动前端、API、Billing MCP、Worker 以及 MySQL、Redis、MinIO、Elasticsearch、Kafka，并在首次启动时执行迁移和演示数据初始化。

> 这套编排固定为 `APP_ENV=dev`，默认凭据和端口仅适用于受信任的本机演示，不能直接作为生产部署配置。

> 升级已有 Demo 前先阅读 [RAG 迁移与恢复](OPERATIONS_2026-11-19.md#rag)：备份、隔离旧 API/Worker、迁移后再部署。2026-10-20 本机 Demo 已更新四阶段源码与独立 CPU Docling 环境，迁移及验收证据见 [升级报告](../reports/DOCKER_DEMO_UPGRADE_2026-10-20.md)。初始化会保留已有知识库，只有空库才导入官方资料并产生编码调用。

### 1. 前置条件

在项目根目录执行以下命令：

```powershell
docker version
docker compose version
docker compose config --quiet
```

前两条确认 Docker Engine 与 Compose 可用；最后一条只校验 Compose 配置，不创建容器。首次构建会拉取基础镜像，并需要足够的 CPU、内存和磁盘空间；Elasticsearch 与 Kafka 是资源占用最大的两个服务。

如果新开的 Windows PowerShell 显示“找不到 `docker`”，Docker Desktop 的 CLI 通常位于 `$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin`；可先为当前窗口补充路径：

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
docker compose ps
```

该设置只影响当前 PowerShell 窗口；也可以将 Docker Desktop CLI 目录加入用户级 `PATH` 后重新打开终端。

如需使用真实 LLM 或 Embedding，在启动前仅编辑本机的 `backend/.env`，填写相应 API Key。该文件已被 Git 忽略，切勿把密钥放入 `compose.yaml` 或提交到仓库。

PDF/DOCX 解析模型须事先准备在 `backend/data/models/docling`；API、Worker 以只读目录挂载，解释器位于镜像 `/opt/docling/bin/python`。此挂载保留固定模型缓存，构建不下载模型的 main 分支。宿主机代理从容器访问时需使用 `host.docker.internal`；Compose 默认保留当前 `7897` 代理，可设置 `DOCKER_EMBEDDING_HTTP_PROXY` 覆盖，显式空字符串表示直连。

网络、代理、Docker CLI 和远端 Provider 的专项检查见 [NETWORK_TROUBLESHOOTING.md](OPERATIONS_2026-11-19.md#network)。

### 2. 启动完整 Demo

```powershell
docker compose up --build -d
docker compose ps
```

`--build` 会构建本地后端和前端镜像；`-d` 让服务在后台运行。第一次启动会依次等待基础设施健康、执行 `migrate`、运行 `demo-seed`，随后启动 API、Worker、Billing MCP 与前端。

访问入口：

| 用途 | 地址 |
| --- | --- |
| 前端 | http://localhost:9527 |
| API 健康检查 | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |
| WebSocket | `ws://localhost:8000/chat` |

经前端 Nginx 访问时，API 前缀为 `/api/v1`，WebSocket 为 `ws://localhost:9527/proxy-ws/chat`。

本机 Demo 管理员为 `admin / admin123`。仅用于本机演示；任何可被他人访问的部署都必须替换 JWT Secret 与管理员密码，并使用生产环境编排。

### 3. 观察启动状态与排障

```powershell
# 追踪全部服务日志；Ctrl+C 只停止查看日志，不停止容器
docker compose logs -f

# 只观察最常需要关注的服务
docker compose logs -f mysql migrate demo-seed api billing-mcp worker frontend

# 查看单个服务最近 200 行日志
docker compose logs --tail 200 api

# 查看容器、健康状态与端口映射
docker compose ps
```

成功条件是 `migrate` 和 `demo-seed` 显示为已完成（退出码 0），长期服务处于 `running` 或 `healthy`。若 API 未启动，优先查看 `migrate`、`demo-seed`、`elasticsearch`、`kafka` 的日志，因为 API 会等待这些依赖完成或健康。

旧 ES 向量可能缺少新版检索必需的模型名和维度。升级后若列表有文档但检索为空，先执行下列只读预检；只有数据库活动版本、ES文档身份、正文和真实向量逐条一致，才允许补齐缺失字段。此操作不编码、不改正文/向量/权限，也不改数据库；已有字段冲突或并发版本变化会停止。

```powershell
docker compose exec api python scripts/repair_legacy_embedding_metadata.py
# 预检匹配后才执行
docker compose exec api python scripts/repair_legacy_embedding_metadata.py --apply
```

常见问题：

| 现象 | 优先检查 |
| --- | --- |
| 9527 或 8000 无法访问 | `docker compose ps`，然后查看 `frontend` 或 `api` 日志；确认宿主端口未被占用。 |
| `demo-seed` 失败 | 查看 `mysql`、`minio`、`elasticsearch` 日志；不要只重启 API。 |
| 知识库无检索结果 | 先确认 `worker` 正常运行，再检查 `demo-seed` 是否完成及 Elasticsearch 健康状态。 |
| 账单查询无法核实 | 查看 `billing-mcp` 日志；它只能由 API 经内部地址 `http://billing-mcp:8011/mcp` 调用。 |
| 容器频繁退出 | 用 `docker compose logs --tail 200 <服务名>` 找到第一条错误；避免直接删除数据卷。 |

### 4. 功能验收

启动稳定后，可先验证基础服务：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

然后登录前端并依次提出以下问题：

1. `你们的退款政策是什么？`：应走 Knowledge 检索。
2. `请求 req_demo_401 返回 401，帮我定位原因。`：应走 API 诊断与知识上下文。
3. `为什么 2026-08 的账单比套餐基础价高？`：应通过 Billing MCP 核实账单事实。
4. `不用继续排查了，帮我转人工。`：应在证据汇总后创建人工交接。

Billing MCP 不映射宿主机端口；不要尝试用 `localhost:8011` 调用它。这是刻意的网络边界，API 容器使用 Compose 服务名访问它。

### 5. 常用维护操作

从待发布源码的根目录执行。当前独立 Git 克隆位置见[Git 操作记录](../../DEVELOPMENT.md#git)。已有部署涉及结构变化时先备份并执行迁移，`alembic upgrade head` 应与待部署源码一致。Worker 或后台恢复未完成的入库任务时，可继续产生 Embedding 请求。

```powershell
# 重启一个长期服务，例如 API
docker compose restart api

# 代码或 Dockerfile 改动后，只重建并替换 API
docker compose up --build -d api

# 前端代理配置或页面改动后，同时替换 API 与前端
docker compose up --build -d api frontend

# 同时重建 API 与 Worker（适合后端、索引或任务处理改动）
docker compose up --build -d api worker

# 进入 API 容器排查；镜像为 slim，优先使用 Python 命令而不是假设有 bash
docker compose exec api sh

# 在 API 容器内执行一个只读健康探针
docker compose exec api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/health').read().decode())"
```

若为已有知识文档配置或更换了 Embedding 模型/维度，必须按 [本地启动说明](../../DEVELOPMENT.md) 的要求重新建立 Elasticsearch 索引并执行 Demo 知识库重建；不能只重启 API。

#### API 重建后的前端代理检查

前端使用 Docker 内置 DNS 动态解析 `api` 服务名。API 刚重建且仍处于 `health: starting` 时，请求可能短暂返回 502；等待 API 变为 `healthy` 并超过约 10 秒的 DNS 缓存窗口后，无需重启 frontend。可用一个需要登录的接口确认代理已恢复（401 是未登录时的预期结果，不是 502）：

```powershell
docker compose up -d --force-recreate --no-deps api
docker compose ps api frontend
Invoke-WebRequest http://localhost:9527/api/v1/users/me
```

如果 API 已健康但持续返回 502，再查看 `docker compose logs --tail 100 frontend api`；重启 frontend 仅是旧镜像或紧急情况下的恢复手段。

### 6. Docker 内回归测试

以下命令使用 `test` profile 构建测试镜像，并在同一 Compose 网络中验证 Agent、Billing MCP 与 WebSocket 主链路：

```powershell
# 核心 Compose 回归
docker compose --profile test run --build --rm test

# 全量测试使用隔离 SQLite，避免测试夹具触碰 Demo 业务数据
docker compose run --rm --no-deps -e DATABASE_URL=sqlite+aiosqlite:////tmp/docker-tests.sqlite -e DATABASE_AUTO_CREATE_DEV=true -e REDIS_ENABLED=false -e BILLING_MCP_COMPOSE_E2E=false -e BILLING_MCP_ENABLED=false -e TASK_MODE=background -e STORAGE_BACKEND=local -e SEARCH_BACKEND=database -e LOCAL_STORAGE_DIR=/tmp/test-storage -e LLM_API_KEY= -e EMBEDDING_API_KEY= --entrypoint pytest test tests -q
```

`--rm` 只删除本次测试容器，不删除数据库、索引或其他命名卷。运行测试前建议确认没有同名的临时 Compose 项目在占用端口或卷。

### 7. 停止、保留数据与彻底重置

```powershell
# 停止并移除容器和网络；保留 MySQL、Redis、MinIO、Elasticsearch、Kafka 的命名卷
docker compose down

# 再次启动并复用保留的数据
docker compose up -d
```

下面的命令会删除所有命名卷，进而永久清空演示数据库、对象、检索索引、缓存和 Kafka 数据。只有确实需要从零开始时才执行：

```powershell
docker compose down -v
docker compose up --build -d
```

重置后 `migrate` 和 `demo-seed` 会再次创建 schema 并写入演示数据。生产数据绝不能用 `down -v` 清理；应遵循备份、迁移和保留策略。

### 8. 仅启动基础设施（高级）

`deploy/compose.infra.yml` 只适用于在宿主机直接运行后端时需要的依赖，不包含 API、前端、Worker 或 Billing MCP：

```powershell
docker compose -f deploy/compose.infra.yml up -d
docker compose -f deploy/compose.infra.yml ps
```

此模式把 MySQL、Redis、MinIO、Elasticsearch、Kafka 映射到宿主机端口，适合后端调试；不要与根目录完整 Demo 混用，以免端口和数据卷冲突。停止时也必须指定同一份文件：

```powershell
docker compose -f deploy/compose.infra.yml down
```

服务拓扑、MCP 边界和详细验收背景见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](OPERATIONS_2026-11-19.md#billing)。


<a id="rag"></a>

## RAG 运维

原文档为 `RAG_OPERATIONS.md`。

### 启动与迁移

从 backend 目录运行应用前先执行 `python -m alembic upgrade head`。当前本地 SQLite 与 Docker Demo 均为 0015；Docker 已于 2026-10-20 更新四阶段源码，原知识库保留，见 [升级验收](../reports/DOCKER_DEMO_UPGRADE_2026-10-20.md)。升级其他部署时先备份、在副本检查迁移，再停止/隔离旧 Worker 后部署，禁止新旧写入逻辑同时运行。

源码入口：`documents/job_runtime.py` 管请求和投递，`documents/coordination.py` 管文档执行权，`knowledge/build_pipeline.py` 管构建与发布，`documents/lifecycle.py` 管清理和用量对账。只通过这些入口写索引，不直接更新活动版本。

### Docling 环境

Windows 本地使用独立环境，不修改当前 API 的依赖：

```powershell
uv venv .venv-docling --python .venv/Scripts/python.exe
uv pip install --python .venv-docling/Scripts/python.exe -r requirements-docling.lock
$env:MODEL_DOWNLOAD_PROXY='http://127.0.0.1:7897' # 仅当本机确有该代理时设置；直连环境省略
.\.venv\Scripts\python.exe scripts/cache_docling_models.py
.\.venv\Scripts\python.exe scripts/verify_docling.py
```

解析器优先使用 `DOCLING_PYTHON`，否则查找 backend/.venv-docling；模型优先 `DOCLING_ARTIFACTS_PATH`，否则使用 backend/data/models/docling 的固定缓存。启动前预下载，解析时不在线获取 main 模型。当前 Docker 镜像内置 `/opt/docling` 独立 Linux CPU 环境，通过只读挂载使用现有固定缓存；不能直接使用 Windows 专属 lock 包。

### 状态与恢复

- `/documents/processing-jobs/{job_id}` 区分任务状态、租约与活动索引是否可用；构建 manifest 保存 Profile、阶段、完成块数、摘要和耗时。
- 默认租约 120 秒、最多 3 次执行、每用户最多 2 个活跃文档。API 后台维护扫描器恢复过期请求、补派及清理；Kafka 投递可重复，消费按 job 执行权防重。
- Worker 正常运行时不要把 RUNNING 手工改 PENDING。确认租约过期后由协调入口接管；不手工将旧 build 重新激活。
- 重建失败保留活动版。先处理模型、存储、额度或解析原因，再用文档重试接口提交强制重建；旧 build 发布权不能恢复。
- 对 `POST /documents/{md5}/reindex` 携带 `Idempotency-Key`：相同文档/输入修订的同一键在完成后重放仍返回原 job，不再次编码。键复用于不同输入修订返回 409；新的强制重建使用新键。
- 删除先落墓碑，后续读取立即隐藏，后台清理失败会重试。普通 GC 默认保留 1 小时；不会无条件清空其他版本。
- `embedding_attempts` 的 UNKNOWN 表示外部用量未知；不要按零费用结清。已知且未结算记录由维护器补结算，外部不明记录依据账单核对。

### 隔离验收

```powershell
docker compose -f deploy/compose.rag-test.yaml up -d
```

从仓库根目录启动，使用专属项目 `paismart-rag-acceptance`，MySQL 13316、ES 19216、Kafka 19092；HTTP 验收 API 18016、前端 19527。MySQL 数据库 `rag_acceptance`、`rag_http_acceptance`、`rag_kafka_acceptance` 分开；索引和 topic 同样独立。测试脚本中的账号密码仅用于本机隔离验收。

执行脚本前核对目标 URL，不对当前 Demo volume 执行 down -v。结束后可停止此验收 Compose 项目，保留数据以供复查；不清理用户已有项目。

### 提交正文新修订

新建独立文档使用 `POST /api/v1/documents/content`，multipart 字段为 file、可选 metadata JSON 字符串。新文档默认仅拥有者可读。返回 documentId / fileMd5（兼容 handle）/ contentMd5 / inputRevision / processingJobId。

更新正文使用 `POST /api/v1/documents/by-id/{documentId}/content-revisions`，multipart 字段 file、expectedRevision、可选 metadata。先从文档状态取得当前 inputRevision；409 表示已被更新，应读取新状态再决定下一步。接口不复用内容 MD5 作为新文档身份；不要把返回的兼容 handle 当正文校验值。

原有分块上传协议继续支持，独立但相同内容的文档应改用上述新建入口。导入脚本 `--reset` 改为保留身份原地重建；清理操作使用墓碑，不直接删除活跃指针或清空其他版本。

### 诊断状态升级

第二阶段增加0014诊断会话、轮次、证据和状态变更表，不重建知识索引。诊断详情和只读API见 [诊断架构](IMPLEMENTATION_2026-11-19.md#diagnosis-state)。`verify_phase2_migration.py`仅在副本演练；`--apply`才备份并迁移本地应用库。中断诊断暂不自动续跑工具，此能力归第三阶段。


<a id="langfuse"></a>

## 追踪与放量探测

原文档为 `LANGFUSE.md`。

Langfuse 是后端问答链路的追踪入口。导出开关默认开启，配置实例地址和两把项目密钥后开始上报。Compose 部署使用后端环境文件，配置生效后重启 API。

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=http://host.docker.internal:3000
LANGFUSE_PUBLIC_KEY=<project-public-key>
LANGFUSE_SECRET_KEY=<project-secret-key>
```

地址使用 API 容器或本地 Python 进程能访问的 Langfuse v4 实例根地址。若实例与 API 共用 Docker 网络，使用对应服务地址。Langfuse Cloud 请填项目所在区域的根地址。后端通过 OTLP/HTTP 批量异步导出。

升级后，原 `/metrics` 和后台 `/agent-runs` 接口已退役。既有数据库追踪记录继续按原隐私保留规则处理。对话恢复、诊断状态、计费和工单仍由业务数据库处理。

本地 Demo 的 Compose 组合使用两个覆盖文件。启动 Langfuse Web 时，保留其原有 Compose 文件并追加 `deploy/compose.langfuse.web-network.yaml`。从本仓库根目录重建 Demo API 时使用 `docker compose -p paismart-demo -f compose.yaml -f deploy/compose.langfuse.local.yaml up -d --no-deps api`。两端通过 `paismart-langfuse` Docker 网络连接，API 通过相邻 Langfuse 目录下的 `local-langfuse/ai-devsupport.env` 读取项目密钥。本地面板地址为 `http://localhost:3000`。

进入 Langfuse 的 Tracing 页面，定位 `customer_service.question`，通过 `generation_id` 对应本地会话追踪。检索记录最多保留 20 条召回结果的文件和片段标识、排名和得分。诊断和账单工具保留工具名、状态和耗时。模型记录保留模型名和供应商回传的 token 数，`answer.model` 的首 token 耗时可和根记录的 `first_chunk_ms` 对照，后者从工作流开始计时，到首个通过质量门的流式片段。最终记录包含路由、质量门、是否转人工和回答长度，`answer_delivery` 记录是否替换已播出的答案。问题原文、回答正文、文档片段、工具参数、账单明细及异常正文只在业务系统内按已有规则处理。

在 `backend` 目录运行 `python -m pytest -q tests/agent/test_langfuse_acceptance.py tests/agent/test_target_workflow_e2e.py`。测试覆盖 RAG 引用错误和证据不支持的结论、流式首 token 延迟、Billing MCP 失败以及取消和超时。测试使用模型和工具替身及本机 OTLP 接收器。

从 `backend` 目录运行 `python scripts/evaluate_customer_service.py --live --output eval-report.json` 执行已有六层评测。此命令使用真实模型和固定工具样本，需要配置模型密钥。开启 Langfuse 后，每个评测用例记录分层结果，报告用 `langfuseTraceId` 关联对应追踪。队列刷新只说明本地批处理已完成，请在 Langfuse 页面核对接收。

### 独立探测与放量门禁

在与业务 API 和 Langfuse 分开的进程上运行 [observe_rollout.py](../../../backend/scripts/observe_rollout.py)。它用专用合成账号走正式登录、创建会话、WebSocket 和生成结果查询，核对完成事件与持久状态。随后用生成 ID 对应的根 trace ID 查询 Langfuse Observations v2。查询成功但没有根观测，以及查询服务不可用，分别记录为 `trace_missing` 和 `trace_check_unavailable`。状态和通知待发送记录保存在独立 SQLite 文件中。

设置 `PROBE_APP_URL`、`PROBE_USERNAME`、`PROBE_PASSWORD`、`PROBE_LANGFUSE_URL`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、`PROBE_NOTIFY_URL`，通知接口如需鉴权再设置 `PROBE_NOTIFY_TOKEN`。使用授权的合成账号和有读取权限的 Langfuse 项目密钥。每个发布环境使用自己的状态文件，写权限仅授予探测进程和授权值守。通知接收端应按 `Idempotency-Key` 去重并以 HTTP 2xx 确认受理。

```text
python scripts/observe_rollout.py --state probe.sqlite probe
python scripts/observe_rollout.py --state probe.sqlite status
python scripts/observe_rollout.py --state probe.sqlite ack --incident <ID> --operator <值守标识>
python scripts/observe_rollout.py --state probe.sqlite resume --incident <ID> --operator <值守标识>
python scripts/observe_rollout.py --state probe.sqlite hold --reason duplicate_charge
```

试点期间每分钟串行运行一次 `probe`，默认等待根观测最多约 30 秒，按目标 Langfuse 的入库延迟校准。放量前运行 `status`，只有最近一次探测健康、记录不超过 300 秒且无暂停锁时退出 0。首个异常即停止把当前状态当成放量依据，连续三次失败或无法观测时触发通知并锁定放量。通知受理后由值守执行 `ack`，两次连续健康仍保留暂停锁，值守核实业务后显式执行 `resume`。

确认一例重复扣费、重复工单、虚报写操作成功、越权或凭据泄露时，立即用相应原因执行 `hold`，零等待锁定放量。聚合指标达到已批准阈值时也可以使用 `hold --reason metrics_threshold`。本文的放量门禁通过退出码供发布流程调用，目标发布系统应接入该检查。


<a id="diagnosis"></a>

## 诊断恢复

原文档为 `DIAGNOSIS_OPERATIONS.md`。

诊断模块对应 `0015_diagnosis_loop`，当前完整应用包含后续迁移至 `0020_remove_invite_codes`，部署统一执行 `alembic upgrade head`。设计见[诊断闭环](IMPLEMENTATION_2026-11-19.md#diagnosis-loop)，结果见[第三阶段验收](../reports/DIAGNOSIS_LOOP_ACCEPTANCE.md)。

### 升级与配置

先停止旧版本业务 Worker，备份数据库，再执行 `python -m alembic upgrade head`。本轮应用 SQLite 已备份升级；原 Docker 镜像没有重建或切换。正式部署仍需按目标 MySQL/实例部署流程执行升级与健康检查。

SQLite 副本演练：在 backend 执行 `python scripts/verify_phase3_migration.py`；仅显式 `--apply` 才备份并升级应用库。脚本检查知识指纹与配置摘要，不会重新编码。回退演练只在副本进行；生产回退删除本阶段表前必须保留诊断与工单数据。

| 设置 | 默认值 | 用途 |
| --- | --- | --- |
| DIAGNOSIS_LEASE_SECONDS | 240 | 数据库执行租约，最低30秒 |
| DIAGNOSIS_STEP_ATTEMPTS | 2 | 每步骤最多尝试 |
| DIAGNOSIS_TURN_ATTEMPT_BUDGET | 12 | 每轮工具尝试预算 |
| DIAGNOSIS_CASE_ATTEMPT_BUDGET | 36 | 单诊断总预算 |
| DIAGNOSIS_RECOVERY_ENABLED | true | 启用结构化后台恢复扫描 |

示例设置在 `.env.example`；本轮没有修改实际 `.env`。关闭恢复只停止自动扫描，面板显式继续仍检查租约与身份。不要直接修改 epoch、清空预算或把所有 RUNNING 置回待执行。

### 排查任务

在诊断详情查看 executions、steps、workflow.decision、rechecks 和 transitions。PENDING/运行中可以点击“继续核查”；持有健康租约时不会接管。过期执行由扫描接管，逐步恢复。新问题 supersede 旧轮次后，旧任务会停止发布。

工单待提交时保留 HANDOFF_PENDING；重试使用原诊断身份，不另造请求。HANDED_OFF 只能由真实工单结果支持。复查被拒绝时检查归属、应用、接口与五分钟时间窗口，不能强行修改 RESOLVED。

历史日志没有请求时观测属于正常不确定性。`seed_support_demo.py` 只为新建的模拟事件同步创建观测，不回填已有日志，也不应为演示清空现有知识库。

### 独立复现

在 backend 运行 `python scripts/phase3_acceptance_server.py`，使用独立 `data/phase3-ui.sqlite`，API 18036，测试账号 loopaccept / LoopAccept123；每次新建带唯一前缀的验收会话，禁用真实模型/编码。另运行 `python scripts/verify_phase3_api.py` 验证真实 HTTP，报告写入 checkpoints。请在启动后五分钟内提交夹具新请求；超时重新启动生成新夹具。

前端进程环境设 VITE_SERVICE_BASE_URL=http://127.0.0.1:18036/api/v1，VITE_OTHER_SERVICE_BASE_URL 包含 api 和 ws://127.0.0.1:18036，再运行 Vite 独立端口19537。登录后选“第三阶段闭环验收 ui”，从 fixture JSON 取新请求号，提交复查并观察“已解决”。此服务不是生产启动命令，不连接正式知识库。

`PHASE3_TEST_MYSQL_URL` 仅指向专用测试库后运行 `pytest tests/agent/test_diagnosis_loop.py`。故障注入覆盖调用后未落库、落库后中断、交接意图后中断和提交确认丢失；这些是固定测试场景，不代表生产长时负载结论。


<a id="network"></a>

## 网络排障

原文档为 `NETWORK_TROUBLESHOOTING.md`。

本文记录 PaiSmart 在 Windows、Docker、Clash/代理和外部 LLM/Embedding Provider 组合下的网络前置条件与排障方法。

### 1. 当前结论

2026-10-19 起，实际建库与检索仅使用远端千问 Embedding，本地哈希编码已移除：

| 模式 | 条件 | 行为 |
|---|---|---|
| 未配置 | `EMBEDDING_API_KEY` 为空 | 明确报错，不生成本地向量 |
| 远端 Provider | `EMBEDDING_API_KEY` 非空 | 访问 `EMBEDDING_BASE_URL/embeddings`，需要 DNS、代理和 Key 均可用 |

远端失败不会切换编码方式。切换模型或维度后重新建立索引，禁止新查询混用旧向量。历史报告中的本地哈希结果仅保留为历史工程记录，不能用作千问效果结论。

### 2. Docker CLI 检查

在项目根目录执行：

```powershell
Get-Command docker -ErrorAction SilentlyContinue
docker version
docker compose version
docker compose config --quiet
```

如果 PowerShell 显示找不到 `docker`：

1. 安装并启动 Docker Desktop；
2. 关闭并重新打开 PowerShell；
3. 如果 Docker Desktop 已安装但 CLI 不在 `PATH`，临时执行：

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
docker compose version
```

当前仓库只能提供检测和启动说明，不能替代 Docker Desktop 安装、Windows 服务启动或管理员权限配置。

### 3. Windows 宿主机网络检查

检查 DashScope DNS 和 HTTPS：

```powershell
Resolve-DnsName dashscope.aliyuncs.com
Test-NetConnection dashscope.aliyuncs.com -Port 443
```

如果使用 Clash，检查本机 HTTP 代理端口。下面以 `7897` 为例：

```powershell
Test-NetConnection 127.0.0.1 -Port 7897
```

如果上述检查失败，优先处理 DNS、Clash 是否运行、端口是否正确和防火墙规则，不要反复执行 Live 评测。

### 4. Docker 容器访问外部 Provider

Docker 容器不能自动继承 Windows 系统代理。使用 Clash 时：

1. Clash 选择“规则”模式；
2. 为 `dashscope.aliyuncs.com` 配置 `DIRECT` 或可用的稳定线路；
3. 确认 Clash HTTP 端口；
4. 在 `backend/.env` 设置：

```env
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=256
EMBEDDING_HTTP_PROXY=http://host.docker.internal:7897
```

端口不是 `7897` 时必须替换为实际端口。不要把 `localhost:7897` 写给容器使用；容器内的 `localhost` 指向容器自身。

Docker 服务重建后，可以从 API 容器检查解析和 HTTPS：

```powershell
docker compose run --rm --no-deps api python -c "import socket; print(socket.gethostbyname('dashscope.aliyuncs.com'))"
```

如果配置了显式代理，再检查容器到宿主机代理端口是否可达：

```powershell
docker compose run --rm --no-deps api python -c "import socket; s=socket.create_connection(('host.docker.internal',7897),5); print('proxy reachable'); s.close()"
```

### 5. 离线验证与 Windows 直连

无外部网络时，只执行文件解析、分块及使用显式测试替身的单测；不能运行真实编码、建库或查询并声称效果通过。

```powershell
cd backend
python scripts/seed_demo_knowledge.py --manifest vendor_knowledge/manifest.json --validate-only
python -m pytest -q tests/knowledge
```

Windows 宿主机不能直接照搬容器专用的 `host.docker.internal` 代理地址。先检查 Provider 直连；可以直连时将宿主机配置的 `EMBEDDING_HTTP_PROXY` 留空，必须走本机代理时使用实际可达的主机地址与端口。容器配置按第 4 节单独设置。

### 6. 真实 Provider 测试顺序

真实模型测试必须遵循以下顺序：

```text
Docker CLI / 服务检查
  → DNS / 代理检查
  → 管理后台 Provider 连接测试
  → 单条受控请求
  → 核对余额与 Trace
  → 再决定是否扩大样本
```

任何网络失败都不应自动重试整批请求。DeepSeek、Qwen 和 Docker 网络问题分别记录，不能把 Provider 失败误判成 Agent 或 RAG 质量失败。

### 7. 结果记录

每轮记录宿主机或容器、Provider 域名、代理方式、失败阶段和实际错误。离线替身测试证明的工程行为与真实 Provider 的连通结果分别记录。历史本地哈希编码已退出运行时，排障完成后通过受控的真实请求核对连接及用量。

[本地启动](../../DEVELOPMENT.md) · [Docker 操作](OPERATIONS_2026-11-19.md#docker) · [历史真实模型记录](../live-tests/DEEPSEEK_LIVE_TEST_REPORT.md)


<a id="billing"></a>

## Billing MCP 拓扑

原文档为 `DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md`。

本文是 PaiSmart 个人 Demo 的当前容器化实现说明。Billing MCP 是本项目内的独立 Docker 服务，不依赖第三方计费系统；它只读取同一套 Demo 数据库中的套餐、用量和账单事实。

### 1. 目标

在一条 `docker compose` 命令下启动可访问的 Linux 容器环境。宿主机浏览器访问前端/API；容器间只通过 Docker 内部网络通信。

```text
Browser on host
  -> frontend (host port 9527)
  -> api (host port 8000)
       -> billing-mcp (internal port 8011 only)
       -> mysql (internal port 3306 only)
       -> redis / minio / elasticsearch / kafka (internal only)

api / worker / demo-seed
  -> redis, minio, elasticsearch, kafka (internal only)
```

Billing 请求的唯一链路：

```text
Billing Agent
  -> Billing MCP Tool Discovery
  -> list_tools
  -> http://billing-mcp:8011/mcp
  -> discovered read-only billing Tool schemas
  -> Billing Agent selects a discovered Tool
  -> call_tool
  -> MySQL support_* billing tables
```

`RoutingPolicy`、三个专业 Agent、Shared Scheduler、证据汇总和转人工顺序不因容器化而改变。

### 2. MCP Tool 发现与路由边界

Billing MCP 采用标准 MCP 的 Tool Discovery，而不是在 API 代码中硬编码远端 Tool 名和参数 Schema：

```text
RoutingPolicy --deterministically selects--> billing Agent
  -> MCP client connects to the fixed billing-mcp service
  -> list_tools
  -> validates the discovered catalog
  -> passes the valid Tool name / description / JSON Schema to billing Agent
  -> Agent selects and calls one of those discovered Tools
```

这里“LLM 发现 Tool”的准确含义是：MCP 客户端负责协议层的 `list_tools` 通信，随后将服务端实时返回的 Tool 描述和 JSON Schema 提供给 Billing Agent 的 LLM。LLM 不需要知道 Docker 地址，也不应自行连接任意 MCP Server。

这不会破坏“路由不能错”的要求：

- `RoutingPolicy` 仍只决定是否启动 `billing` Agent，LLM 不能新增或替换 Agent。
- 发现只会连接固定 Compose 服务名 `billing-mcp`，不会扫描网络或连接用户指定地址。
- `billing-mcp` 只能发布只读 Billing Tool；客户端拒绝非只读、缺少 Schema、重复名称或不符合 Billing 域声明的 Tool。
- 发现失败、目录为空或 Schema 不合法时，不向 LLM 提供 Tool，记录为账务事实无法核验，再由证据/转人工链路处理。

个人 Demo 初始 MCP Server 只发布 `get_plan`、`get_usage`、`get_invoice`。后续在该 Server 新增符合只读 Billing 约束的 Tool 时，Agent 不需要修改硬编码 Tool Schema 即可发现和使用它。

### 3. 当前实现状态

| 项目项 | 当前状态 | 实现说明 |
| --- | --- | --- |
| 后端镜像 | 使用 `backend/Dockerfile` | 非 root 运行并提供 API 健康检查。 |
| 基础设施 | 提供 `deploy/compose.infra.yml` | 作为可选完整依赖，不直接承担应用编排。 |
| API 容器 | `compose.yaml` 已提供 API、迁移、数据库、Redis、对象存储、搜索、Kafka、Demo seed 和 Billing MCP | 当前完整个人 Demo 主链路。 |
| Worker 容器 | 已接入独立 Kafka Worker 服务 | 处理上传后的文档索引、重试和 DLQ。 |
| 前端容器 | 多阶段前端 Dockerfile、Nginx 代理和 Compose 服务 | 宿主机 `9527` 访问。 |
| Billing MCP Client | 支持 MCP `list_tools`、目录校验和动态 Tool 注册 | 已在运行中的 API 容器内完成真实目录发现。 |
| Billing MCP Server | `billing_mcp_server.py` 只暴露三条账单 Tool | 已通过真实 HTTP MCP 边界发现并调用 `get_plan`。 |
| 现有 `mcp_server.py` | 只暴露知识库 Tool | 不复用为 Billing MCP，避免额外 Tool 暴露。 |

### 4. 服务边界

| 服务 | 进程 | 对宿主机开放 | 职责 |
| --- | --- | --- | --- |
| `api` | FastAPI / WebSocket | `8000` | 客服 Agent、路由、Tool Runtime、最终答复。 |
| `billing-mcp` | Streamable HTTP MCP | 不开放，仅 `expose: 8011` | 只读套餐、用量、账单查询。 |
| `mysql` | MySQL | 开发模式可选 `3306` | Demo 业务数据、会话、工单和账单表。 |
| `worker` | Kafka consumer | 不开放 | 异步文档处理；仅 Kafka 模式启用。 |
| `frontend` | 静态 Web/Nginx | `9527` | 浏览器入口。 |
| `demo-seed` | 一次性初始化脚本 | 不开放 | 创建演示账单/API 数据并索引 9 份 Demo 知识文档。 |
| `redis` | Redis 7.4 | 不开放，仅内部访问 | 路由/记忆缓存、限流和 WebSocket 协调。 |
| `minio` | MinIO | 不开放，仅内部访问 | 上传对象持久化。 |
| `elasticsearch` | Elasticsearch 8.17 | 不开放，仅内部访问 | 混合向量/关键词 RAG 检索。 |
| `kafka` | Kafka 3.9 KRaft | 不开放，仅内部访问 | 文档异步处理队列、重试和 DLQ。 |

当前完整个人 Demo 使用这些镜像：`mysql:8.4`、`redis:7.4-alpine`、`minio/minio:latest`、`docker.elastic.co/elasticsearch/elasticsearch:8.17.0`、`apache/kafka:3.9.2`、本地构建的 `paismart-backend:dev` 和 `paismart-frontend:dev`。`migrate`、`demo-seed`、`api`、`billing-mcp` 和 `worker` 复用后端镜像；测试 profile 额外构建 `paismart-backend-test:dev`。

禁止把 `billing-mcp` 映射为宿主机端口；API 必须使用服务发现地址 `http://billing-mcp:8011/mcp`，不能使用 `localhost`。

### 5. 本地 Demo 的 MCP 配置

`api` 和 `billing-mcp` 使用同一个 Docker 网络以及同一个 MySQL 数据源。Billing MCP 只接受 API 注入的 `customer_id`，并使用它读取对应的 Demo 账单记录。

API 容器的环境变量：

```env
DATABASE_URL=mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
BILLING_MCP_ENABLED=true
BILLING_MCP_URL=http://billing-mcp:8011/mcp
BILLING_MCP_TIMEOUT_SECONDS=10
# Demo 内部网络默认不发送 bearer；变量名仍保留，以便日后升级鉴权。
BILLING_MCP_BEARER_TOKEN_ENV=BILLING_MCP_TOKEN
```

Billing MCP 容器的环境变量：

```env
DATABASE_URL=mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
```

个人 Demo 的安全边界是 Docker 内部网络加“不映射 Billing MCP 端口”。这不等同于生产认证：如果未来对宿主机或其他网络开放 `billing-mcp`，必须加入服务间 bearer/mTLS 验证，并由 MCP Server 验证调用方身份。

### 6. 当前 Compose 轮廓

```yaml
services:
  mysql:
    image: mysql:8.4

  redis:
    image: redis:7.4-alpine

  minio:
    image: minio/minio:latest

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0

  kafka:
    image: apache/kafka:3.9.2

  worker:
    image: paismart-backend:dev
    command: ["python", "-m", "app.workers.file_processor"]

  demo-seed:
    image: paismart-backend:dev
    command:
      - sh
      - -c
      - >-
        python -c "import asyncio; from app.db.init_db import init_db; asyncio.run(init_db())"
        && python scripts/seed_support_demo.py --username admin
        && python scripts/seed_demo_knowledge.py --username admin

  api:
    image: paismart-backend:dev
    environment:
      DATABASE_URL: mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
      REDIS_URL: redis://redis:6379/0
      STORAGE_BACKEND: minio
      MINIO_ENDPOINT: minio:9000
      SEARCH_BACKEND: elasticsearch
      ELASTICSEARCH_URL: http://elasticsearch:9200
      TASK_MODE: kafka
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      BILLING_MCP_ENABLED: "true"
      BILLING_MCP_URL: http://billing-mcp:8011/mcp
    ports: ["8000:8000"]
    depends_on:
      mysql:
        condition: service_healthy
      billing-mcp:
        condition: service_started

  billing-mcp:
    image: paismart-backend:dev
    command: ["python", "billing_mcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8011"]
    environment:
      DATABASE_URL: mysql+aiomysql://root:paismart@mysql:3306/PaiSmart
    expose: ["8011"]
    depends_on:
      mysql:
        condition: service_healthy

  frontend:
    image: paismart-frontend:dev
    ports: ["9527:80"]
```

最终文件使用 Compose `env_file` 或 Docker secrets 传递密钥；示例不写入真实 LLM Key 或 JWT Secret。

### 7. 当前实现组成

#### 容器基础

1. 根级 `compose.yaml` 是当前入口；`compose.infra.yml` 仅作为手动基础设施来源。
2. MySQL、Redis、MinIO、Elasticsearch 和 Kafka 使用健康检查及命名数据卷。
3. API、Worker、RAG、对象存储和队列地址统一使用 Compose 服务名。
4. 后端和前端均有 `.dockerignore`；后端镜像使用非 root 用户，迁移和 Demo 数据初始化由一次性服务执行。

验收：`docker compose up --build` 后，宿主机可访问 API 健康检查；重启容器后 MySQL 数据仍存在。

#### 独立 Billing MCP

1. `billing_mcp_server.py` 提供独立 MCP Server。
2. Server 只注册 `get_plan(customer_id)`、`get_usage(customer_id, month?)`、`get_invoice(customer_id, month?)`。
3. 每个 Tool 提供名称、描述和输入 Schema，并调用只读 billing domain service。
4. Billing Agent 被路由选中后，API Client 执行 `list_tools`，校验目录并把实时 Schema 提供给 Agent。
5. Shared Scheduler 使用发现到的 Tool 名和 Schema 执行 `call_tool`，不维护远端 Tool 的硬编码 Schema。
6. 知识库 `mcp_server.py` 不复用为 Billing MCP，Server 不注册退款、套餐变更、工单或知识库 Tool。
7. Compose 启动 `billing-mcp`，API 通过 `http://billing-mcp:8011/mcp` 调用它。

验收：Billing Agent 只能看到 `list_tools` 实际发现且校验通过的 Billing Tool；MCP 初始目录恰好列出三个远端 Tool；一个用户不能从另一个用户的 `customer_id` 读取账单（Demo 阶段通过 API 注入约束和测试覆盖）。

#### 端到端验证

1. 独立 `test` Compose service 使用 Dockerfile 的 `test` target 安装 `requirements-dev.txt`，运行 Agent/MCP 回归。
2. Billing MCP → MySQL 的 Compose E2E 覆盖真实 `list_tools`、套餐、用量和账单查询，测试数据结束后清理。
3. 回归覆盖 Billing 高风险请求：先读事实，再形成证据，再创建人工工单。
4. 回归验证 `billing-mcp` 不暴露宿主机端口，API 容器不使用 `localhost:8011` 访问它。

架构 E2E 覆盖两个完整链路：

- 三个专业 Agent 同时命中时的并发调度、独立上下文和每个 Agent 的 Tool 所有权。
- 前端 WebSocket 从请求进入、Tool 事件、证据摘要、人工决策到最终回答的完整闭环。

这两类测试使用固定模型输出即可，不需要 `LLM_API_KEY`；真实 LLM 行为由独立的 `--live` 评测负责。

先执行已接入的 Agent/MCP/WebSocket 回归（当前 11 项核心用例）：

```bash
docker compose --profile test run --build --rm test
```

在同一 Compose 测试环境中运行所有现有 pytest：

```bash
docker compose --profile test run --build --rm test pytest -q tests
```

验收重点：MCP 不可用时客服答复诚实降级，并按证据规则转人工。

#### 完整 Demo 服务

1. 前端使用多阶段 Dockerfile、Nginx API/WebSocket 代理与 `frontend` 服务。
2. `TASK_MODE=kafka` 使用独立 `worker` 服务，支持文档重试和 DLQ。
3. MinIO 和 Elasticsearch 为上传存储与父子切分 RAG 提供完整后端。
4. `demo-seed` 一次性服务自动初始化管理员关联的 Billing/API 演示数据并索引内置知识库。

验收：当前个人 Demo 启动 `mysql + redis + minio + elasticsearch + kafka + worker + migrate + demo-seed + api + billing-mcp + frontend`。

### 8. 不做事项

- 不把三个专业 Agent 拆成三个 Docker 服务；它们是同一 API 进程中的并发 LLM 规划单元。
- 不把 API 诊断、Knowledge、工单或退款能力接入 Billing MCP。
- 不让 Billing MCP 直接产生客服答复、决定路由或创建人工工单。
- 不把全部 API、Worker、MCP Server 塞进一个容器。
- 不把 LLM Key、JWT Secret 或未来 MCP 凭据提交到仓库。

### 9. 当前验收结果

当前实现满足以下条件：

1. 通过一条 Compose 命令启动完整个人 Demo；浏览器可访问前端，API 和内部依赖健康运行。
2. Billing Agent 在每次独立工作前，或在有缓存失效时，通过 MCP `list_tools` 获得可调用 Tool 目录；不是读取本地硬编码远端 Schema。
3. Billing Agent 已实际跨容器调用本地 Billing MCP，而非回退本地 Tool 实现；MCP 初始目录恰好为三个只读账单 Tool。
4. Agent 运行图、独立 Agent 取证、证据后转人工和最终答复顺序保持不变。
5. Compose 内 E2E 测试服务与现有 Agent/MCP/WebSocket 回归入口已配置；当前核心 11 项已通过，包含三 Agent 并发和前端 WebSocket 完整链路。

全量 pytest 已在无 `LLM_API_KEY` 环境通过 **114 项**，包含三 Agent 独立并发 E2E、前端 WebSocket 完整 E2E 和父子 RAG 指标回归。


<a id="production"></a>

## 生产运行边界

原文档为 `PRODUCTION.md`。

### 1. 生产启动

建议：

```env
APP_ENV=production
DATABASE_AUTO_CREATE_DEV=false
```

必须替换默认 JWT Secret 和 bootstrap admin password，或直接关闭 bootstrap admin。

生产数据库结构只通过：

```bash
cd backend
alembic upgrade head
```

演进。

### 2. 客服 Handoff 数据

当前 Alembic 包含 `support_handoffs` 表迁移。人工升级是生产业务数据，不是临时 Agent Trace。

客户接口：

```text
GET /api/v1/support/handoffs
GET /api/v1/support/handoffs/{handoff_id}
```

管理员接口：

```text
GET   /api/v1/support/admin/handoffs
PATCH /api/v1/support/admin/handoffs/{handoff_id}
```

工单更新支持 status、assignedTo、resolutionNote。生产接 CRM/Ticket System 时，建议通过明确 Adapter/MCP 做同步，不要让 LLM 直接操作底层数据库。

### 3. Full Infrastructure

```bash
docker compose -f deploy/compose.infra.yml up -d
```

推荐：

```text
MySQL          客服会话、工单、trace、usage
Redis          多实例限流/共享瞬态状态
MinIO          客服知识文档
Elasticsearch  大规模客服知识检索
Kafka          durable document processing
```

### 4. Detached Generation

Generation Task 与 WebSocket 解耦：

```text
Generation
├── durable GenerationState snapshot
└── event subscribers
```

客户网络断线只取消 socket subscription，不直接取消 LLM/Tool generation。重连后读取 snapshot 并继续订阅。

新客户端发问时显式提交 `conversationId`，服务端验证所属账号及活动状态。旧纯文本客户端仍按账号最近活动会话选择，多标签页应使用新版结构化消息。

每个活动生成每 10 秒更新心跳。启动与每 30 秒的恢复扫描仅回收超过 120 秒无心跳的 `PENDING` / `STREAMING` 任务。完成、取消和回收用条件更新争用终态，预留结算或释放与相关持久状态在同一事务提交，迟到完成无法覆盖已取消或中断的任务。

跨实例停止通过数据库 `CANCELLED` 状态传播。实时事件队列仍在进程内，连接换到其他副本时需要依赖权威快照校准。共享实时事件传输的剩余工作见[债务台账](../../MAINTENANCE.md)，回归见[候选验收](../reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。

### 5. Billing MCP

本项目只有 Billing MCP；它只处理套餐、用量和账单的只读事实：

```text
PaiSmart Agent
 -> Tool Runtime
 -> MCP Client Adapter
 -> Billing MCP Server
```

要求：

- token/secret 使用环境变量或 Secret Manager。
- 仅暴露 `get_plan`、`get_usage`、`get_invoice`。
- Tool 自身继续执行 scope / role / risk policy。
- 只读 Tool 可以并行；写操作不能因为 MCP 化而绕过资源冲突和授权。
- 不把远程 MCP 返回文本视为系统指令。

个人 Demo 通过 Docker 内部网络隔离 Billing MCP，不映射 MCP 端口到宿主机；若未来开放网络访问，必须开启 Bearer Auth 并映射真实用户/scopes。


#### Billing MCP Adapter

生产环境建议保持 Agent-facing Tool contract 稳定：

```text
Billing Agent
 -> query_plan / query_usage / query_bill
 -> Billing MCP Adapter
 -> Billing MCP Server
```

配置：

```env
BILLING_MCP_ENABLED=true
BILLING_MCP_URL=http://billing-mcp:8011/mcp
BILLING_MCP_BEARER_TOKEN_ENV=BILLING_MCP_TOKEN
BILLING_MCP_TIMEOUT_SECONDS=30
```

Billing MCP 仅允许 `get_plan`、`get_usage`、`get_invoice`。个人 Demo 中 `customer_id` 由 API 的已认证用户上下文注入；退款、套餐变更和支付争议只能在证据汇总后转人工。完整容器化步骤见 [DOCKER_AND_LOCAL_BILLING_MCP_PLAN.md](OPERATIONS_2026-11-19.md#billing)。

### 6. 客户数据与知识库边界

生产环境应明确区分：

```text
Knowledge / RAG
= policy, FAQ, product manual, troubleshooting guide

Billing MCP
= current customer's plan, usage and invoice facts only
```

不要把大量客户私有业务状态直接索引进通用 RAG 来替代授权业务 API。

### 7. Kafka Retry / DLQ

```env
KAFKA_RETRY_ATTEMPTS=3
KAFKA_RETRY_BACKOFF_SECONDS=2.0
KAFKA_DLQ_TOPIC=file-processing-dlq
```

毒消息经过 retry/DLQ 后再提交 offset，DLQ 必须有监控。

### 8. Token / Rate Limit

`app/accounting/` 统一记录 LLM/Embedding usage 和 balance ledger。Provider 提供真实 usage 时优先使用真实值。

登录/注册支持 Redis 多实例限流；Redis 不可用时的本地 fallback 不能视为跨实例保证。

### 9. Observability

在 Langfuse 查看问答路由、RAG 检索、模型生成和工具调用。配置步骤见 [Langfuse 链路追踪](OPERATIONS_2026-11-19.md#langfuse)。

```env
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=<instance-base-url>
LANGFUSE_PUBLIC_KEY=<project-public-key>
LANGFUSE_SECRET_KEY=<project-secret-key>
```

客服生产环境可从 Langfuse 追踪检查：

```text
answer latency
LLM/tool failure rate
handoff rate
handoff creation failure
troubleshooting repeat count
RAG no-result rate
account-data abstention rate
```

### 10. 发布前检查

```text
[ ] alembic upgrade head
[ ] 非默认 JWT / admin password
[ ] CORS 只允许真实客服前端
[ ] Redis / ES / Kafka / MinIO credentials 已修改
[ ] MCP user/scope/allowedTools 最小权限
[ ] 订单/支付等客户事实只通过授权业务 Tool/MCP 查询
[ ] create_support_handoff 实际写库可用
[ ] pytest 通过
[ ] customer-service Skill / Answer benchmark 通过
[ ] /health 正常，抽样问答在 Langfuse 中可按 generation_id 查询
[ ] Kafka DLQ 有告警
[ ] DB、工单和对象存储有备份策略
```


<a id="staging"></a>

## 预发布逐步验收

原文档为 `CONTEXT_STAGING_ACCEPTANCE_RUNBOOK.md`。

历史演练镜像为 `paismart-backend:context-rc-20261118`。每次发布先填写待发布提交、对应构建镜像及摘要，当前源码候选见[候选验收](../reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。按 **锁定产物 → 迁移 → 影子 → 验收白名单 → 故障与回滚 → 签字** 执行。验收窗口仅接入专用测试账号和合成数据，外部用户流量保持为零。

当前状态：本机生产配置预演已通过。客服工程候选 `paismart-backend:erp-stages-1-2-20261118` 已按本手册在本机隔离环境复验，报告保存其完整镜像 ID、真实模型对照、告警和回滚证据。下面的步骤需要在目标预发布环境重新执行。目标环境的依赖、告警渠道、值守接手和放量控制待签验。[客服工程候选验收](../reports/ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md) · [上下文初版预演](../reports/CONTEXT_RELEASE_ACCEPTANCE.md)

### 0. 开场检查与证据目录

开始前由发布负责人填写本表。每一步都记录北京时间、执行人、结果和证据链接。证据仅保留排查需要的脱敏标识，密钥通过部署平台注入。

| 项目 | 本轮填写 |
| --- | --- |
| 验收编号、时间窗、工单 | 待填写 |
| 预发布部署入口、服务名、镜像仓库 | 待填写 |
| 前端入口、API、独立探测运行位置 | 待填写 |
| MySQL、Redis、检索服务、Billing MCP、Langfuse 项目 | 待填写 |
| 冻结题集版本或校验和、评分器版本、知识版本、模型及上下文配置 | 待填写 |
| 合成租户 A/B、账号、验收白名单、测试账单和工单队列 | 待填写 |
| 发布负责人、应用值守、数据库值守、实际通知渠道 | 待填写 |
| 前一稳定版本及部署修订、回滚入口、备份位置及恢复目标 | 待填写 |
| 观察窗、指标口径、阈值、允许停机和恢复目标 | 待填写 |

证据目录建议按验收编号保存镜像核对、迁移与恢复、影子、长会话、冻结评测、故障、告警、回滚和签字九组材料。测试账号预先核对额度，历史长会话首跑曾被测试账号的 LLM 余额限制拦截。确认测试账单和工单只落入预发布数据范围，通知进入约定的演练渠道。

### 1. 锁定候选镜像

- 已在本机预演确认的镜像 **ID** 为 `sha256:ced4021a0dc3ab114b041f5b521859ca780b0f46d7b6b2d1497727cfbd5e265d`。交付到镜像仓库后另记仓库 **RepoDigest**，部署引用固定为 `<仓库>/<镜像>@sha256:<仓库摘要>`。本机镜像 ID 和仓库 manifest 摘要在各自位置核对。涉及多架构镜像时同时记录目标平台和平台 manifest。
- 在目标运行节点拉取指定摘要，核对部署模板、迁移任务和实际容器所用产物。容器直接从候选镜像启动，应用源码无宿主机挂载。核对当前部署修订和回滚修订都可用。
- Docker 环境可以用下列命令取证。占位符先替换成目标环境实际值。

```powershell
docker image inspect paismart-backend:context-rc-20261118 --format '{{.Id}} {{json .RepoDigests}}'
docker image inspect <仓库>/<镜像>@sha256:<仓库摘要> --format '{{.Id}} {{json .RepoDigests}}'
docker inspect <预发布API容器> --format '{{.Image}} {{.Config.Image}}'
```

通过条件：镜像来源、仓库摘要、运行镜像和回滚修订可追溯。若产物或配置变更，记录新候选版本并重新确认受影响的验收项。[本机镜像证据](../../../backend/data/context-system/stage4-final-image.txt)

### 2. 数据库迁移和恢复验证

1. 在预发布库准备至少两个迁移前会话，其中一个包含后续要续办的原请求和用户纠正。通过正式历史入口记录会话 ID、消息顺序和消息数。记录当前 Alembic 版本和备份时间。
2. 按目标环境策略备份，并用单独的恢复库还原。检查恢复库版本、抽样会话和原消息，记录恢复耗时、被恢复的数据时间点和恢复操作人。
3. 用候选镜像启动一次迁移任务，使用受控的预发布数据库连接。在应用工作目录执行下列命令。迁移作业只启动一份。有异常时暂停后续步骤，保存迁移输出并核对数据库当前状态。

```text
alembic current
alembic heads
alembic upgrade head
alembic current
```

4. 当前候选的预期迁移为 `0015 → 0016_conversation_context_state`。核对当前 revision 与候选镜像的 head 一致，核对新增 `conversation_context_states` 表。以测试账号再次打开迁移前会话，逐项检查原始消息和历史回执。
5. 准备好两套恢复选择。读策略异常优先切回旧读取。数据库结构或数据异常按已验证的备份恢复流程处理，由数据库值守评估恢复点之后的消息、计费和工单如何保全与核对。

证据：备份引用、恢复报告、迁移前后 revision、抽样历史差异、迁移任务退出状态。[迁移文件](../../../backend/alembic/versions/0016_conversation_context_state.py) · [生产部署说明](OPERATIONS_2026-11-19.md#production)

### 3. 影子模式

显式设置以下值，避免候选镜像的默认开关影响阶段顺序。通过目标平台滚动部署，在每个 API 副本核对有效配置。

```dotenv
APP_ENV=production
CONTEXT_SYSTEM_ENABLED=false
CONTEXT_SHADOW_ENABLED=true
CONTEXT_PROGRESS_ENABLED=false
```

- 从正常前端或正式 HTTP/WebSocket 入口登录，先跑健康基线，再使用迁移前历史和新会话发起超窗口追问、纠正、切换请求和多请求澄清。每条记录生成 ID、完成状态、工具调用和相关业务记录。
- 通过同一生成 ID 在 Langfuse 查 `customer_service.question` 根观测，核对影子范围差异、候选时延、回查和裁剪元数据。抽样比较最终回复与旧路径、工具参数与实际工具结果，确认影子候选只影响观测。
- 在验收实例内演练影子超时或失败，核对正式回复仍完成、候选状态异常可定位、没有多余写操作。逐条解释样本中出现的范围和字段差异。
- 通过条件：真实入口和独立探测健康，样本的影子差异和超时均能解释，追踪未导出原始问题、回复正文、实体值、工具参数或业务数据。影子样本、差异和耗时有证据可回查。

### 4. 测试白名单切换与质量复测

开关作用于应用进程。使用独立预发布实例或网关将验收白名单路由到启用上下文的实例。通过白名单内、外各一个请求确认路由策略，再在验收实例设置 `CONTEXT_SYSTEM_ENABLED=true`、`CONTEXT_SHADOW_ENABLED=false`。如本轮要启用进度摘录，在单独一轮打开 `CONTEXT_PROGRESS_ENABLED=true` 并记录有效配置。

#### 4.1 正式入口长会话

固定测试序列和预期。跨窗口场景同时超过 20 条历史消息及 12,000 字符，并通过裁剪观测确认原始锚点已滑出近期窗口。

| 场景 | 操作与判定 |
| --- | --- |
| 老会话续办 | 先记录请求号、接口、版本和诊断 ID，跨窗口后问「继续查这个请求」。应定位原请求、回查原始片段、沿用诊断 ID。 |
| 最新纠正 | 将 v1 更正为 v2，插入无关轮次，重启 API 后再追问。工具参数及答复沿用 v2。补做并发或迟到旧轮次，检查持久状态仍为 v2。 |
| 作用范围隔离 | 在同一会话明确切换到另一请求，再分别用同账号新会话和另一账号追问。旧请求字段、诊断和工具结果不能串入。 |
| 歧义澄清 | 一个问题同时给两个请求号，核对先要求选定请求且无诊断工具调用。选定后仅处理指定请求。 |
| 业务事实重查 | 先查询测试账期，再在受控账单夹具中修改该期的用量后追问。核对复用账期、重调 Billing MCP、展示新值及本轮回执。 |
| 工单创建与重试 | 用独立工单请求在自然入口确认提交，捕获本轮回执，按实际入口重试并查询落库。核对同一逻辑工单只有一条，回复与持久结果一致。 |
| 进度摘录 | 使用固定的四项排障尝试和一项待查，滑出窗口后问进度。启用组恢复 5/5 项，并保留用户反馈来源。记录关闭组、首段延迟和历史预算供对照。 |
| 引用与预算 | 用跨窗口的文档追问检查主要结论和例外，逐项打开正式引用来源并核对支撑。记录上下文组装耗时、裁剪、回退及最终完成状态。 |

每组保存合成账号别名、会话和生成 ID、服务日志、回执、业务落库增量、根追踪及复测结果。对写动作比较前后扣费记录和工单记录，记录预期增量、实际增量及幂等关联键。

#### 4.2 冻结 60 条和六类入口抽验

- 使用仓库固定的 60 条、30 对，每题使用新会话。沿用 `deepseek-flash`、显式 `LLM_THINKING_ENABLED=false` 和现有上下文预算。先检查流式首段、完成事件和工具调用，再运行冻结题。记录供应商、思考设置及测试额度。
- 从 `backend` 目录运行 `python scripts/run_phase_a_graph.py <结果文件.jsonl> --smoke-first` 可执行候选代码的生产图评测。正式入口抽验另走目标环境 HTTP/WebSocket，六类各一对、共 12 条。生产图结果与入口结果分别留档。
- 报告须单列单题通过数/60、成对通过数/30、逐项引用通过数/必需项数、实际输出中引用支撑率、必答覆盖、各类别结果、截断与原因、运行失败与原因。一对只有两侧均满足目标行为才算通过。漏答和缺引用均列到对应主张，原结果与复算结果分别保留。
- 发布门槛：成对至少 27/30、引用支撑率至少 95%、关键安全反例为 0。逐项引用以既有 38/38 为对照，任何退化逐项列出并在签字前处理。入口抽验和上表关键行为全部通过。出现失败时定位到入口、上下文组装、工具、持久化、模型或评分器；修复后重跑失败链路及受影响的完整门禁批次。

[固定题集](../../../backend/eval/customer_service/phase_a_release.jsonl) · [生产图评测入口](../../../backend/scripts/run_phase_a_graph.py) · [候选基线与真实模型记录](IMPLEMENTATION_2026-11-19.md#context)

### 5. 依赖故障与业务对账

每种故障先跑健康基线，确认影响范围限制在验收实例。注入后通过正式入口验证，解除注入后在原会话重查，并用新会话复测。同一写操作用同一逻辑标识比对回执和落库。

| 注入 | 故障中核对 | 恢复后核对 |
| --- | --- | --- |
| 预发布共享 Redis 不可达 | 生产共享限流保留拒绝行为，检查登录 503 和已认证的新 WebSocket 1013；核对是否产生意外业务写入。 | Redis 恢复后重走登录、WebSocket、续办和纠正。若另有独立的纯缓存故障验证点，单独记录 SQL 回退与 Redis 重建。 |
| 搜索 503、正常无命中 | 分别记录错误与空结果，回复无虚假引文，无跨租户命中。 | 同题复测可检索、可打开引用。 |
| Billing MCP 全部超时 | 账单追问有可解释的失败结果，账表和扣费流水没有预期外变化，答复未将旧金额用作当前值。 | 重新查询实际值，核对回执和扣费增量。 |
| 工单提交前失败、提交后回执丢失 | 前者核对无工单且无成功回执；后者核对实际写入、首次回执缺失及受控重试。 | 同一逻辑请求最终工单数符合预期，客户端回执与落库工单匹配。 |
| Langfuse 写入中断、查询不可达、导出积压 | 分开注入。记录业务仍可完成的样本。只断写时独立探测可报 `trace_missing`；查询不可达时可报 `trace_check_unavailable`。积压时记录根追踪入库延迟和异常触发。 | 查到恢复后的新根追踪，记录旧追踪实际补齐或永久缺失情况，核对恢复后的业务和告警。 |

日常阈值单独记录首段延迟 P95、生成失败率、质量门异常、引用异常及追踪缺口。每项填时间窗、样本量下限、基线、触发阈值和负责人。样本不足时标记「待验证」。当轮需验证的阈值以发布负责人事前确认值为准。[现有指标与建议口径](../plans/PRODUCTION_READINESS_PLAN.md)

### 6. 独立探测、通知送达和值守接手

探测部署在业务 API 和 Langfuse 之外，使用专用账号、目标 Langfuse 读取权限和约定的通知渠道。变量及密钥注入见 [Langfuse 运维说明](OPERATIONS_2026-11-19.md#langfuse)。使用该预发布环境独享的持久 SQLite 状态文件，探测每分钟串行运行一次。发布控制器读取同一状态并以 `status` 退出码守住白名单扩大或后续放量动作。

在 `backend` 下执行，先替换占位符。命令中的工单和身份与当班记录对应。

```text
python scripts/observe_rollout.py --state <预发布状态文件> probe
python scripts/observe_rollout.py --state <预发布状态文件> status
python scripts/observe_rollout.py --state <预发布状态文件> ack --incident <事件ID> --operator <当班人员标识>
python scripts/observe_rollout.py --state <预发布状态文件> resume --incident <事件ID> --operator <当班人员标识>
```

1. 健康基线应有业务完成记录、可查询根观测、`status` 退出 0。核对独立探测时间与发布检查时间。
2. 注入故障使探测异常。首次失败时 `status` 应退出 2，并现场证明扩大操作被拦截。连续三次失败或不可核验时应创建事件并锁定。另验证健康探测超过 300 秒即失去扩大资格。
3. 通过实际演练渠道收取通知。保存事件 ID、接收端受理时间、通知落地消息和当班人员接手时间。演练首次回执丢失时，核对重试沿用同一事件 ID 和 `Idempotency-Key`，接收端仅生成一条事件。
4. 当班人员确认收到并接手后执行 `ack`。恢复依赖，连跑两次健康探测，验证此时仍暂停。授权值守核对业务落库和追踪后执行 `resume`，再查 `status`。
5. 单独演练严重事件的即时锁定，例如 `hold --reason context_scope_violation`。其他即时锁定情形包括过期业务事实、最新纠正丢失、越权、凭据泄露、重复扣费、重复工单或虚报写入成功。聚合指标达到已批准阈值时使用 `metrics_threshold`。实际事件需要附业务证据并由当班人确认。

### 7. 回滚演练

| 顺序 | 操作与验证 |
| --- | --- |
| 1. 锁定 | 记录触发原因、生成 ID、影响面、开始时间与操作者。核对放量控制已暂停。 |
| 2. 切回旧读取 | 验收实例设 `CONTEXT_SYSTEM_ENABLED=false`、`CONTEXT_SHADOW_ENABLED=false`、`CONTEXT_PROGRESS_ENABLED=false`，滚动更新并保留 0016。核对所有副本的配置及正式历史入口。 |
| 3. 验证业务 | 检查健康、旧会话原始消息、当轮动作回执、账单及工单实际增量，确认进行中的操作已对账。保留回滚耗时和复核人。 |
| 4. 验证进一步恢复 | 若配置回滚不足，按预先填写的稳定修订和兼容检查结果演练镜像回退。涉及数据库恢复时先在独立库验证，然后由数据库值守评估进预发布库恢复所需的停写、恢复点和数据补偿。 |
| 5. 复位 | 只有修复或恢复证据齐全、当班已接手且达到门禁恢复条件后，才执行显式解锁。回到新读取策略需要重新通过受影响的验收项目。 |

### 8. 签字与小流量决定

| 签字项 | 审核角色 | 结论与证据 |
| --- | --- | --- |
| 候选摘要、迁移、恢复及版本回退 | 发布负责人、数据库值守 | 待填写 |
| 影子、长会话、作用范围、真实入口及业务落库 | 应用负责人 | 待填写 |
| 冻结 60 条、30 对、逐项引用、截断及失败诊断 | 评测负责人 | 待填写 |
| Redis、Langfuse、实际告警、当班接手、即时暂停和恢复 | 当班值守 | 待填写 |
| 外部流量状态、未关闭缺陷及最终发布决定 | 发布负责人 | 待填写 |

只有目标环境各项都通过、门禁当前健康、严重问题已关闭且审批明确记录后，才能提交小流量开启决定。此次验收结束时默认维持零外部流量。若另行批准，从固定白名单或网关已批准比例开始，现有规划建议从 5% 起步，至少观察一个完整业务日再评审扩大。开流前写明实际比例、观察人、观察窗和停止条件；任何新异常按本手册暂停，恢复需重新核对门禁及发布决定。

签字记录需附最终结论「通过 / 待复测 / 阻断」、证据目录、遗留问题、下一次决策时间和实际签字人。
