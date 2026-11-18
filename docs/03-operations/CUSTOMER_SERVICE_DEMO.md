# 客服演示与正式入口验收

从项目根目录运行下列命令。Docker Compose 构建后端运行镜像，启动临时 API，轮询容器内的正式健康接口，执行两条演示并退出。离线服务无外部网络和宿主端口映射。每次使用空的证据目录，SQLite 和合成账号随容器清理。

```powershell
New-Item -ItemType Directory -Force backend/data/customer-demo | Out-Null
docker compose -f deploy/compose.customer-demo.yaml run --rm --build demo
Get-Content backend/data/customer-demo/summary.jsonl
docker compose -f deploy/compose.customer-demo.yaml down
```

Linux 或 macOS 将首行换成 `mkdir -p backend/data/customer-demo`，并执行 `export CUSTOMER_DEMO_USER="$(id -u):$(id -g)"` 以匹配证据目录所有者。每次复跑前归档旧目录，或将 `CUSTOMER_DEMO_EVIDENCE` 指向新的空目录。已有候选镜像时，将 `CUSTOMER_DEMO_IMAGE` 设为候选镜像标签并省略 `--build`。

- 无请求号演示使用三个合成账号、固定接口和 2026-11-18 的日志窗口。11 轮包含补时间、补错误码和纠正接口或时区。前 8 轮逐轮断言澄清项和零工具调用，后 3 轮各断言一次窗口统计，并核对接口、起止时间、状态码或空窗口以及零工单。
- 工单演示走真实登录、WebSocket、生成查询、诊断恢复和工单查询。核对普通工单成功、提交前失败后重试、提交后回执丢失时三个并发恢复，以及 API 进程重启后恢复原工单。另检查匿名读取、跨账号工单读取和诊断续办被拒绝。逐轮对照 SQLite 中的工单 ID 与正式接口回执。
- 离线替身提供分类和模型协议响应，路由、日志统计、写库、恢复与安全审查均由实际应用执行。证据保存在 `diagnosis.jsonl`、`handoff.jsonl`、`handoff-audit.log` 和 `server.log`。失败返回非零退出码，保留已经产生的证据。

## 显式真实模型模式

只在希望调用供应商时运行。预先在相同终端设置 `LLM_API_KEY`、`LLM_MODEL` 和 `LLM_BASE_URL`，然后选已构建的候选镜像和一个新目录。容器可以访问模型供应商，API 仍只监听容器回环地址。业务数据继续使用合成夹具。

```powershell
$evidence = New-Item -ItemType Directory backend/data/customer-demo-real
docker run --rm --user 0 --tmpfs /app/data:rw,size=128m -e LLM_API_KEY -e LLM_MODEL -e LLM_BASE_URL --mount "type=bind,source=$($evidence.FullName),target=/evidence" --entrypoint python paismart-backend:customer-demo /app/scripts/run_customer_service_demo.py --real-model
Get-Content "$($evidence.FullName)/summary.jsonl"
```

快速 CI 以本机回环和全新的 SQLite 文件执行同一离线脚本，上传验收证据。
