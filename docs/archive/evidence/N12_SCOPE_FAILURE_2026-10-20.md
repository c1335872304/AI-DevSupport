# N12 地域与计费范围失败证据

此记录支撑[维护台账](../../MAINTENANCE.md)中尚未关闭的范围问题，保存 2026-10-20 原问法、审阅与回答。价格和限制属于当时被审阅的历史回答内容。

## 原始记录

现有Qwen文档能否保证text-embedding-v4在2099年仍然免费、批量上限不变？

判分要求：当前资料不足以保证未来费用与限制；当前快照价格和限制不得当成未来承诺

审阅：PARTIAL。未来费用与限制无法保证的核心结论正确；但补充信息把新加坡的0.000514/无免费额度泛化为通用当前状态，且把RPM/TPM限流混入批量条数讨论。地域、计费及限制类型范围表达仍有缺陷，未计为满分。

### 原始回答

不能保证。基于现有 Qwen 文档，无法得出“text-embedding-v4 在 2099 年仍然免费、批量上限不变”的结论，理由如下：

**1. 关于“免费”**
- 文档中 text-embedding-v4 的免费额度一栏明确写的是“无免费额度”，计费为 0.000514 元（按文档所列计费单位）。也就是说，现有文档不仅没有承诺未来免费，反而显示该模型当前没有免费额度。来源#2: qwen-embedding-api.md
- 文档是特定核对日期的快照（核对日期 2026-10-19），且明确说明“核对日期不等于规则生效日”，属于历史时点的资料，不能作为对 2099 年价格的承诺。来源#1: qwen-embedding-v4.md

**2. 关于“批量上限不变”**
- 文档只记录了当前时点的限流数值：text-embedding-v4 在 Batch API 调用下不受限流限制，表中列出 1,800（RPM）和 1,200,000（TPM）。这是对当时规则的描述，并未承诺长期不变。来源#5: qwen-rate-limits.md
- 文档也说明限流规则可参考专门的限流页面，属于会随产品调整的运营参数，不能据此推断 2099 年的上限。来源#4: qwen-rate-limits.md

**结论**：现有文档只能反映核对时点的规则快照，既不能证明该模型“免费”，也不能承诺价格或批量上限在 2099 年保持不变。如需长期稳定性承诺，建议以阿里云百炼官方服务条款或商务合同为准，并关注官方页面的后续更新。

来源#1: qwen-embedding-v4.md
来源#2: qwen-embedding-api.md
来源#3: qwen-embedding-api.md
来源#4: qwen-rate-limits.md
来源#5: qwen-rate-limits.md
来源#6: qwen-embedding-api.md
来源#7: qwen-batch.md

## 追溯与关闭

本机原始结果为 `backend/data/checkpoints/answer-quality-fix-20261020/final/N12.json`，SHA-256 为 `17177e00d76437b408deb955ef73bc96928f8c73cb88bb0570ad5e59e89ab318`。当次冻结组合 SHA-256 为 `813e89b70ab91b169ec87ee467543f3daf5595ce21867e40ac9c747765002de5`。

