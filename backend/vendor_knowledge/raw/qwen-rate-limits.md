# 限流

> 百炼按主账号维度对模型调用设置限流，账号下所有RAM子账号、业务空间和API Key 的调用量合并计算。超出限制时请求会被拒绝，通常在一分钟内自动恢复。

<meta property="og:title" content="限流" />

## 限流规则 <span id="0d83adbf7f19s" />

- <strong>账号级别限流</strong>：限流按主账号维度计算，账号下所有RAM子账号、业务空间和API Key 的调用量合并计算。
- <strong>模型独立限流</strong>：不同模型限流额度相互独立，具体参见下方表格。

<Note>
  部分模型，如 qwen3.8-max、qwen3.8-flash 采用 [动态限流（新）](/zh/model-studio/quota-management)的方式，根据百炼月消费档位进行软限流。
</Note>

## FAQ <span id="d1688da3e3egs" />

### 为什么触发限流？ <span id="08b8421697cff" />

根据错误信息判断触发了哪类限流：

- `Requests rate limit exceeded` 或 `You exceeded your current requests list`：触发了每分钟请求数（RPM）限流。
- `Allocated quota exceeded` 或 `You exceeded your current quota`：触发了每分钟 Token 消耗（TPM）限流。
- `Request rate increased too quickly`：请求频率在短时间内激增，触发了系统稳定性保护——即使总调用量未达到 RPM 或 TPM 上限也会触发。
- 其他报错，参见[错误码](/zh/model-studio/error-code)确认原因。

除 RPM 和 TPM 外，限流策略可能按秒级 RPS（RPM/60）与 TPS（TPM/60）执行。即使每分钟总调用量未超限，短时间内的请求爆发也可能触发限流。

### 如何查看模型调用量？ <span id="2c4544e8d8wy6" />

