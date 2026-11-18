# 客服上下文系统

## 数据流与责任

正式登录和 WebSocket 校验用户后，聊天服务先保存本轮用户消息。上下文组装器用该消息 ID 更新续办状态，随后向生产图交付同一个本轮上下文。路由读取已解析字段，检索改写读取近期历史与回查片段，工具规划使用作用范围约束参数，答复节点分别接收用户口述上下文和本轮已核验证据。原始消息仍由聊天服务保存。

| 内容 | 权威来源 | 范围与时效 |
| --- | --- | --- |
| 用户原话、纠正和已尝试步骤 | `conversation_messages` | 查询同时校验客户、会话、消息 ID。近期内容以完整消息为单位裁剪。 |
| 当前续办字段 | `conversation_context_states` | 一会话一行，内部按请求、工单、账期或应用标识归并。每个字段保存值、来源、时间和原消息 ID。纠正保留被替代的消息 ID。 |
| 诊断结论、执行及工单 | 既有诊断、工具与工单记录 | 续办上下文提供查询锚点，诊断和工单状态沿用各自的权威记录。 |
| 账单、用量等可变业务事实 | 本轮已获授权的实际工具结果 | 续办状态可提供账期等参数。确认当前业务值仍走工具和已有时效校验。 |
| 通用文档规则 | 本轮已授权的检索结果及引用 | 载入现有证据预算，原文来源可通过正式引用接口查询。 |

追问才继承活动范围。普通寒暄不会把旧工单内容放进本轮，也不会清空续办状态。明确换请求时先选择新的范围；单问同时出现多个请求号时，先要求选择，再允许诊断工具开始。相邻会话和不同账号分开读取。用户口述标记为 `user_report`，不会因此变为工具核实的事实。

## 持久化与预算

迁移 `0016_conversation_context_state` 增加独立表，保留现有会话和诊断表。首次启用已有会话时，最多从最近 100 条用户消息补建状态。正常写入按消息 ID 有序推进。SQL 比较旧版本后提交新版本；迟到的旧轮次无法覆盖新纠正。Redis 键包含客户、会话和持久版本号，只有 SQL 当前版本对应的缓存才参与读入。缓存不可用时回退 SQL。

近期历史与回查片段共同使用原有的 20 条、12,000 字符预算。回查最多取 3 条授权原话、合计最多 1,000 字符，优先取原始锚点和关联尝试。问起最初一次排障时，也可以按保留的首次尝试 ID 回查。旧业务回执仍保存在原业务记录中；续办状态只保留用户明确提供的范围字段和原话引用。上下文入口不把旧工具原文整批送回模型。

当前开关为 `CONTEXT_SYSTEM_ENABLED`，默认开启。关闭时走原读取策略，正式发布前先执行迁移。生产环境的 Redis 限流和 WebSocket 配额仍执行原安全策略。隔离环境验证了缓存层的 SQL 回退，生产入口在共享限流不可用时可以拒绝新连接。

## 阶段 0–2 验收

| 检查 | 结果 |
| --- | --- |
| 原版对照 | 真实入口超过 20 条历史消息及 12,000 字符后，旧请求号消失。 |
| 跨窗口续办 | 恢复旧请求号、接口、版本和原始片段，并沿用同一诊断 ID。 |
| 用户纠正和延迟写入 | v1 更正为 v2 后，新追问使用 v2；迟到的旧轮次无法回写。 |
| 隔离 | 切换到新请求得到新诊断，不继承旧版本或接口；新会话和其他账号也不继承。多个请求号同时出现时先澄清，不调用工具。 |
| Redis 故障 | 停止专用 Redis 后，从 SQL 恢复同一请求和版本；重启并清空缓存后重新建立缓存。 |
| 业务重查 | 通过真实 Billing MCP，追问沿用账期并重新得到变化后的用量 175，原值为 120。 |
| 预算与引用 | 跨窗口后仍回答 50 MB 限制和压缩归档例外；引用通过正式接口打开。 |
| 迁移 | 隔离 MySQL 8.4 从 0015 升到 0016，保留既有会话。 |
| 原有回归 | 冻结离线 60/60、30/30 对、必需引用 38/38；六类固定 Docker 入口抽验 12/12。 |

[基线](../../backend/data/context-system/baseline.json) · [续办和隔离](../../backend/data/context-system/verified.json) · [缓存停机](../../backend/data/context-system/offline.json) · [缓存恢复](../../backend/data/context-system/restored.json) · [账单重查](../../backend/data/context-system/billing.json) · [跨预算引用](../../backend/data/context-system/knowledge.json) · [MySQL 迁移](../../backend/data/context-system/mysql-upgrade.json)

验收在隔离 Docker 使用合成账号、容器内模型与向量替身、真实 Redis 和 Billing MCP。

## 阶段 3 · 长工单进度摘录