[原提交中的完整逐题导出](https://github.com/c1335872304/AI-DevSupport/blob/47b0c8503aee4b4c735b9bd8938eeb4973990103/docs/artifacts/2026-10-20/ANSWER_QUALITY_FINAL_CASES_2026-10-20.md)保留于 Git 历史。

关闭该问题需用原问法及独立地域对照题复验，数值明确绑定地域、计费方式、时间和限制类型，并保存新回答和引用。

## 2026-11-19 真实复测

结论：**仍未通过，不能关闭**。N12、批量限制和未来承诺题为 PARTIAL，地域比较题为 FAIL，完整通过 0/4。批量条数与 RPM/TPM 的区分本身已答对，但数值仍未标注地域。

使用当前源码的 `AgentRuntime`、实际数据库检索和现有 `deepseek-chat` 配置，四题各首跑一次，不挑选重试结果。知识库通过 SQLite backup 复制至隔离目录，不修改原库。题目依据既有知识快照，未联网更新供应商规则。这轮覆盖后端图与真实检索、生成，不包含浏览器或 WebSocket 交付。

定位：N12 引用的 API 表格父块含新加坡定价，但父块已丢失上游地域标签；地域对照题的两次检索均被规划为单地域 `region=CN`，第二次还附带 `category=billing`，最终零召回。后续修复应保留来源地域上下文，并避免将跨地域比较收窄成单地域过滤。尚未修改生产代码或宣称修复。

### N12

问法：现有Qwen文档能否保证text-embedding-v4在2099年仍然免费、批量上限不变？

复核：PARTIAL：拒绝未来承诺正确，但继续泛化免费额度与新加坡单价。

原始回答：

不能保证。现有文档没有对2099年免费或批量上限不变作出承诺，且文档本身显示 text-embedding-v4 当前并非免费。

- text-embedding-v4 的免费额度栏为“无免费额度”（来源#1）。
- text-embedding-v4 的单价为每千输入Token 0.000514元（来源#1）。
- text-embedding-v4 的 Batch 调用单价为每千输入Token 0.00025元（来源#3）。
- text-embedding-v4 的最大行数为10（来源#1）。
- text-embedding-v4 的单行最大Token数为8,192（来源#1）。
- 用 Batch API 调用 text-embedding-v4 时不受限流限制（来源#2）。
- text-embedding-v4 的限流条件为每分钟调用次数1,800、每分钟消耗Token数1,200,000（来源#2）。
- 该文档的核对日期为2026-10-19，且核对日期不等于规则生效日（来源#5）。
- 文档未给出2099年的价格或批量上限承诺（来源#5）。

如需确认未来价格与配额安排，请以阿里云百炼官方最新公告或商务协议为准，并向官方渠道书面确认。

来源#1: qwen-embedding-api.md
来源#2: qwen-rate-limits.md
来源#3: qwen-embedding-api.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-v4.md
来源#6: qwen-rate-limits.md
来源#7: qwen-batch.md

引用定位：#1 qwen-embedding-api.md / chunk 12、#2 qwen-rate-limits.md / chunk 740、#3 qwen-embedding-api.md / chunk 5、#4 qwen-embedding-api.md / chunk 3、#5 qwen-embedding-v4.md / chunk 0、#6 qwen-rate-limits.md / chunk 746、#7 qwen-batch.md / chunk 5。

原始结果 SHA-256：`fd61a69bdc09594be076e6c9eecfba98b827d68ee7b4cd10e7d136a736ccd48f`。

### REGION

问法：按现有Qwen文档，text-embedding-v4在北京和新加坡的价格与免费额度是否相同？请分别注明地域、计费单位和资料时间，不要把一个地域泛化成全部地域。

复核：FAIL：知识快照有地域定价内容，检索却返回无资料。

原始回答：

知识库中未找到支持该结论的资料，请补充问题细节后再查。

引用定位：无。

原始结果 SHA-256：`f216141d6bc5b1f8c5af56e72c229353e6bbba4d87af91f1eb4668c9b36022ca`。

### BATCH

问法：按现有Qwen文档，text-embedding-v4单次请求最多提交多少条文本？这与RPM、TPM限流以及Batch API是否受限流是同一个限制吗？请分别说明并引用。

复核：PARTIAL：正确区分单次条数与 RPM/TPM，但列出的限流数值缺地域范围。

原始回答：

按现有 Qwen 文档，text-embedding-v4 单次请求最多提交 10 条文本（来源#5）。text-embedding-v4 在输入为字符串列表或文件时，最多支持 10 条（行）（来源#5）。text-embedding-v4 每条（行）最长支持 8,192 Token（来源#5）。OpenAI 兼容接口下 text-embedding-v3 / v4 同样规定输入为字符串列表或文件时最多支持 10 条（行）（来源#6）。示例代码中批量大小常量设为 10，与上述条数上限一致（来源#4）。

这不是同一个限制。RPM 与 TPM 是限流条件，超出任一数值时触发限流（来源#2）。限流表按模型分别列出每分钟调用次数（RPM）和每分钟消耗 Token 数（TPM）（来源#2）。text-embedding-v4 在限流表中对应的 RPM 为 1,800（来源#1）。text-embedding-v4 在限流表中对应的 TPM 为 1,200,000（来源#1）。用 Batch API 调用服务时，不受限流限制（来源#1）。因此单次请求的文本条数上限属于请求体批量大小规则，而 RPM/TPM 属于调用频率与 Token 消耗的限流规则，Batch API 则是对限流限制的豁免说明，三者不是同一个限制（来源#1）（来源#2）（来源#5）。

如需确认您账户的实际限流额度或批量调用表现，请结合您所在地域的限流表与调用日志核对。

来源#1: qwen-rate-limits.md
来源#2: qwen-rate-limits.md
来源#3: qwen-rate-limits.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-api.md
来源#6: qwen-embedding-api.md
来源#7: qwen-errors.md

引用定位：#1 qwen-rate-limits.md / chunk 740、#2 qwen-rate-limits.md / chunk 738、#3 qwen-rate-limits.md / chunk 745、#4 qwen-embedding-api.md / chunk 85、#5 qwen-embedding-api.md / chunk 64、#6 qwen-embedding-api.md / chunk 19、#7 qwen-errors.md / chunk 173。

原始结果 SHA-256：`dc7feebf784dbf508d7741b316917b6e1307bd065f5e42318333cae0a037b222`。

### FUTURE

问法：现有Qwen资料可以保证北京地域text-embedding-v4在2099年仍有当前免费额度、单次批量条数不变吗？新加坡地域的价格能直接当成北京价格吗？

复核：PARTIAL：正确区分北京与新加坡价格，但仍将免费额度泛化。

原始回答：

不能保证。现有资料只说明 text-embedding-v4 当前“无免费额度”（来源#1）。资料没有承诺该额度或单次批量条数在 2099 年保持不变。新加坡地域的价格不能直接当成北京价格：北京地域 text-embedding-v4 文本输入为 0.5 元/每百万 tokens（来源#4）。新加坡地域 text-embedding-v4 文本输入为 0.514 元/每百万 tokens（来源#4）。两地 API Key 不同，新加坡地域需使用不同的 base_url（来源#7）。如需确认未来额度与批量限制，请以届时的官方文档和控制台为准。

来源#1: qwen-embedding-api.md
来源#2: qwen-batch.md
来源#3: qwen-rate-limits.md
来源#4: qwen-embedding-v4.md
来源#5: qwen-rate-limits.md
来源#6: qwen-rate-limits.md
来源#7: qwen-batch.md

引用定位：#1 qwen-embedding-api.md / chunk 12、#2 qwen-batch.md / chunk 5、#3 qwen-rate-limits.md / chunk 746、#4 qwen-embedding-v4.md / chunk 10、#5 qwen-rate-limits.md / chunk 751、#6 qwen-rate-limits.md / chunk 747、#7 qwen-batch.md / chunk 156。

原始结果 SHA-256：`20bef6463aacf8d5078b4a33e61484cb3d9b7b24da6850d79a1ec043f2766e62`。

### 用量与回归

Provider 回执记录输入 44,887 Token、输出 2,128 Token，Embedding 203 Token。四题生成均完成，无已记录的 Provider 错误或截断。未估算金额。原始结果保存在 `backend/data/checkpoints/n12-retest-20261119/`。

相关离线回归 `test_answer_quality_regression.py` 与 `test_vendor_scope.py` 共 36 passed，使用隔离 SQLite 并禁用外部追踪。离线回归通过不能覆盖此次真实模型暴露的地域问题。
