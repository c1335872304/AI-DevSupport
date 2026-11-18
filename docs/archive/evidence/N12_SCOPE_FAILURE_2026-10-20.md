# N12 地域与计费范围追溯及修复验收

当前状态：**已修复并于 2026-11-19 用同四题真实复验通过（4/4）**。下文保留 2026-10-20 原始失败、2026-11-19 修复前失败及修复后首跑，供[维护台账](../../MAINTENANCE.md)追溯。价格和限制仅用于核验既有知识快照，不代表当前供应商报价。

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

## 2026-11-19 修复后真实复验

结论：**PASS 4/4，该项 P2 关闭**。保持同四题、同模型 `deepseek-chat`、同知识库副本和原验收标准，四题各运行一次，未丢弃失败后重试挑选答案。修复前后 manifest 的数据库 SHA-256 相同，未改题目、知识快照、向量或文件元数据。

修复包含两部分。检索从同一所有者、文件和活动版本的完整父块序列恢复原文分区、章节、核对日期和表头单位，适配既有索引；文档分块读取及签名引用预览复用同样上下文。跨地域问题保留原问法，去掉规划器或实体提取错误加入的单地域过滤及未由用户指定的分类过滤，保留厂商、版本、日期和权限约束。生成提示要求数值绑定适用范围，压缩证据时不拆散地域与表格。

相关离线回归共 56 项通过，其中新增 9 项覆盖旧分块、分区关闭、代码围栏、跨地域改写、保留单地域/显式分类、同一来源不同地域不误合并，以及数据库/Elasticsearch 检索、读取和引用一致性。24 条引用均核验所有者、活动构建和子块存在，并保存恢复后的原文上下文及哈希。

### 修复后 N12

问法：现有Qwen文档能否保证text-embedding-v4在2099年仍然免费、批量上限不变？

复核：PASS：拒绝未来保证，免费额度明确限定新加坡，批量条数与 RPM/TPM 分开表述，数值标明北京范围。

原始回答：

现有Qwen文档不能保证text-embedding-v4在2099年仍然免费或批量上限不变。文档只记录了核对日期为2026-10-19的当时规则，核对日期不等于规则生效日，也没有任何面向2099年的免费或限额承诺（来源#1）（来源#5）。

就现有文档记录而言：在新加坡地域的同步接口模型概览中，text-embedding-v4的免费额度为“无免费额度”（来源#1）。在北京地域的同步接口模型概览中，text-embedding-v4的最大行数为10（来源#3）。在北京地域的限流文档中，text-embedding-v4的每分钟调用次数（RPM）为1,800（来源#2）。在北京地域的限流文档中，text-embedding-v4的每分钟消耗Token数（TPM）为1,200,000（来源#2）。这些数值均属于对应地域和章节下的当时记录，不能作为未来长期不变的保证（来源#1）（来源#2）（来源#3）。

如需确认未来价格与限额安排，请以阿里云百炼官方最新公告和您账户的实际计费页面为准。

来源#1: qwen-embedding-api.md
来源#2: qwen-rate-limits.md
来源#3: qwen-embedding-api.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-v4.md
来源#6: qwen-rate-limits.md

引用定位：#1 qwen-embedding-api.md / chunk 12、#2 qwen-rate-limits.md / chunk 740、#3 qwen-embedding-api.md / chunk 5、#4 qwen-embedding-api.md / chunk 3、#5 qwen-embedding-v4.md / chunk 0、#6 qwen-rate-limits.md / chunk 746。

原始结果 SHA-256：`2f7068739a5828949077fe953715757360dd52a2039c85725aa7f30294b91443`。

### 修复后 REGION

问法：按现有Qwen文档，text-embedding-v4在北京和新加坡的价格与免费额度是否相同？请分别注明地域、计费单位和资料时间，不要把一个地域泛化成全部地域。

复核：PASS：分别给出北京、新加坡的价格、计费单位、免费额度和资料日期，不再零召回。

原始回答：

按现有 Qwen 文档，text-embedding-v4 在北京和新加坡的价格与免费额度并不相同。

**北京（华北2，北京）**
- 北京地域 text-embedding-v4 的同步接口单价为每千输入 Token 0.0005 元（来源#6）。
- 北京地域 text-embedding-v4 的 Batch 调用单价为每千输入 Token 0.00025 元（来源#6）。
- 北京地域 text-embedding-v4 的免费额度为 100 万 Token，有效期为百炼开通后 90 天内（来源#6）。
- 上述北京数据来自核对日期 2026-10-19 的资料（来源#6）。

**新加坡**
- 新加坡地域 text-embedding-v4 的同步接口单价为每千输入 Token 0.000514 元（来源#1）。
- 新加坡地域 text-embedding-v4 的免费额度为无免费额度（来源#1）。
- 上述新加坡数据来自核对日期 2026-10-19 的资料（来源#1）。

**计费单位说明**
- 北京地域的模型价格表以“每百万 tokens”为计费单位，文本输入为 0.5 元每百万 tokens（来源#2）。
- 新加坡地域的模型价格表以“每百万 tokens”为计费单位，文本输入为 0.514 元每百万 tokens（来源#2）。
- 上述价格表来自核对日期 2026-10-19 的资料（来源#2）。

如需确认您账户的实际计费与免费额度使用情况，请以百炼控制台的账单和额度页面为准。

来源#1: qwen-embedding-api.md
来源#2: qwen-embedding-v4.md
来源#3: qwen-rate-limits.md
来源#4: qwen-batch.md
来源#5: qwen-rate-limits.md
来源#6: qwen-embedding-api.md

