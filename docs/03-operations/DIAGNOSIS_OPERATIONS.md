# 诊断闭环运行与恢复

适用迁移：`0015_diagnosis_loop`。设计见[诊断闭环](../02-architecture/DIAGNOSIS_LOOP.md)，结果见[第三阶段验收](../04-testing/DIAGNOSIS_LOOP_ACCEPTANCE.md)。

## 升级与配置

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

## 排查任务

在诊断详情查看 executions、steps、workflow.decision、rechecks 和 transitions。PENDING/运行中可以点击“继续核查”；持有健康租约时不会接管。过期执行由扫描接管，逐步恢复。新问题 supersede 旧轮次后，旧任务会停止发布。

工单待提交时保留 HANDOFF_PENDING；重试使用原诊断身份，不另造请求。HANDED_OFF 只能由真实工单结果支持。复查被拒绝时检查归属、应用、接口与五分钟时间窗口，不能强行修改 RESOLVED。

历史日志没有请求时观测属于正常不确定性。`seed_support_demo.py` 只为新建的模拟事件同步创建观测，不回填已有日志，也不应为演示清空现有知识库。

## 独立复现

在 backend 运行 `python scripts/phase3_acceptance_server.py`，使用独立 `data/phase3-ui.sqlite`，API 18036，测试账号 loopaccept / LoopAccept123；每次新建带唯一前缀的验收会话，禁用真实模型/编码。另运行 `python scripts/verify_phase3_api.py` 验证真实 HTTP，报告写入 checkpoints。请在启动后五分钟内提交夹具新请求；超时重新启动生成新夹具。

前端进程环境设 VITE_SERVICE_BASE_URL=http://127.0.0.1:18036/api/v1，VITE_OTHER_SERVICE_BASE_URL 包含 api 和 ws://127.0.0.1:18036，再运行 Vite 独立端口19537。登录后选“第三阶段闭环验收 ui”，从 fixture JSON 取新请求号，提交复查并观察“已解决”。此服务不是生产启动命令，不连接正式知识库。

`PHASE3_TEST_MYSQL_URL` 仅指向专用测试库后运行 `pytest tests/agent/test_diagnosis_loop.py`。故障注入覆盖调用后未落库、落库后中断、交接意图后中断和提交确认丢失；这些是固定测试场景，不代表生产长时负载结论。
