# 源码候选验收

验收日期为 2026-11-19，前序 P1 与地域修复基线为 `7c101b820a4ee70fe0cb90cea9a111d9a8f3b3a4`，本轮在其后完成下述五项债务关闭，最终交付版本以本 PR 最新提交记录为准，交付分支为 `codex/support-demo-rag-ci`。三个 P1 修复起于 `99e7485`，当前基线另完成地域上下文和跨地域检索修复，可按本页已验证范围及合成支付范围封源码版本。[前序源码提交](https://github.com/c1335872304/AI-DevSupport/commit/7c101b820a4ee70fe0cb90cea9a111d9a8f3b3a4) · [PR #1](https://github.com/c1335872304/AI-DevSupport/pull/1)

## 修复与回归

| 问题 | 修复与验证 |
| --- | --- |
| 多标签页串会话 | 浏览器发送显式 `conversationId`，服务端核对账号和活动状态。两个 WebSocket 分别读取各自历史并写回对应会话，越权、归档和缺失会话被拒绝 |
| 多副本重启与结算 | 生成每 10 秒续心跳，超过 120 秒无更新的活动任务进入回收，每 30 秒扫描。完成、停止和恢复通过条件更新争用终态，余额与答复在同一事务提交。覆盖健康任务、过期任务、两个副本并发回收、迟到完成及结算/释放竞争 |
| 审批中断后换人恢复 | 管理员恢复接口读取原决定，保留原审批人和说明。覆盖决定落库后图推进中断、执行前中断、另一管理员并发恢复、退款回执一致、重复关单及队列分页 |

[隔离与结算回归](../../../backend/tests/e2e/test_release_p1_regressions.py) · [审批回归](../../../backend/tests/e2e/test_refund_approval_preview.py) · [额度回归](../../../backend/tests/agent/test_token_reservation.py)

同一交付同步了原工作目录已有的去邀请码改动及 `0020` 迁移。冻结评测和官方知识快照按原 SHA-256 清单核对，Git 属性覆盖 Phase A 输入、正文和原始快照。

## 前序基线验证

| 验证 | 结果与范围 |
| --- | --- |
| 完整后端离线回归 | 当前基线本机 420 通过、2 跳过，Fast CI 通过；跳过的 Compose Billing MCP 和 MySQL 跨进程用例由隔离集成覆盖 |
| 地域范围复验 | 新增 9 项回归，相关集合 56 项通过；同四题真实模型首跑 4/4 通过，24 条引用核验完成，见[前后证据](../evidence/N12_SCOPE_FAILURE_2026-10-20.md) |
| MySQL P1 专项 | 本机独立临时 MySQL 8.4 库，7 项通过，结束后清理测试库 |
| 前端 | 类型检查、生产构建通过，双账号退款及关单浏览器用例通过 |
| 业务演示 | HTTP 与浏览器确认同一退款回执，独立支付模拟账本只写一笔，原工单为 `CLOSED` |
| 隔离集成 | 真实 MySQL 迁移、Elasticsearch 跨存储与执行隔离、Billing MCP 协议验收通过 |
| 工程检查 | 文档目标、冻结数据、关键 Ruff 规则与 Compose 校验通过 |

前序基线对应的 push、pull request 两轮 Fast CI 和 PR 隔离集成均已完成。[Fast CI](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384682502) · [push 检查](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384665745) · [隔离集成](https://github.com/c1335872304/AI-DevSupport/actions/runs/44384682348)

## 适用边界

本页确认源码候选和上述自动化验证。2026-11-18 的真实模型、成本与本机预发布对照见[候选性能验收](ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md)，其镜像和样本范围按原报告解释。当前源码对应的目标环境镜像、实际依赖、通知、流量与签验见[预发布手册](../../RELEASING.md)。

本轮审批检查点已共享到 SQL，Redis 提供跨副本事件和取消，Provider 未知消耗有持久请求台账与受控对账入口，原五项债务均已关闭，见[维护台账](../../MAINTENANCE.md)。退款仍为合成支付，真实渠道不属于这批改动。目标环境的实际镜像、依赖、备份、通知和放量签验按发布手册执行。


## 本轮五项债务关闭验收

所有实现先在本地完成，再集中上传原 PR。没有更换正式题库或官方知识快照，日常手册仍为七份，docs 共十六份。当前源码增加 `0021_close_runtime_debts` 迁移，共享审批检查点和任务、供应商请求/对账记录、工单及角色审计均在 SQL 持久化。

| 项目 | 本地结果与范围 |
| --- | --- |
| 完整后端回归 | 441 passed、2 skipped，启用新专项的真实 MySQL 和 Redis；两项跳过为单独运行的旧集成用例 |
| 完整隔离集成 | 真实 MySQL / ES / Redis 共 81 passed，包含独立进程领取、诊断恢复、跨副本续流和取消、共享审批及对账/权限；ES 测试端口已可配置 |
| 原 P1 MySQL | 专用 `p1_release_debts` 库，7 passed |
| Billing MCP | 独立 HTTP MCP + MySQL，1 passed，读取范围与协议核对通过 |
| 退款/关单 | HTTP 演示确认同一回执、独立合成支付账本一笔退款、原工单 CLOSED；三账号浏览器 2 passed，客服能处理并查看审计，无法访问审批 |
| 迁移 | 独立 SQLite、MySQL 全新升级、回退至 0020、再升级 0021 均通过 |
| 前端工具链 | 全量只读 ESLint 0 errors / 0 warnings，类型与生产构建通过，流式重放/隔离脚本通过；干净目录按冻结锁文件用 Node 20 / pnpm 9.15.5 安装，lint、类型和构建通过。Windows 缩短虚拟依赖路径以避开长路径解析问题 |
| 真实 API | 同 N12 / REGION / BATCH / FUTURE 四题，首跑 4/4 通过；12 次 LLM 和 4 次 Embedding 请求均有持久用量、供应商请求 ID，汇总与实际回执一致 |

真实 API 回执输入 **49,464 Token**、输出 **2,159 Token**、Embedding **159 Token**，无已记录 Provider 错误，未估算费用。原始回答、事件、请求台账和逐题复核位于 `backend/data/checkpoints/debt-closure-live-20261119/`，该目录中的 `review.json` 校验账本与回执一致。前序真实模型报告仅用于其原样本与版本解释。

新增专项为 [test_debt_closure.py](../../../backend/tests/e2e/test_debt_closure.py) 与 [test_shared_generation_events.py](../../../backend/tests/e2e/test_shared_generation_events.py)。覆盖原决定不变、执行者失联、失败重试、十二次后暂停及换人恢复、未知用量 NULL、供应商收据去重、状态约束与最小权限。默认 CI 使用离线夹具；真实服务在隔离集成跑。Fast CI 保留 PR、主分支与手动入口，开发分支同一提交不再重复跑 push / PR 两轮。

本地原始检查结果另见 `backend/data/debt-seal-integration.log`、`debt-p1-mysql.log`、`debt-billing-protocol.log`、`debt-browser-confirmed.log` 及 Git 工作副本的 `backend/data/debt-seal-all.log`。远端检查以[原 PR Checks](https://github.com/c1335872304/AI-DevSupport/pull/1/checks)中的实际提交为准。

## 编排扩展验证

专业 Agent 支持按需读取已声明的 Skill 参考材料；每个 Skill 每次生成最多一次读取尝试、4,000 字符和一次追加规划调用，后续复用。证据汇总允许在原权限、工具和步骤预算内补查一轮、最多两项只读工具；诊断执行器已有租约时保持原恢复路径。前端显示独立的业务阶段事件。

新增编排专项 19 项通过，覆盖参考材料边界、依赖补齐、重复与失败调用保护、账期和文档锚点，以及完整运行时。完整离线后端检查 448 passed / 13 skipped，随后补充的一项完整运行时测试另行通过；跳过为需要显式真实服务配置的集成测试。浏览器 3 项通过，包含进度隔离和等待补充信息的展示。前端类型、流式脚本和生产构建通过；ESLint 排除浏览器生成产物，继续对源码执行零警告门禁。

原 N12 / REGION / BATCH / FUTURE 四题真实复测首跑 4/4 通过，无 Provider 错误。15 次 LLM 与 4 次 Embedding 请求均有持久回执和请求 ID，输入 55,709 Token、输出 2,889 Token、Embedding 159 Token。原始结果与逐题哈希保存在 `backend/data/checkpoints/orchestration-live-20261119/`，复核结论见其中 `review.json`。该结果验证四题的范围、单位与未来承诺边界，不代表通用任务成功率或成本降低。