引用定位：#1 qwen-embedding-api.md / chunk 12、#2 qwen-embedding-v4.md / chunk 10、#3 qwen-rate-limits.md / chunk 746、#4 qwen-batch.md / chunk 5、#5 qwen-rate-limits.md / chunk 751、#6 qwen-embedding-api.md / chunk 5。

原始结果 SHA-256：`3b2d23bcd5f822fbbc4705b4e1e12fd77e5a4687b619ee23140a8f79437f414d`。

### 修复后 BATCH

问法：按现有Qwen文档，text-embedding-v4单次请求最多提交多少条文本？这与RPM、TPM限流以及Batch API是否受限流是同一个限制吗？请分别说明并引用。

复核：PASS：单次 10 条与 RPM/TPM、Batch API 限流豁免分别说明，限流数值明确北京范围。

原始回答：

**直接结论**

- text-embedding-v4 在输入为字符串列表或文件时，单次请求最多支持 10 条（行）（来源#5）。
- text-embedding-v4 每条（行）最长支持 8,192 Token（来源#5）。
- 在华北2（北京）地域，text-embedding-v4 的每分钟调用次数（RPM）为 1,800（来源#1）。
- 在华北2（北京）地域，text-embedding-v4 的每分钟消耗 Token 数（TPM）为 1,200,000，且仅计输入 Token（来源#1）。
- 用 Batch API 调用服务时，不受限流限制（来源#1）。

**是否同一个限制**

不是同一个限制。单次请求最多 10 条是请求体批量大小限制（来源#5）。RPM 与 TPM 是每分钟维度的限流条件，超出任一数值时触发限流（来源#2）。Batch API 不受限流限制，属于限流豁免规则（来源#1）。三者分别约束不同维度，不能互相替代。

**核验建议**

如需确认您账号下的实际限流与批量配置，请以对应地域的控制台或配额页面为准。

来源#1: qwen-rate-limits.md
来源#2: qwen-rate-limits.md
来源#3: qwen-rate-limits.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-api.md
来源#6: qwen-embedding-api.md

引用定位：#1 qwen-rate-limits.md / chunk 740、#2 qwen-rate-limits.md / chunk 738、#3 qwen-rate-limits.md / chunk 745、#4 qwen-embedding-api.md / chunk 85、#5 qwen-embedding-api.md / chunk 64、#6 qwen-embedding-api.md / chunk 19。

原始结果 SHA-256：`10dece505ae9431f670ccfc10ed578cb5a139113776c601b760ccd0c73bf0158`。

### 修复后 FUTURE

问法：现有Qwen资料可以保证北京地域text-embedding-v4在2099年仍有当前免费额度、单次批量条数不变吗？新加坡地域的价格能直接当成北京价格吗？

复核：PASS：不保证 2099 年免费额度或条数，分别引用两地价格，不再泛化“无免费额度”。

原始回答：

现有资料不能保证北京地域 text-embedding-v4 在 2099 年仍有当前免费额度或单次批量条数不变；这些资料是核对日期为 2026-10-19 的文档快照，不构成对未来版本的承诺（来源#1）。新加坡地域价格不能直接当成北京价格：北京地域 text-embedding-v4 的文本输入价格为 0.5 元/每百万 tokens（来源#4）。新加坡地域（部署范围：国际）的文本输入价格为 0.514 元/每百万 tokens（来源#4）。两地价格分属不同地域表格，不能混用（来源#4）。

如需确认未来版本或当前个人账户的额度与价格，请以届时官方文档和百炼控制台为准。

来源#1: qwen-embedding-api.md
来源#2: qwen-batch.md
来源#3: qwen-rate-limits.md
来源#4: qwen-embedding-v4.md
来源#5: qwen-rate-limits.md
来源#6: qwen-rate-limits.md

引用定位：#1 qwen-embedding-api.md / chunk 12、#2 qwen-batch.md / chunk 5、#3 qwen-rate-limits.md / chunk 746、#4 qwen-embedding-v4.md / chunk 10、#5 qwen-rate-limits.md / chunk 751、#6 qwen-rate-limits.md / chunk 747。

原始结果 SHA-256：`12eb04be1c17d38371258f294c1a8829189e06f692605ca5bbd85ffb3705bb47`。

### 修复后用量与复现

本轮 Provider 回执输入 49,464 Token、输出 2,394 Token，Embedding 159 Token。均完成生成，无已记录 Provider 错误或截断，未估算费用。该次调用覆盖后端真实图、检索及生成，不替代浏览器交付或目标环境生产验收。

原始结果、引用审计及逐题复核位于 `backend/data/checkpoints/n12-retest-fixed-20261119/`。知识库副本 SHA-256：`946a11f4d246b069a3419b2d6dd33440be0f49005b4f7e6e2d771eb3442e49d9`。

在已配置模型的 backend 环境，显式运行 `python scripts/retest_n12_scope.py --live --output data/checkpoints/n12-fresh-run` 复现，输出目录需为空。这会调用实际供应商并产生费用。

完整后端回归在无本机 .env 的工作副本中完成：**420 passed，2 skipped**（Compose Billing MCP 与 MySQL 专项依赖单独环境，由隔离集成 CI 覆盖）。新增及现有代码通过致命 Ruff 规则、编译、文档链接与冻结输入校验。


## 五项债务关闭后的再复验

保持同四题，本轮真实复验再次 4/4 通过，结果保存在 `backend/data/checkpoints/debt-closure-live-20261119/`。新增请求台账记录 12 次 LLM 与 4 次 Embedding，所有请求均有用量及供应商请求 ID，输入 49,464、输出 2,159、Embedding 159 Token，与回执总计一致。详见[当前候选验收](../reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md#本轮五项债务关闭验收)，原始前后失败与回答不覆盖。