新增可选开关 `CONTEXT_PROGRESS_ENABLED`，默认关闭。续办状态按工单记录已尝试、用户反馈和待查项的消息 ID。相同原话按指纹去重，查询时只从已授权会话回查最多六条、总计最多 800 字符。只在续办且明确询问进度或下一步时读取。相同条目在进度、普通回查和近期历史中只计入一份，仍受原预算限制。无法读取或超过 0.5 秒时保留原来的续办状态和原话。诊断路径把摘录明确标为用户反馈，进度和当前业务证据分别呈现。

两组分别在新 Docker 容器中，走相同正式 HTTP/WebSocket 序列。覆盖四项操作和一项待查，包括备用网关、调整退避、回退后的反馈和出口代理。所有关键步骤都移出近期窗口后再问进展。

| 指标 | 关闭 | 启用 |
| --- | ---: | ---: |
| 能在续办答复定位的关键项 | 0/5 | 5/5 |
| 历史与回查 token 估算 | 3,633 | 3,202 |
| 客户端首段耗时，本次样本 | 1,968 ms | 712 ms |
| 摘要专用模型调用 | 0 | 0 |

首段耗时来自单次隔离轨迹，尚未形成性能基线。开启组首次出现普通回查和摘要互相去重后，诊断答复遗漏两条的情况。修复后同一来源只保留在进度摘录，正式入口复测完整恢复五项。Langfuse 已接入上下文组装耗时、选择来源、历史裁剪、进度命中、超时回退等元数据。真实模型长会话对照、影子运行和发布回滚仍待阶段 4 完成。

[关闭组](../../backend/data/context-system/progress-off.json) · [开启组](../../backend/data/context-system/progress-on.json) · [冻结离线回归](../../backend/data/context-system/progress-frozen-offline.log)

## 阶段 4 · 影子运行和发布门禁

执行迁移后，通过 `CONTEXT_SYSTEM_ENABLED=false` 和 `CONTEXT_SHADOW_ENABLED=true` 开始影子模式。旧路径继续生成答复；新组装器在独立数据库会话中生成候选状态，各自完成范围和字段解析后只对比差异、是否续办、是否歧义及当前事实的重查意图。候选字段不参与工具执行和回答。影子超时或失败时，本轮照常由旧路径处理。Langfuse 记录生成 ID 关联下的差值、消息数和耗时。

2026-11-18 · 候选镜像 `paismart-backend:context-rc-20261118` 从镜像运行，无源码挂载。独立 Docker 中，旧路径对超窗口追问没有找到请求号，影子捕捉到范围差异；切换为新路径后从同一数据卷恢复原请求。API 重启后仍能续办。模拟确认范围串用，运行门禁返回退出码 2；切回旧读取策略后，原始消息通过正式历史接口仍可回查。切回新读取策略后再次恢复原请求。OTLP 接收器按生成 ID 确认了影子及启用路径的上下文元数据，未收到实体值。严重条件包括串用、过期业务事实和纠正丢失，分别通过 `context_scope_violation`、`stale_context_fact`、`context_correction_lost` 暂停放量。

[演练时的镜像 ID](../../backend/data/context-system/stage4-image.txt) · [最终候选镜像 ID](../../backend/data/context-system/stage4-final-image.txt) · [影子、重启与回滚报告](../../backend/data/context-system/stage4-rollout.json) · [放量门禁](../03-operations/LANGFUSE.md)

候选镜像另走正式入口验证了 Redis 停机后回退数据库、Redis 重启后恢复缓存、v1 到 v2 的纠正及同账号不同会话与跨账号隔离。阶段 2 的 MySQL 迁移记录仍适用。[请求范围和纠正](../../backend/data/context-system/stage4-scopes.json) · [缓存失效](../../backend/data/context-system/stage4-cache-offline.json) · [缓存重建](../../backend/data/context-system/stage4-cache-restored.json)

DeepSeek Flash 非思考模式的 60 条冻结用例，初次评分 59/60、29/30 对、36/38 项引用。唯一失败是评分器把紧跟句号后的同一行引文拆成了独立片段。修正后，同一句的句号前、句号后引文均归属原主张，邻句和文末清单仍不能补分。用原始答复复算为 60/60、30/30 对、38/38 项，无截断和执行错误。[原始结果](../../backend/data/context-system/stage4-deepseek-frozen.jsonl) · [冻结结果复算](../../backend/data/context-system/stage4-frozen-rescore.json)

最终镜像从全新合成会话通过两组真实 DeepSeek 长会话。第一组核对了跨窗口恢复、新值更正、多请求澄清与隔离；第二组在步骤滑出窗口后恢复了 5/5 项用户反馈。首跑两组被测试账号的 LLM 余额限制拦截，调高隔离账号余额后只重跑了两组长会话。最终镜像的本地六类入口抽验为 12/12。目标部署环境仍需连通实际依赖、运行影子模式并验收放量门禁。[长会话真实记录](../../backend/data/context-system/stage4-deepseek-retest-long.json) · [进度摘录真实记录](../../backend/data/context-system/stage4-deepseek-retest-progress.json) · [最终镜像入口抽验](../../backend/data/context-system/stage4-final-smoke.jsonl)