模型调用发生后<strong>分钟级</strong>即可在监控图表查看。登录模型监控页面（[北京](https://bailian.console.aliyun.com/cn-beijing/model/telemetry)或[新加坡](https://bailian.console.aliyun.com/ap-southeast-1/model/telemetry)），在左侧导航栏选择<strong>运维管理</strong> > <strong>模型监控</strong>进入监控概览页，设置查询条件（例如，选择时间范围、业务空间等），再在<strong>模型列表</strong>区域找到目标模型并单击<strong>查看详情</strong>，即可查看该模型的调用统计结果。具体请参见[监控告警](/zh/model-studio/model-telemetry)文档。

> 监控数据按分钟级更新，仅供参考，不作为计费依据。

### 遇到限流后多久恢复？ <span id="45e83f5504b7t" />

通常在一分钟内恢复。如出现其他报错，参见[错误码](/zh/model-studio/error-code)进行处理。

### 模型响应速度与付费有关吗？ <span id="faq-speed-paid-h" />

模型输出速度与是否付费无关。免费额度和付费调用使用相同的模型服务基础设施，同一模型的生成速度相同。免费额度仅控制请求是否被接受——额度耗尽时返回 403 错误（开通<strong>免费额度用完即停</strong>后），不会降低已接受请求的生成速度。

### 什么因素影响模型响应速度？ <span id="faq-speed-factors-h" />

- <strong>模型类型</strong>：轻量模型（如 qwen-flash）比大型模型（如 qwen-max）生成更快。
- <strong>输出长度</strong>：输出 Token 越多，总耗时越长。
- <strong>服务器负载</strong>：高峰期可能略有波动。

### 限流会降低已接受请求的生成速度吗？ <span id="faq-rate-limit-speed-h" />

不会。限流（RPM/TPM）仅导致超出限制的请求被拒绝（返回 429 错误）。免费额度耗尽时（开通<strong>免费额度用完即停</strong>）返回 403 错误，同样不影响已接受请求的速度。429 为速率限制，403 为配额耗尽，两者均为拒绝机制。

### 如何避免限流？ <span id="0e4e875b9c2eg" />

1. <strong>选用高限流模型</strong>

   - 优先使用 [qwen-plus](/zh/model-studio/models) 等限流额度更高的模型。
   - 稳定版或最新版比带日期的快照版本限流更宽松。
2. <strong>优化调用策略</strong>

   - <strong>降低调用频率</strong>：收到 `Requests rate limit exceeded` 或 `You exceeded your current requests list` 时，降低API调用频率。
   - <strong>减少 Token 消耗</strong>：收到 `Allocated quota exceeded` 或 `You exceeded your current quota` 时，缩短输入或限制输出长度。
   - <strong>平滑请求速率</strong>：收到 `Request rate increased too quickly` 时，采用匀速调度、指数退避或请求队列将请求均匀分散，避免瞬时高峰。
3. <strong>添加备选模型</strong>

   触发限流后切换到备用模型继续生成，可降低失败概率、提升吞吐量。以下代码在调用 `qwen-plus` 触发限流后，自动改用 `qwen-flash` 重试。也可以选择不同系列的模型（如 qwen-flash）作为备选模型，进一步降低主备模型同时限流的风险。

   <Accordion title="示例代码">
     ```python expandable
     import os
     import asyncio
     from openai import AsyncOpenAI, APIStatusError

     # 配置
     API_KEY = os.getenv("DASHSCOPE_API_KEY")
     # 主用模型
     MODEL = "qwen-plus"
     # 备选模型
     BACKUP_MODEL = "qwen-flash"
     # 测试问题
     QUESTION = "你是谁？"
     # 并发设置
     NUM_REQUESTS = 10

     client = AsyncOpenAI(
         api_key=API_KEY,
         # 以下为华北2（北京）地域的URL，请将WorkspaceId替换为真实的业务空间ID。
         base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
     )

     async def send_request(model):
         """发送单个请求"""
         try:
             await client.chat.completions.create(
                 model=model,
                 messages=[{"role": "user", "content": QUESTION}]
             )
             return True
         except APIStatusError as e:
             if e.status_code == 429:
                 print(f"[限流触发] 模型 {model}")
                 return False
             raise
         except Exception as e:
             print(f"[请求失败] 模型 {model}，错误：{e}")
             return False

     async def task(i):
         # 尝试主模型
         if await send_request(MODEL):
             return True
         # 限流时尝试备用模型
         return await send_request(BACKUP_MODEL)

     async def main():
         results = await asyncio.gather(*(task(i) for i in range(NUM_REQUESTS)))
         print(f"成功请求: {sum(results)}, 失败请求: {len(results) - sum(results)}")

     if __name__ == "__main__":
         asyncio.run(main())
     ```
   </Accordion>
4. <strong>拆分任务</strong>：长对话或大型文档会快速消耗大量 Token。将大批量任务拆分为小批次，分时段提交。
5. <strong>批量推理</strong>：无需实时响应时，使用[批量推理](/zh/model-studio/batch-inference)（Batch API）。批量请求不受实时限流约束，但需考虑排队和处理时间。

### 如何控制 Token 用量或费用支出？ <span id="faq_cost_ctrl_h3" />

限流仅约束单位时间内的调用速率，不限制累计用量。如需控制 Token 用量或费用支出，可通过以下方式管理：

- <strong>设置消费限额与费用告警</strong>：在<strong>账单费用</strong>卡片设置<strong>费用告警</strong>，开启月度消费限额并配置阈值通知，达到阈值即提醒，避免超额支出。详见[账单查询与成本管理](/zh/model-studio/bill-query-and-cost-management)。
- <strong>开启免费额度用完即停</strong>：对支持免费额度的模型，可开启<strong>免费额度用完即停</strong>，免费额度耗尽后自动停止调用，避免产生额外费用。详见[新人免费额度](/zh/model-studio/new-free-quota)。
- <strong>监控模型调用量</strong>：定期查看各模型的 Token 用量，及时发现异常增长，参见上文[如何查看模型调用量？](/zh/model-studio/rate-limit#2c4544e8d8wy6)。

### 充值后是否还会被限流？ <span id="faq_recharge_limit_h3" />

充值不改变模型默认的 RPM 和 TPM 限流阈值。限流按阿里云主账号维度配置，与计费相互独立；充值（按量付费）仅确保账号不因欠费停服，不会提升限流值。

如需更高的限流额度，请联系商务经理申请。

## 文本生成-千问 <span id="3392a1d49fftj" />

### 千问语言模型 <span id="ae2b12964a71a" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-06-08
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-preview
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-17
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-max

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus-2026-04-02
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash-2026-04-16
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-04-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-02-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-latest

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-07-14

            （qwen-plus-0714）
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-04-28

            （qwen-plus-0428）
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-01-25

            （qwen-plus-0125）
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            150,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-long

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            150,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-06-08
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus-2026-04-02
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash-2026-04-16
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-02-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-06-08
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-max

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus-2026-04-02
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash-2026-04-16
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-04-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-02-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-latest
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-07-14

            (qwen-plus-0714)
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-04-28

            (qwen-plus-0428)
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-01-25

            (qwen-plus-0125)
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            150,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-06-08
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus-2026-04-02
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash-2026-04-16
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-plus-2026-02-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            欧盟
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            欧盟
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            35,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            欧盟
          </td>

          <td style={{ verticalAlign: "top" }}>
            35,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            欧盟
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            150,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-max-2026-05-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            日本
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-plus-2026-05-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            日本
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus-2026-04-02
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash-2026-04-16
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-max-0902
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            150,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-flash-2026-07-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-flash-2026-02-23
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问VL（视觉理解/图生文） <span id="590df02870hyp" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            欧盟
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问Omni <span id="5b7c656e788u8" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management#sec-tier-h2)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management#sec-tier-h2)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            2000000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            2000000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            2000000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            30000
          </td>

          <td style={{ verticalAlign: "top" }}>
            2000000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问Omni-Realtime <span id="a410617af4cte" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-realtime-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-realtime-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-omni-flash-realtime-2025-09-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-omni-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-plus-realtime-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-omni-flash-realtime-2026-03-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-omni-flash-realtime-2025-09-15
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问OCR（文字提取） <span id="9c49551dfbk4r" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-ocr
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr-2025-11-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            30,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr-2024-10-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr-2025-11-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr-2025-11-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-vl-ocr-2025-11-20
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问Audio（音频理解） <span id="2deeb92f4f8de" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-turbo
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-turbo-latest
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            无 TPM 限制
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问Coder <span id="f7770a0349vq5" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-coder-flash-2025-07-28
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问翻译模型 <span id="19090eae8arxa" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            25,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            35,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-lite
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            25,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            35,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-lite
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-lite
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-lite
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            25,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            35,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-mt-lite
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Qwen-MT-Uni <span id="uni-rate-limit" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%"  , overflowWrap: "anywhere" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "18.75%" }} /><col style={{ width: "18.75%" }} /><col style={{ width: "18.75%" }} /><col style={{ width: "18.75%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={4} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟消耗Token数（TPM）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>异步并发数</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>异步排队数</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-mt-uni</p></td><td style={{ verticalAlign: "top" }}><p>162</p></td><td style={{ verticalAlign: "top" }}><p>2,592,000</p></td><td style={{ verticalAlign: "top" }}><p>3</p></td><td style={{ verticalAlign: "top" }}><p>500</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 千问数据挖掘模型 <span id="9828e02499d55" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-doc-turbo
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 千问深入研究模型 <span id="9884d121bfy7o" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-deep-research
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 通义晓蜜对话分析模型 <span id="cd57449384qjp" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-xiaomi-analysis-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-xiaomi-analysis-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 文本生成-千问-开源版 <span id="6b08d31e9cg77" />

### 千问语言模型开源版 <span id="a1264d06b9yyl" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-2.4t-a95b
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-27b
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-397b-a17b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-122b-a10b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-397b-a17b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-122b-a10b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-2.4t-a95b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-397b-a17b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-122b-a10b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.6-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-397b-a17b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-122b-a10b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-27b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-35b-a3b
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 文本生成-第三方模型 <span id="5ac9d0fa5bzgw" />

### DeepSeek <span id="f5d967328bgje" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-r1-distill-qwen-1.5b
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-r1-distill-llama-70b
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            日本
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            日本
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            日本
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35.03%" }} />

        <col style={{ width: "15.01%" }} />

        <col style={{ width: "25.02%" }} />

        <col style={{ width: "24.94%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash-1017
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-flash-0731
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### DeepSeek-硅基流动直供 <span id="8981b276d2fab" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            siliconflow/deepseek-v3.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            siliconflow/deepseek-v3.1-terminus
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            siliconflow/deepseek-r1-0528
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            siliconflow/deepseek-v3-0324
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### DeepSeek-快手万擎直供 <span id="vanchin-deepseek-ratelimit-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v3.2-think
          </td>

          <td style={{ verticalAlign: "top" }}>
            30
          </td>

          <td style={{ verticalAlign: "top" }}>
            600,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v3.1-terminus
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-r1
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v3
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-ocr
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v4-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            300,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v4-pro-0813
          </td>

          <td style={{ verticalAlign: "top" }}>
            30
          </td>

          <td style={{ verticalAlign: "top" }}>
            600,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vanchin/deepseek-v4.1-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            30
          </td>

          <td style={{ verticalAlign: "top" }}>
            600,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Kimi <span id="a9ee85ed0emvu" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.6
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td colSpan={2} style={{ verticalAlign: "top" }}>
            [动态限流](/zh/model-studio/quota-management)
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi-k2.7-code
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Kimi-月之暗面直供 <span id="4c5e80ec70q4z" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi/kimi-k3
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            500

            > 同一个阿里云百炼API Key 下，在 5 个模型中共享 500 RPM 限流配额。即这 5 个模型的每分钟请求总数加起来不能超过 500。
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            3,000,000

            > 同一个阿里云百炼API Key 下，在 5 个模型中共享 3000000 TPM 限流配额。即这 5 个模型的每分钟 Token 消耗总数加起来不能超过 3000000。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi/kimi-k2.7-code-highspeed
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi/kimi-k2.7-code
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi/kimi-k2.6
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kimi/kimi-k2.5
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### GLM <span id="c66e2c68c1w9s" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            美国
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            15,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35.03%" }} />

        <col style={{ width: "15.01%" }} />

        <col style={{ width: "25.02%" }} />

        <col style={{ width: "24.94%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35.03%" }} />

        <col style={{ width: "15.01%" }} />

        <col style={{ width: "25.02%" }} />

        <col style={{ width: "24.94%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            glm-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### GLM-智谱直供 <span id="cb01c6d8c8zxp" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5.3
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5.3-Flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5.3-FlashX
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5.2
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            ZHIPU/GLM-5
          </td>

          <td style={{ verticalAlign: "top" }}>
            200
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### MiniMax <span id="cf86f6b6a7cku" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax-M2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### MiniMax-稀宇科技直供 <span id="d92c3ff8f4tw1" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/MiniMax-M3
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/MiniMax-M2.7
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/MiniMax-M2.5
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/MiniMax-M2.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### MiMo-小米直供 <span id="54b32ee55e7zu" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            xiaomi/mimo-v2.6-pro-ultraspeed
          </td>

          <td style={{ verticalAlign: "top" }}>
            100
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            xiaomi/mimo-v2.5-pro
          </td>

          <td style={{ verticalAlign: "top" }}>
            100
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Stepfun-阶跃星辰直供 <span id="sf_ratelimit_h3" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            stepfun/step-3.7-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            stepfun/step-5-preview
          </td>

          <td style={{ verticalAlign: "top" }}>
            500
          </td>

          <td style={{ verticalAlign: "top" }}>
            10,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Unisound-云知声直供

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            unisound/unisound-u2
          </td>

          <td style={{ verticalAlign: "top" }}>
            300
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 图像生成 <span id="5998fd159df49" />

### 千问（Qwen-Image） <span id="f812e7c63axvx" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "23.078698%" }} /><col style={{ width: "38.460651%" }} /><col style={{ width: "38.460651%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-06-22</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-04-22</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-03-03</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0</p></td><td style={{ verticalAlign: "top" }}><p>2 次/秒</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-2026-03-03</p></td><td style={{ verticalAlign: "top" }}><p>2 次/秒</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-mt-image-2.0</p></td><td style={{ verticalAlign: "top" }}><p>60 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-mt-image</p></td><td style={{ verticalAlign: "top" }}><p>1 次/秒</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 2</p></td></tr></tbody></table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "19.99%" }} /><col style={{ width: "13.31%" }} /><col style={{ width: "33.35%" }} /><col style={{ width: "33.35%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-06-22</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-04-22</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-pro-2026-03-03</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/秒</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.0-2026-03-03</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2 次/秒</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-mt-image-2.0</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>60 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 2</p></td></tr></tbody></table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "19.99%" }} /><col style={{ width: "13.31%" }} /><col style={{ width: "33.35%" }} /><col style={{ width: "33.35%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr></tbody></table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "19.99%" }} /><col style={{ width: "13.31%" }} /><col style={{ width: "33.35%" }} /><col style={{ width: "33.35%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr></tbody></table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "19.99%" }} /><col style={{ width: "13.31%" }} /><col style={{ width: "33.35%" }} /><col style={{ width: "33.35%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>任务下发接口调用限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-3.0</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-pro</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>20 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>qwen-image-2.1-turbo</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>120 次/分钟</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制 / 异步接口 10</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 文生图-Z-Image <span id="e17ad85fd8wwl" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>z-image-turbo</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "35%" }} /><col style={{ width: "15%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>z-image-turbo</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 万相 <span id="513e0a3df24v7" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "23.078698%" }} /><col style={{ width: "38.460651%" }} /><col style={{ width: "38.460651%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-image-pro</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-image</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-image</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2i</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-t2i-preview</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2i-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2i-flash</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-t2i-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-t2i-turbo</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.0-t2i-turbo</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-i2i-preview</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-imageedit</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-v1</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-x-painting</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-sketch-to-image-lite</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr></tbody></table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2i</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-image</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-image-pro</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-image</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-image</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2i</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-t2i-preview</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2i-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2i-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-t2i-turbo</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-t2i-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-i2i-preview</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2i</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-image</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 图像编辑与生成 <span id="980e34f881ihz" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>shoemodel-v1</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-virtualmodel</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-style-repaint-v1</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx-poster-generation-v1</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>virtualmodel-v2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>image-instance-segmentation</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>image-erase-completion</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 人物写真生成-FaceChain <span id="88756e5f858dv" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>facechain-facedetect</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>facechain-finetune</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 图像生成-第三方模型 <span id="dc5de83bf45os" />

### 可灵系列 <span id="fdd6e348d2md4" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每秒钟调用次数（RPS）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kling/kling-v3-omni-image-generation
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            10

            > 同一阿里云百炼API Key 下，可灵系列的 5 个模型（[图像](/zh/model-studio/rate-limit#fdd6e348d2md4)及[视频](/zh/model-studio/rate-limit#kling-third-party-title)）共享 10 个并发数。即这 5 个模型处于运行状态的任务总数加起来不能超过 10 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kling/kling-v3-image-generation
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Vidu系列 <span id="vidu-img-third-party-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟请求数RPM限制</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/vidu-image-pro\_reference2image
          </td>

          <td rowSpan={6} style={{ verticalAlign: "top" }}>
            300
          </td>

          <td rowSpan={6} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 下，Vidu参考生图系列的模型共享 5 个并发数。即所有模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/vidu-image-lite\_reference2image
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/vidu-image\_reference2image
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-fast\_reference2image
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-pro\_reference2image
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-fast\_reference2image
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 音频生成 <span id="audio-generation-rate-limit" />

<Tabs>
  <Tab title="华北2（北京）">
| 模型名称                    | 每秒钟调用次数（RPS） |
| ----------------------- | ------------ |
| qwen-audio-3.1-tts-next | 3            |
  </Tab>
</Tabs>

## 音乐生成 <span id="757a2950ads1i" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "50%" }} /><col style={{ width: "50%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>fun-music-preview</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-music-v1</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 语音对话 <span id="55945fd2b5bbf" />

### 实时语音对话 <span id="739e085c10fxx" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.1-realtime-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-realtime-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-realtime-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "29.16%" }} />

        <col style={{ width: "29.16%" }} />

        <col style={{ width: "20.8%" }} />

        <col style={{ width: "20.88%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.1-realtime-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-realtime-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-realtime-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 语音合成（文本转语音） <span id="16c0080f6axd3" />

### Qwen-Audio-TTS <span id="79352135767l3" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "39.972401%" }} /><col style={{ width: "60.027599%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-tts-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-tts-plus</span></p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-tts-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.76%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.2%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-tts-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-tts-plus</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-tts-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen3-TTS <span id="476158da2fwdl" />

<Tabs>
  <Tab title="华北2（北京）">
    <Tabs>
      <Tab title="Qwen3-TTS-Flash">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "29.231831%" }} /><col style={{ width: "70.768169%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-tts-flash</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="新加坡">
    <Tabs>
      <Tab title="Qwen3-TTS-Flash">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "25.42%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "61.54%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-tts-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

### Qwen3-TTS-Realtime <span id="0deabef960pq1" />

<Tabs>
  <Tab title="华北2（北京）">
    <Tabs>
      <Tab title="Qwen3-TTS-Flash-Realtime">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "29.231831%" }} /><col style={{ width: "70.768169%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-tts-flash-realtime</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="新加坡">
    <Tabs>
      <Tab title="Qwen3-TTS-Flash-Realtime">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "25.42%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "61.54%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-tts-flash-realtime</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

### Qwen3-TTS声音复刻 <span id="f4de4b96c09v6" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "39.880405%" }} /><col style={{ width: "60.119595%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-voice-enrollment</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.68%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.28%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen-voice-enrollment</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>180</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### CosyVoice <span id="95cc317401h9u" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "39.972401%" }} /><col style={{ width: "60.027599%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3.5-plus</p></td><td rowSpan={6} style={{ verticalAlign: "top" }}><p>3</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3.5-flash</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3-plus</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3-flash</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v2</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.76%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.2%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td rowSpan={2} style={{ verticalAlign: "top" }}><p>3</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>cosyvoice-v3-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen-Audio-TTS/CosyVoice声音复刻/设计 <span id="86517f838d10u" />

Qwen-Audio-TTS/CosyVoice声音复刻/设计共用一个模型，共用限流额度。

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "39.880405%" }} /><col style={{ width: "60.119595%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>voice-enrollment</p></td><td style={{ verticalAlign: "top" }}><p>10</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.68%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.28%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>voice-enrollment</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>10</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Sambert <span id="3f9ff5ba2b5tt" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "49.9925%" }} /><col style={{ width: "50.0075%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型服务</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>Sambert系列模型</p></td><td style={{ verticalAlign: "top" }}><p>20</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 语音合成（文本转语音）-第三方模型 <span id="bfc779c80fj0j" />

### MiniMax-稀宇科技直供 <span id="7ba64ebc288nj" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗字符数</strong>

            > <strong>仅含输入字符数</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/speech-2.8-hd
          </td>

          <td style={{ verticalAlign: "top" }}>
            20
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/speech-02-hd
          </td>

          <td style={{ verticalAlign: "top" }}>
            20
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/speech-2.8-turbo
          </td>

          <td style={{ verticalAlign: "top" }}>
            20
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            MiniMax/speech-02-turbo
          </td>

          <td style={{ verticalAlign: "top" }}>
            20
          </td>

          <td style={{ verticalAlign: "top" }}>
            20,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 语音识别（语音转文本）与翻译（语音转成指定语种的文本） <span id="1b9e6dea2dr4x" />

### Qwen3-LiveTranslate-Flash <span id="4be13d2d4a3r9" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "39.972401%" }} />

        <col style={{ width: "29.967801%" }} />

        <col style={{ width: "30.059798%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-livetranslate-flash
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            100
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-livetranslate-flash-2025-12-01
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "34.76%" }} />

        <col style={{ width: "13.04%" }} />

        <col style={{ width: "26.06%" }} />

        <col style={{ width: "26.14%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-livetranslate-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            100
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-livetranslate-flash-2025-12-01
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Qwen-LiveTranslate-Flash-Realtime <span id="ea64133a8buvv" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "39.972401%" }} />

        <col style={{ width: "29.967801%" }} />

        <col style={{ width: "30.059798%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-livetranslate-flash-realtime
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            10
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-livetranslate-flash-realtime
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-livetranslate-flash-realtime-2026-05-19
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "34.76%" }} />

        <col style={{ width: "13.04%" }} />

        <col style={{ width: "26.06%" }} />

        <col style={{ width: "26.14%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.8-livetranslate-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            10
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            100,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-livetranslate-flash-realtime
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.5-livetranslate-flash-realtime-2026-05-19
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Qwen-Audio-ASR-Message <span id="asr-message" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "60%" }} /><col style={{ width: "40%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}>模型名称</th><th style={{ verticalAlign: "top" }}>每分钟调用次数（RPM）</th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}>qwen-audio-3.1-asr-flash-message</td><td style={{ verticalAlign: "top" }}>1200</td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "50%" }} /><col style={{ width: "20%" }} /><col style={{ width: "30%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}>模型名称</th><th style={{ verticalAlign: "top" }}>服务部署范围</th><th style={{ verticalAlign: "top" }}>每分钟调用次数（RPM）</th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}>qwen-audio-3.1-asr-flash-message</td><td style={{ verticalAlign: "top" }}>国际</td><td style={{ verticalAlign: "top" }}>1200</td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen-Audio-ASR-Streaming <span id="6314d076aabhs" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "70%" }} />

        <col style={{ width: "30%" }} />
      </colgroup>

      <thead>
        <tr>
          <th style={{ verticalAlign: "top" }}>
            **模型名称**
          </th>

          <th style={{ verticalAlign: "top" }}>
            **每分钟调用次数（RPM）**
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.1-asr-flash-streaming
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            1200
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-asr-flash-streaming
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "50%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th style={{ verticalAlign: "top" }}>
            **模型名称**
          </th>

          <th style={{ verticalAlign: "top" }}>
            **服务部署范围**
          </th>

          <th style={{ verticalAlign: "top" }}>
            **每分钟调用次数（RPM）**
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.1-asr-flash-streaming
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            1200
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-audio-3.0-asr-flash-streaming
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Qwen-Audio-ASR-Filetrans <span id="29376bdaa5s47" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "65%" }} /><col style={{ width: "35%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-asr-flash-filetrans</span></p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-asr-flash-filetrans</span></p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "45%" }} /><col style={{ width: "25%" }} /><col style={{ width: "30%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-asr-flash-filetrans</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-asr-flash-filetrans</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen-Audio-ASR <span id="8e353130f9pmp" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "65%" }} /><col style={{ width: "35%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-asr-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-asr-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "45%" }} /><col style={{ width: "25%" }} /><col style={{ width: "30%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.1-asr-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><span>qwen-audio-3.0-asr-flash</span></p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen3-ASR <span id="7d2f0509a3n03" />

<Tabs>
  <Tab title="华北2（北京）">
    <Tabs>
      <Tab title="Qwen3-ASR-Flash-Filetrans">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "40.075897%" }} /><col style={{ width: "59.924103%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash-filetrans</p></td><td rowSpan={2} style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
      </Tab>

      <Tab title="Qwen3-ASR-Flash">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "40.052898%" }} /><col style={{ width: "59.947102%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash</p></td><td rowSpan={3} style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="新加坡">
    <Tabs>
      <Tab title="Qwen3-ASR-Flash-Filetrans">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.85%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.11%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash-filetrans</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td rowSpan={2} style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
      </Tab>

      <Tab title="Qwen3-ASR-Flash">
        <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.83%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.13%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td rowSpan={3} style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.83%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.13%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash</p></td><td style={{ verticalAlign: "top" }}><p>美国</p></td><td rowSpan={2} style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Qwen3-ASR-Realtime <span id="9f21be56e82vj" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "40.052898%" }} /><col style={{ width: "59.947102%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash-realtime</p></td><td rowSpan={3} style={{ verticalAlign: "top" }}><p>20</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "34.83%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "52.13%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>qwen3-asr-flash-realtime</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td rowSpan={3} style={{ verticalAlign: "top" }}><p>20</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Fun-ASR <span id="8c50a9f1e526h" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "36.706532%" }} /><col style={{ width: "63.293468%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>fun-asr</p></td><td rowSpan={6} style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-flash-2026-06-15</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "31.98%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "54.98%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>fun-asr</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-flash-2026-06-15</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>600</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Fun-ASR-Realtime <span id="c9c9419f7btw4" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "57.072217%" }} /><col style={{ width: "42.927783%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-realtime</p></td><td rowSpan={6} style={{ verticalAlign: "top" }}><p>20</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-realtime-2026-02-28</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-flash-8k-realtime</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-flash-8k-realtime-2026-01-28</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "49.63%" }} /><col style={{ width: "13.04%" }} /><col style={{ width: "37.33%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>fun-asr-realtime</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td rowSpan={2} style={{ verticalAlign: "top" }}><p>20</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### Paraformer <span id="71c5d28fb01yz" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "49.9925%" }} /><col style={{ width: "50.0075%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>paraformer-realtime-v2</p></td><td rowSpan={4} style={{ verticalAlign: "top" }}><p>20</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>paraformer-realtime-8k-v2</p></td></tr></tbody></table>

    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "49.9925%" }} /><col style={{ width: "50.0075%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每分钟调用次数（RPM）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>paraformer-v2</p></td><td style={{ verticalAlign: "top" }}><p>1,200</p></td></tr></tbody></table>

    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>paraformer-8k-v2</p></td><td style={{ verticalAlign: "top" }}><p>20</p></td><td style={{ verticalAlign: "top" }}><p>100</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 视频生成 <span id="d809366847gza" />

### HappyHorse系列 <span id="hh-third-party-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-t2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-i2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-r2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-t2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-i2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-r2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-video-edit</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "35%" }} /><col style={{ width: "15%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-video-edit</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "35%" }} /><col style={{ width: "15%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-t2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-i2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-r2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-t2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-i2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-r2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-video-edit</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "35%" }} /><col style={{ width: "15%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-video-edit</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "35.04%" }} /><col style={{ width: "15%" }} /><col style={{ width: "24.98%" }} /><col style={{ width: "24.98%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流值（任何一个值超出即触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>正在处理中的任务数（并发）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.1-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>happyhorse-1.0-video-edit</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 万相系列 <span id="018a73300efzz" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "23.078698%" }} /><col style={{ width: "38.460651%" }} /><col style={{ width: "38.460651%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-r2v-2026-06-12</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v-2026-06-12</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v-2026-04-25</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-t2v-preview</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-t2v-turbo</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-t2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-i2v-2026-04-25</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-i2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-i2v-preview</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-i2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-i2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-i2v-turbo</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-i2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-kf2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-kf2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wanx2.1-vace-plus</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-videoedit</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-r2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-s2v-detect</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>同步接口无限制</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-s2v</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-animate-move</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-animate-mix</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr></tbody></table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-r2v-2026-06-12</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2v</p></td><td style={{ verticalAlign: "top" }}><p>美国</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v</p></td><td style={{ verticalAlign: "top" }}><p>美国</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v-2026-06-12</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v-2026-04-25</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-t2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-t2v-preview</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-t2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-t2v-turbo</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-t2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-i2v-2026-04-25</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-i2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.5-i2v-preview</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-i2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-i2v-turbo</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-i2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-kf2v-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.1-vace-plus</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td><td style={{ verticalAlign: "top" }}><p>2</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-videoedit</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.7-r2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v-flash</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-animate-move</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.2-animate-mix</p></td><td style={{ verticalAlign: "top" }}><p>国际</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td></tr></tbody></table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-t2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-i2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan2.6-r2v</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "20%" }} /><col style={{ width: "13.33%" }} /><col style={{ width: "33.33%" }} /><col style={{ width: "33.33%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>服务部署范围</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video-prime</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>wan3.0-video</p></td><td style={{ verticalAlign: "top" }}><p>全球</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 舞动人像AnimateAnyone <span id="02e62576072f0" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>animate-anyone-detect</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1算力单元支持2并发</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>animate-anyone</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td><td style={{ verticalAlign: "top" }}><p>1算力单元支持1并发</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 声动人像VideoRetalk <span id="4bb36ecec8el3" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>videoretalk</p></td><td style={{ verticalAlign: "top" }}><p>1</p></td><td style={{ verticalAlign: "top" }}><p>1</p><p>在同一时刻，只有1个作业实际处于运行状态，其他队列中的作业处于排队状态。</p></td></tr></tbody></table>
  </Tab>
</Tabs>

### 视频风格重绘 <span id="101f9ad4210ev" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>每秒钟调用次数（RPS）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>video-style-transform</p></td><td style={{ verticalAlign: "top" }}><p>20</p></td><td style={{ verticalAlign: "top" }}><p>2</p><p>在同一时刻，只有1个作业实际处于运行状态，其他队列中的作业处于排队状态。</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 视频生成-第三方模型 <span id="80dffccfb0dax" />

### 爱诗系列 <span id="d64654d0f0rfx" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.226315%" }} />

        <col style={{ width: "29.386842%" }} />

        <col style={{ width: "29.386842%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟任务下发接口RPM限制</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-lipsync
          </td>

          <td style={{ verticalAlign: "top" }}>
            300
          </td>

          <td rowSpan={3} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 在 3 个模型间共享额度。即这 3 个模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-motioncontrol
          </td>

          <td style={{ verticalAlign: "top" }}>
            300
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-upscale
          </td>

          <td style={{ verticalAlign: "top" }}>
            300
          </td>
        </tr>
      </tbody>
    </table>

    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.18%" }} />

        <col style={{ width: "29.41%" }} />

        <col style={{ width: "29.41%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每秒钟调用次数（RPS）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-c1-t2v
          </td>

          <td rowSpan={4} style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={4} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 在 4个模型间共享额度。即这 4个模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-c1-it2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-c1-kf2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-c1-r2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v6-r2v-omni
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={5} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 在 5 个模型间共享额度。即这 5 个模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v6-t2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v6-it2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v6-kf2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v6-r2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v5.6-t2v
          </td>

          <td rowSpan={4} style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={4} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 在 4 个模型间共享额度。即这 4 个模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v5.6-it2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v5.6-kf2v
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            pixverse/pixverse-v5.6-r2v
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 可灵系列 <span id="kling-third-party-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />

        <col style={{ width: "33.33%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每秒钟调用次数（RPS）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            kling/kling-v3-omni-video-generation
          </td>

          <td rowSpan={3} style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={3} style={{ verticalAlign: "top" }}>
            10

            > 同一阿里云百炼API Key 下，可灵系列的 5 个模型（[图像](/zh/model-studio/rate-limit#fdd6e348d2md4)及[视频](/zh/model-studio/rate-limit#kling-third-party-title)）共享 10 个并发数。即这 5 个模型处于运行状态的任务总数加起来不能超过 10 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kling/kling-v3-turbo-video-generation
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            kling/kling-v3-video-generation
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### Vidu系列 <span id="vidu-third-party-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "23.078698%" }} />

        <col style={{ width: "38.460651%" }} />

        <col style={{ width: "38.460651%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每秒钟调用次数（RPS）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-ad\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={20} style={{ verticalAlign: "top" }}>
            5

            > 同一个阿里云百炼API Key 在 20 个模型间共享并发额度。即这 20 个模型处于运行状态的任务总数加起来不能超过 5 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-drama\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-pro-fast\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-turbo\_text2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-pro\_text2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2\_text2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-turbo\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-pro\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-turbo\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-pro\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-pro-fast\_img2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-turbo\_start-end2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-pro\_start-end2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-turbo\_start-end2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-pro\_start-end2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-mix\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq3-turbo\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2-pro\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            vidu/viduq2\_reference2video
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### MiniMax系列 <span id="minimax-h3-video-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "41.176471%" }} /><col style={{ width: "29.411765%" }} /><col style={{ width: "29.411765%" }} /></colgroup><thead><tr><th rowSpan={2} style={{ verticalAlign: "top" }}><p><strong>模型名称</strong></p></th><th colSpan={2} style={{ verticalAlign: "top" }}><p><strong>限流条件（超出任一数值时触发限流）</strong></p></th></tr><tr><th style={{ verticalAlign: "top" }}><p><strong>每分钟任务下发接口RPM限制</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>同时处理中任务数量（并发数）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>MiniMax/MiniMax-H3</p></td><td style={{ verticalAlign: "top" }}><p>300</p></td><td style={{ verticalAlign: "top" }}><p>5</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 3D模型生成-第三方模型 <span id="0b7e66f09e7lj" />

### Tripo系列 <span id="tripo-third-party-title" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟任务下发接口RPM限制</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>同时处理中任务数量（并发数）</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            Tripo/Tripo-H3.1
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>

          <td rowSpan={2} style={{ verticalAlign: "top" }}>
            10

            > 同一个阿里云百炼API Key 在 2 个模型间共享额度。即这 2 个模型处于运行状态的任务总数加起来不能超过 10 个。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            Tripo/Tripo-P1.0
          </td>

          <td style={{ verticalAlign: "top" }}>
            5
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 向量模型 <span id="68ae4e7d1ehra" />

### 文本向量 <span id="953ddcd76495l" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）/作业数</strong>

            > <strong>仅输入Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-text-embedding
          </td>

          <td style={{ verticalAlign: "top" }}>
            24,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-text-embedding-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            24,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v1

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v2

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v3

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v4

            > 用[Batch API](/zh/model-studio/batch-interfaces-compatible-with-openai)调用服务时，不受限流限制。
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-async-v1
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            当前用户在系统通用文本向量异步作业排队中和运行中的作业数量不超过50个。

            另外，为了避免大量突发的作业占据太多资源，限制并发的作业数为3个，即任意时间，单个用户最多只有3个通用文本向量的异步作业在并发运行，其他的作业只能在队列中等待。
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-async-v2
          </td>

          <td style={{ verticalAlign: "top" }}>
            60
          </td>

          <td style={{ verticalAlign: "top" }}>
            当前用户在系统通用文本向量异步作业排队中和运行中的作业数量不超过50个。

            另外，为了避免大量突发的作业占据太多资源，限制并发的作业数为3个，即任意时间，单个用户最多只有3个通用文本向量的异步作业在并发运行，其他的作业只能在队列中等待。
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-text-embedding
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            24,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v4
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v3
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            6,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            24,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="中国香港">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            text-embedding-v4
          </td>

          <td style={{ verticalAlign: "top" }}>
            中国香港
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,800
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 多模态向量 <span id="d59f78d5c18y5" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>仅输入Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-embedding
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,400
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen2.5-vl-embedding
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            600,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-embedding-vision-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-embedding-vision-flash
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            200,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-embedding-vision-flash-2026-03-06
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            9,600,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-embedding-vision-plus-2026-03-06
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            9,600,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            multimodal-embedding-v1
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 排序模型 <span id="6b57066d2aglk" />

### 排序模型 <span id="1b5bd6eddbdau" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3.7-text-rerank
          </td>

          <td style={{ verticalAlign: "top" }}>
            3,000
          </td>

          <td style={{ verticalAlign: "top" }}>
            9,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-rerank
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,400
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-vl-rerank
          </td>

          <td style={{ verticalAlign: "top" }}>
            600
          </td>

          <td style={{ verticalAlign: "top" }}>
            9,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            gte-rerank-v2
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,040
          </td>

          <td style={{ verticalAlign: "top" }}>
            4,980,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen3-rerank
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,400
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            gte-rerank-v2
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,040
          </td>

          <td style={{ verticalAlign: "top" }}>
            4,980,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 行业 <span id="e6785f7240c8r" />

### 意图理解 <span id="3921a60f269e3" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            tongyi-intent-detect-v3
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 角色扮演 <span id="86e73ce5885wo" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-character-2026-02-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character-ja
          </td>

          <td style={{ verticalAlign: "top" }}>
            国际
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-flash-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            500,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="德国（法兰克福）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="日本（东京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "35%" }} />

        <col style={{ width: "15%" }} />

        <col style={{ width: "25%" }} />

        <col style={{ width: "25%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>服务部署范围</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            qwen-plus-character
          </td>

          <td style={{ verticalAlign: "top" }}>
            全球
          </td>

          <td style={{ verticalAlign: "top" }}>
            120
          </td>

          <td style={{ verticalAlign: "top" }}>
            5,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 界面交互 <span id="2c80cf1f06pw2" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            gui-plus
          </td>

          <td style={{ verticalAlign: "top" }}>
            80
          </td>

          <td style={{ verticalAlign: "top" }}>
            540,000
          </td>
        </tr>

        <tr>
          <td style={{ verticalAlign: "top" }}>
            gui-plus-2026-02-26
          </td>

          <td style={{ verticalAlign: "top" }}>
            100
          </td>

          <td style={{ verticalAlign: "top" }}>
            540,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

### 决策模型 <span id="dm-ratelimit" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            decision-model-preview
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>

  <Tab title="新加坡">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
      <colgroup>
        <col style={{ width: "41.176471%" }} />

        <col style={{ width: "29.411765%" }} />

        <col style={{ width: "29.411765%" }} />
      </colgroup>

      <thead>
        <tr>
          <th rowSpan={2} style={{ verticalAlign: "top" }}>
            <strong>模型名称</strong>
          </th>

          <th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟消耗Token数（TPM）</strong>

            > <strong>含输入与输出Token</strong>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td style={{ verticalAlign: "top" }}>
            decision-model-preview
          </td>

          <td style={{ verticalAlign: "top" }}>
            1,200
          </td>

          <td style={{ verticalAlign: "top" }}>
            2,000,000
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

## 已下线模型 <span id="14dd0e482478d" />

详细信息，请参见 [模型下线机制说明](/zh/model-studio/model-depreciation) 。