# Langfuse 问答追踪

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

## 独立探测与放量门禁

在与业务 API 和 Langfuse 分开的进程上运行 [observe_rollout.py](../../backend/scripts/observe_rollout.py)。它用专用合成账号走正式登录、创建会话、WebSocket 和生成结果查询，核对完成事件与持久状态。随后用生成 ID 对应的根 trace ID 查询 Langfuse Observations v2。查询成功但没有根观测，以及查询服务不可用，分别记录为 `trace_missing` 和 `trace_check_unavailable`。状态和通知待发送记录保存在独立 SQLite 文件中。

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
