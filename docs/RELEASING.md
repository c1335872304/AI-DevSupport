# 发布与审批

源码、CI、运行镜像和目标环境分别记录版本。代码候选状态见[验收报告](archive/reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)，当前剩余工作见[维护](MAINTENANCE.md)。

## 候选记录

| 项目 | 发布时记录 |
| --- | --- |
| 产物 | Git 提交、仓库镜像摘要、实际运行镜像和回退镜像 |
| 依赖 | 数据库 / Redis / ES / 存储 / Kafka / Billing MCP 及 Langfuse 的目标地址与状态 |
| 配置 | 模型、知识版本、Embedding 模型和维度、功能开关 |
| 数据 | 迁移前 revision、备份、恢复点及抽样会话与账本 |
| 值守 | 通知渠道、接手人员、流量控制器、观察窗口和批准范围 |

从待发布提交构建镜像，以仓库摘要绑定实际容器。历史报告中的镜像标签用于复查原演练，新的候选在本表记录自己的镜像与配置。

## 迁移和启动

生产配置使用 `APP_ENV=production`，关闭开发建表，替换默认 JWT Secret，并配置或关闭 bootstrap 管理员。密钥由部署环境注入。

在数据库副本验证升级和恢复，抽查迁移前会话、消息、诊断、工单与账本。暂停旧写入者后运行单份迁移作业，再启动新代码。

```text
alembic current
alembic heads
alembic upgrade head
alembic current
```

当前源码包含 `0020_remove_invite_codes`，以候选镜像的 `heads` 核对目标 revision。`0020` 移除邀请码表，降级只能重建空表，旧邀请码数据由备份恢复。切回旧镜像前确认其与当前结构兼容，并按恢复点核对新增业务记录。

已有 Demo 更新可按以下顺序操作，备份由目标环境的数据库和存储策略完成。

```powershell
docker compose stop api worker
docker compose build api worker billing-mcp frontend
docker compose run --rm migrate
docker compose up -d api worker billing-mcp frontend
docker compose ps -a
```

## 预发布验证

1. 用专用测试账号和合成数据验证登录、会话隔离、知识引用、诊断续办、账单读取及工单回执。
2. 首先以 `CONTEXT_SYSTEM_ENABLED=false`、`CONTEXT_SHADOW_ENABLED=true` 观察差异，再启用新上下文。进度摘录通过 `CONTEXT_PROGRESS_ENABLED` 单独配置。
3. 验证 Redis、检索、MCP 和追踪故障及恢复，核对生成终态、预留账本和工单记录。双副本启动和跨副本停止保留对应回归证据。
4. 在实际 Langfuse 查询根追踪，通知实际渠道并由当班人员确认接手，演练暂停、恢复及回滚。
5. 记录配置回滚、镜像回滚和数据库恢复各自的适用条件、耗时与数据核对结果，再完成签验。

本机演练和真实模型对照保存在[候选性能报告](archive/reports/ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md)。

## 放量与回滚

流量控制器接入[独立探测](OPERATIONS.md#observability)的 `status` 结果，要求最近 300 秒内健康且无暂停锁。首次异常即暂停扩大，连续三次失败或追踪不可核验时告警并锁定。跨范围串用、重复扣费、重复工单、越权或虚报成功等确认事件立即锁定。

解锁需要值守接手、连续两次健康及显式 `resume`。初始白名单或小流量范围、目标性能阈值和观察窗口沿用该次发布批准的记录。恢复后重新核对知识问答、账单、原工单、会话和新追踪。

配置或读取策略回滚保留原始业务记录。镜像和数据库回滚按已验证的兼容性与恢复点执行，恢复后对账新增消息、费用和工单。

<a id="approvals"></a>

## 审批与合成支付沙箱

启用 `REFUND_PREVIEW_ENABLED=true` 后，聊天页可以发起退款或关闭工单申请，管理员工单台展示审批队列。当前检查点使用持久化 SQLite 文件，跨主机共享检查点和自动恢复由维护台账跟踪。

```dotenv
REFUND_PREVIEW_ENABLED=true
REFUND_CHECKPOINT_PATH=data/refund-checkpoints.sqlite
REFUND_SANDBOX_URL=<synthetic-service-root>/sandbox
```

| 接口，前缀 `/api/v1/support` | 用途 |
| --- | --- |
| `POST /refund-requests` | 本人提交申请，携带 `requestKey`、原因及发票或同会话工单目标 |
| `GET /refund-requests` | 按 `conversationId` 读取本人会话申请 |
| `GET /refund-requests/{id}` | 本人查询原申请结果 |
| `GET /admin/refund-requests` | 管理员分页查询，待恢复记录优先，支持 `offset` / `limit` |
| `POST /admin/refund-requests/{id}/decision` | 保存批准或拒绝及说明 |
| `POST /admin/refund-requests/{id}/resume` | 管理员接手原决定并恢复执行 |

同一客户端请求键和相同输入返回原申请，改用不同输入返回冲突。决定先持久化再推进审批图，中断后由具备权限的管理员调用 `resume`，原决定、审批人和说明保留。恢复读取服务端原参数。

批准退款时，合成支付适配器通过查单核对金额、币种和退款 ID，再返回 `SANDBOX_REFUNDED`，结果未知时保持核对状态。服务只识别合成支付 `sandbox-paid-1`、人民币 15.00 元。未配置沙箱的普通申请批准后为 `APPROVED_PREVIEW`。批准关闭工单则更新原工单，并在同一事务保存关闭结果。

真实渠道、资格与金额快照、独立审批权限、自动对账及回调验签由[维护台账](MAINTENANCE.md)跟踪。验收入口见[测试](TESTING.md#demos)。
