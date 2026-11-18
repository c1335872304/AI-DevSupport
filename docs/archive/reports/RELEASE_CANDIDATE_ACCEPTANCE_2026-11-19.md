# 源码候选验收

验收日期为 2026-11-19，当前源码功能基线为 `7c101b820a4ee70fe0cb90cea9a111d9a8f3b3a4`，交付分支为 `codex/support-demo-rag-ci`。三个 P1 修复起于 `99e7485`，当前基线另完成地域上下文和跨地域检索修复，可按单实例及合成支付范围封源码版本。[当前源码提交](https://github.com/c1335872304/AI-DevSupport/commit/7c101b820a4ee70fe0cb90cea9a111d9a8f3b3a4) · [PR #1](https://github.com/c1335872304/AI-DevSupport/pull/1)

## 修复与回归

| 问题 | 修复与验证 |
| --- | --- |
| 多标签页串会话 | 浏览器发送显式 `conversationId`，服务端核对账号和活动状态。两个 WebSocket 分别读取各自历史并写回对应会话，越权、归档和缺失会话被拒绝 |
| 多副本重启与结算 | 生成每 10 秒续心跳，超过 120 秒无更新的活动任务进入回收，每 30 秒扫描。完成、停止和恢复通过条件更新争用终态，余额与答复在同一事务提交。覆盖健康任务、过期任务、两个副本并发回收、迟到完成及结算/释放竞争 |
| 审批中断后换人恢复 | 管理员恢复接口读取原决定，保留原审批人和说明。覆盖决定落库后图推进中断、执行前中断、另一管理员并发恢复、退款回执一致、重复关单及队列分页 |

[隔离与结算回归](../../../backend/tests/e2e/test_release_p1_regressions.py) · [审批回归](../../../backend/tests/e2e/test_refund_approval_preview.py) · [额度回归](../../../backend/tests/agent/test_token_reservation.py)

同一交付同步了原工作目录已有的去邀请码改动及 `0020` 迁移。冻结评测和官方知识快照按原 SHA-256 清单核对，Git 属性覆盖 Phase A 输入、正文和原始快照。

## 验证结果

| 验证 | 结果与范围 |
| --- | --- |
| 完整后端离线回归 | 当前基线本机 420 通过、2 跳过，Fast CI 通过；跳过的 Compose Billing MCP 和 MySQL 跨进程用例由隔离集成覆盖 |
| 地域范围复验 | 新增 9 项回归，相关集合 56 项通过；同四题真实模型首跑 4/4 通过，24 条引用核验完成，见[前后证据](../evidence/N12_SCOPE_FAILURE_2026-10-20.md) |
| MySQL P1 专项 | 本机独立临时 MySQL 8.4 库，7 项通过，结束后清理测试库 |
| 前端 | 类型检查、生产构建通过，双账号退款及关单浏览器用例通过 |
| 业务演示 | HTTP 与浏览器确认同一退款回执，独立支付模拟账本只写一笔，原工单为 `CLOSED` |
| 隔离集成 | 真实 MySQL 迁移、Elasticsearch 跨存储与执行隔离、Billing MCP 协议验收通过 |
| 工程检查 | 文档目标、冻结数据、关键 Ruff 规则与 Compose 校验通过 |

提交对应的 push、pull request 两轮 Fast CI 和 PR 隔离集成均已完成。[Fast CI](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384682502) · [push 检查](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384665745) · [隔离集成](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384682348)

## 适用边界

本页确认源码候选和上述自动化验证。2026-11-18 的真实模型、成本与本机预发布对照见[候选性能验收](ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md)，其镜像和样本范围按原报告解释。当前源码对应的目标环境镜像、实际依赖、通知、流量与签验见[预发布手册](../../RELEASING.md)。

审批仍使用单机 SQLite 检查点和合成支付服务。地域范围问题已关闭。跨副本实时事件共享、跨主机审批及外部未知用量对账仍按[技术债务台账](../../MAINTENANCE.md)的升级条件处理，目标环境尚未因源码 CI 通过而自动获准放量。
