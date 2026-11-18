# 401/429 诊断闭环与执行恢复

当前源码：2026-10-20，第三阶段 P3-01～P3-11。承接[诊断状态与证据](DIAGNOSIS_STATE.md)，执行记录见[第三阶段验收](../04-testing/DIAGNOSIS_LOOP_ACCEPTANCE.md)。

## 规则与事实

服务身份固定为独立模拟服务 `demo-api`，规则版本 `2026-10-v1`。DeepSeek、Qwen、GPT 文档提供各自产品的通用规则，不能证明这个模拟服务或厂商真实账户的业务状态。

| HTTP | 候选原因 | 最少请求时观测 |
| --- | --- | --- |
| 401 | 缺认证 | authPresent=false |
| 401 | 认证格式错误 | authPresent=true，authSchemeValid=false |
| 401 | Key 失效或过期 | 前两项有效，keyStateAtCall 为 REVOKED/INVALID 或 EXPIRED |
| 401 | 应用不匹配 | Key 当时 ACTIVE，keyAppIdAtCall 与请求应用不同 |
| 429 | 请求频率 | limiterKind=RATE，rateObserved 大于 rateLimit |
| 429 | 并发 | limiterKind=CONCURRENCY，concurrencyObserved 大于 concurrencyLimit |
| 429 | 配额 | limiterKind=QUOTA，quotaRemaining<=0 |

日志与观测分别保存，通过同用户、request_id、应用、接口和版本关联。`query_request_observation` 只返回白名单脱敏字段。HTTP 状态、错误码说明和当前 Key 状态均不能单独证明细分根因；未知版本、缺观测、计数矛盾或描述冲突保留不确定性。候选保存 SUPPORTED / EXCLUDED / UNDETERMINED、支持/反对证据与时间，建议逐条关联原因及证据。

## 现有聊天流程中的执行

沿用现有 LangGraph：实体/路由 → 请求日志 → 独立只读核查并行 → 专业 Agent 补充资料 → 证据汇总 → 真实交接 → 答复 → 质量门。诊断预核查复用 Tool Registry 的参数、角色、Skill 和事件校验；请求不存在时停止下游猜测。

核心状态在证据汇总节点完成持久化，不依赖模型成功输出答案。程序从受验证决定生成有范围的诊断答复，质量门继续审计；通用知识仍按现有检索权限与引用机制处理。过时 generation 或 epoch 不能提交根因或覆盖新轮次。

## 修正后复查

用户执行修正，提交新的 request_id，可在聊天中明确说“复查”，也可通过面板提交。原故障请求保留在 workflow.original，新请求单独记录。

复查必须属于本人、同一应用和接口，区别于原请求；发生在原事件与诊断开始之后，不能来自未来，核查时距现在不超过五分钟。只有成功的新请求支持对应应用/接口/请求范围恢复。用户口述单独记录；关联不符、无日志、仍失败均不能标解决。

API：`POST /api/v1/diagnoses/{id}/rechecks`，参数 requestId、expectedRevision、idempotencyKey；202 表示已提交，以详情结果为准。同键同请求重放复用 generation，同键不同请求或过时 revision 返回409。`POST /{id}/resume` 只唤醒已有执行，不重置预算或抢健康租约。全部按本人授权，未知和无权均404。

## 检查点与恢复

迁移 `0015_diagnosis_loop` 增加 DiagnosisExecution、DiagnosisStep、SupportRequestObservation，扩展 workflow、工单诊断身份以及 MySQL 事件微秒精度。

- 执行以 generation 为身份，数据库时间租约 + owner + 单调 epoch 保护。先锁会话，再锁执行/诊断；网络调用不占长事务。
- 每个允许的只读步骤按 generation、工具与规范化参数生成稳定身份。调用前记预算，完成后记脱敏结果；结果发布检查执行权。
- TIMEOUT 与服务 ERROR 最多尝试两次；无记录、参数错误、权限拒绝和未知工具不重试。默认每轮12次、每诊断36次；中断也消耗已预留尝试。
- 同一诊断内仅复用未过期成功读。日志/观测120秒、Key30秒、统计60秒、错误码300秒；过期重查。历史证据仍可解释对应事件，不能被描述成当前恢复。
- 服务每10秒扫描待执行或租约过期任务；PENDING 等待至少5秒，避免抢刚开始的聊天。健康 Worker 续租；过期才接管，旧执行者不能发布。
- 恢复结构化任务、证据和交接意图，不续跑付费模型、不恢复模型内部思考。文档原文不写入诊断读步骤；引用读取时重新检查活动版本与授权。

两轮无进展、三次复查上限、预算/权限条件或用户明确要求触发交接。先持久化 HANDOFF_PENDING，再创建真实工单；按 diagnosis_id 唯一，提交成功但确认丢失时先查询既有结果。工单包含症状、已查事实、尝试动作、缺口和复查记录；失败不能声称已转人工。

实现入口：`app/diagnosis/{rules,loop,execution,response,service}.py`、`app/agent/graph/workflow.py`、`app/support/handoff.py`、`app/api/v1/diagnoses.py`。

## 第四阶段：停止多余规划

`diagnosis/planning.py` 用相同的版本化观测契约检查预核查是否已足以判断原因；请求号、应用和用户描述均不能冲突。满足时仅跳过 API 专业 Agent 的重复模型规划，继续保留原路由记录、知识/Billing规划、证据汇总、最终执行权校验和质量门。未知原因、缺观测、未知版本、越权与冲突不会触发跳过；事件 `diagnosis_planning_skipped` 记录原因。

“已恢复”反馈沿用同一故障并标为用户报告，不能跳过新请求复查守卫。轨迹评分、调用数对照与限制见[最终验收](../04-testing/FINAL_PROJECT_ACCEPTANCE.md)。
