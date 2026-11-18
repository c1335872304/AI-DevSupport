# 独立端到端回答评测：逐题原始回答与审阅证据

2026-10-20；首次执行结果，未重跑筛选。引用令牌不公开，正文与锚点摘要保留。

## E01 · deepseek · fact

文档校对：DeepSeek的JSON Output只设置response_format就够了吗？提示里应包含什么，如何避免JSON被截断，空content是否属于已知情况？

判分要求：response_format=json_object；提示含json并给格式样例；合理max_tokens避免截断；空content是已知可能情况，可调整prompt，不保证必然解决

审阅：PARTIAL。三个事实要求满足；实际只引用#1 chunk1，缺少response_format设置所在的chunk0。另有get_document和检索#8提供全文相关证据，但不是回答实际引用的锚点。自动创建工单。

### 原始回答

根据已检索到的 DeepSeek 官方文档，就您提出的几个校对点答复如下：

**1. 只设置 response_format 够不够？**
不够。文档要求同时满足：将 `response_format` 设为 `{'type': 'json_object'}`；并且在传入的 system 或 user prompt 中必须含有 `json` 字样。

**2. 提示里应包含什么？**
prompt 中除必须出现 `json` 字样外，还应给出希望模型输出的 JSON 格式样例，以指导模型输出合法 JSON。

**3. 如何避免 JSON 被截断？**
文档建议合理设置 `max_tokens` 参数，防止 JSON 字符串被中途截断。

**4. 空 content 是否属于已知情况？**
文档说明：使用 JSON Output 功能时，API 有概率返回空的 content；官方表示正在积极优化，并建议尝试修改 prompt 以缓解此类问题。

以上均为文档中的通用规则说明，不代表对您本次具体请求的核验结论。如需针对具体请求排查，请提供 request_id、HTTP 状态/错误码、接口地址及发生时间。

另外，本次已为您创建人工工单（工单号：CS_db2fc0f13ff9463ea39c），可进一步跟进。

来源#1: deepseek-json-output.md

### 实际引用锚点

来源#1：`deepseek-json-output.md`，chunk=1，version=8ca3370a65d15df5b4e04f783542de05，HTTP=200

~~~~text
中必须含有 `json` 字样，并给出希望模型输出的 JSON 格式的样例，以指导模型来输出合法 JSON。

- 需要合理设置 `max_tokens` 参数，防止 JSON 字符串被中途截断。

- 在使用 JSON Output 功能时，API 有概率会返回空的 content。我们正在积极优化该问题，您可以尝试修改 prompt 以缓解此类问题。

## 样例代码

这里展示了使用 JSON Output 功能的完整 Python 代码：

```
import jsonfrom openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com",)system_prompt = """The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format.
~~~~

## E02 · deepseek · fact

DeepSeek对话前缀续写要把哪种角色放在messages最后、加哪个标志，并使用什么Beta地址？请给三个配置要点。

判分要求：最后消息role=assistant；最后消息prefix=True；base_url=https://api.deepseek.com/beta

审阅：PASS。assistant、prefix=True、Beta地址三项正确，#1 chunk0及#2可支撑。额外自动转人工，单列运行缺陷。

### 原始回答

根据已检索到的 DeepSeek 官方文档，对话前缀续写（Beta）的三个配置要点如下：

1. **最后一条消息的角色设为 `assistant`**：`messages` 列表里最后一条消息的 `role` 必须为 `assistant`。
2. **在该消息上设置 `prefix: true`**：最后一条消息需设置 `prefix` 参数为 `True`，以强制模型从该 assistant 消息提供的前缀内容开始补全。
3. **使用 Beta 地址**：设置 `base_url="https://api.deepseek.com/beta"` 以开启 Beta 功能。

示例结构：

```python
messages = [
    {"role": "user", "content": "Please write quick sort code"},
    {"role": "assistant", "content": "```python\n", "prefix": True},
]
```

补充说明：以上为文档中的通用规则，不代表对您账户或某次请求的核验结果。另外，本次人工工单已创建成功（工单号：CS_0d0d5660531c4ec79a76），如需进一步排查具体请求，请提供 request_id、HTTP 状态/错误码、接口地址或发生时间。

来源#1: deepseek-prefix-completion.md
来源#2: deepseek-chat-completions.md

### 实际引用锚点

来源#1：`deepseek-prefix-completion.md`，chunk=0，version=4ebb1c1409b3573188a9f2105103b409，HTTP=200

~~~~text
# DeepSeek API：前缀续写

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[对话前缀续写（Beta）](https://api-docs.deepseek.com/zh-cn/guides/chat_prefix_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 对话前缀续写（Beta）

对话前缀续写沿用 [Chat Completion API](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion)，用户提供 assistant 开头的消息，来让模型补全其余的消息。

## 注意事项

- 使用对话前缀续写时，用户需确保 `messages` 列表里最后一条消息的 `role` 为 `assistant`，并设置最后一条消息的 `prefix` 参数为 `True`。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码
~~~~

来源#2：`deepseek-chat-completions.md`，chunk=5，version=acb1ddea03df5b2cb00d72d0f989cf84，HTTP=200

~~~~text
缀内容开始。

您必须设置 `base_url="https://api.deepseek.com/beta"` 来使用此功能。

reasoning_content stringnullable

(Beta) 用于思考模式下在[对话前缀续写](https://api-docs.deepseek.com/zh-cn/guides/chat_prefix_completion)功能下，作为最后一条 assistant 思维链内容的输入。使用此功能时，`prefix` 参数必须设置为 `true`。

role stringrequired

Possible values: [`tool`]

该消息的发起角色，其值为 `tool`。

content string | object[]

required

tool 消息的内容。可以是字符串，也可以是内容块数组（可以携带图片）。详见 [Vision 指南](https://api-docs.deepseek.com/zh-cn/guides/vision)。

oneOf

- Text content

- Array of content parts

string

-

Array [

oneOf

- Text content part

- Image content part
~~~~

## E03 · deepseek · insufficient

DeepSeek官方文档能否证明我这个账号在2026年12月31日一定享有5000 QPS且永不限流？请给可核验依据。

判分要求：不能据通用文档断言个人未来保障；不把本地Demo套餐当成DeepSeek生产账户证据；不得承诺5000QPS或永不限流

审阅：PARTIAL。没有承诺个人5000QPS或永不限流，也明确Demo不代表厂商账户；但被故障诊断模板替换，未直接解释文档无法证明个人未来保障，追问故障号偏离问题。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

当前没有匹配的已核验请求记录，不能确认本次故障原因。

下一步：补充脱敏请求号或故障发生时间，无需提供完整 Key

人工工单已创建：CS_41f87bbe90a4400eace7

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: deepseek-rate-limits.md
来源#2: deepseek-errors.md
来源#3: deepseek-token-usage.md

### 实际引用锚点

来源#1：`deepseek-rate-limits.md`，chunk=0，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
# DeepSeek API：限速与隔离

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[限速与隔离](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 限速与隔离

## 并发限速

对每个账号，DeepSeek API 不同模型的并发限制如下表所示。

若您有更高的并发需求，可提交[账号扩容申请工单](https://trtgsjkv6r.feishu.cn/share/base/form/shrcnda9jNKvhyYr8xb843xLEzc)，我们将根据您实际的业务需求匹配合适的并发量，扩容并不增加额外的费用。

|  | deepseek-flash | deepseek-v4-pro |
| --- | --- | --- |
| 并发限制 | 2500 | 500 |

- 一个请求从发出后，到模型响应完成之前记为一个并发

- 并发限制以账号粒度计，与 API Key 无关
~~~~

来源#2：`deepseek-errors.md`，chunk=0，version=a5df631500ec55a689b45d1a015e55ff，HTTP=200

~~~~text
# DeepSeek API：错误码

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[错误码](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 错误码

您在调用 DeepSeek API 时，可能会遇到以下错误。这里列出了相关错误的原因及其解决方法。

| 错误码 | 描述 |
| --- | --- |
| 400 - 格式错误 | 原因 ：请求体格式错误 解决方法 ：请根据错误信息提示修改请求体 |
| 401 - 认证失败 | 原因 ：API key 错误，认证失败 解决方法 ：请检查您的 API key 是否正确，如没有 API key，请先 创建 API key |
| 402 - 余额不足 | 原因 ：账号余额不足 解决方法 ：请确认账户余额，并前往 充值 页面进行充值 |
| 422 - 参数错误 | 原因 ：请求体参数错误 解决方法 ：请根据错误信息提示修改相关参数 |
~~~~

来源#3：`deepseek-token-usage.md`，chunk=0，version=17decf9b6c8356c6a67b7826e5e99e08，HTTP=200

~~~~text
# DeepSeek API：Token 用量

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Token 用量计算](https://api-docs.deepseek.com/zh-cn/quick_start/token_usage/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Token 用量计算

token 是模型用来表示自然语言文本的基本单位，也是我们的计费单元，可以直观的理解为“字”或“词”；通常 1 个中文词语、1 个英文单词、1 个数字或 1 个符号计为 1 个 token。

一般情况下模型中 token 和字数的换算比例大致如下：

- 1 个英文字符 ≈ 0.3 个 token。

- 1 个中文字符 ≈ 0.6 个 token。

但因为不同模型的分词不同，所以换算比例也存在差异，每一次实际处理 token 数量以模型返回为准，您可以从返回结果的 `usage` 中查看。

## 离线计算 Token 用量

您可以通过如下压缩包中的代码来运行 tokenizer，以离线计算一段文本的 Token 用量。
~~~~

## E04 · qwen · fact

把千问北京地域的Key放到新加坡的OpenAI兼容地址，能作为跨地域通用Key使用吗？Base URL还必须匹配哪一项？

判分要求：地域Key独立，不能跨地域通用；Base URL必须与同一计费方案的API Key配套

审阅：FAIL。跨地域Key和计费方案两项均未回答；诊断门替换为没有请求记录。来源#3声明qwen-structured-outputs，实际映射qwen-batch。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

当前没有匹配的已核验请求记录，不能确认本次故障原因。

下一步：补充脱敏请求号或故障发生时间，无需提供完整 Key

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-errors.md
来源#2: qwen-batch.md
来源#3: qwen-structured-outputs.md

### 实际引用锚点

来源#1：`qwen-errors.md`，chunk=145，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
.dashscope.aliyuncs.com/v1)</a>；Token Plan 团队版的专属 Base URL 可在控制台<strong>我的订阅</strong>的 API Key 区域查看。请确认同时更新了 API Key 和 Base URL，具体配置方法请分别参见接入AI工具与[快速开始](/zh/model-studio/token-plan-team-quickstart)。
- <strong>地域不匹配</strong>：API Key 和 Base URL 属于不同的地域，例如使用了华北2（北京）地域的 API Key 和新加坡地域的 Base URL。请确认您使用的 API Key 位于[北京](https://bailian.console.aliyun.com/settings/api-key)地域页面或[新加坡](https://bailian.console.aliyun.com/settings/api-key)地域页面，或[美国](https://bailian.console.aliyun.com/us-east-1)地域页面。各地域对应的 Base URL 如下：
~~~~

来源#2：`qwen-batch.md`，chunk=104，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
// 北京地域配置（默认）
          private static final String BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
          // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
          // private static final String BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
          // 注意：切换地域时，API Key也需要对应更换

          private static String API_KEY;
~~~~

来源#3：`qwen-batch.md`，chunk=36，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
坡地域：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
     */
    public class BatchAPITest {

        // 北京地域的 Base URL（默认）
        private static final String BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
        // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
        // private static final String BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";

        private static String API_KEY;
~~~~

## E05 · qwen · fact

Qwen text-embedding-v4可以一次提交15行、每行8192 Token，同时指定256维吗？请分别判定批量条数、单行长度和维度。

判分要求：每批最多10行，15行应拆分；每行最多8192 Token，边界允许；256维受支持

审阅：FAIL。15行拆批、8192边界、256维三项均未回答；相关文档已召回，却被诊断门替换。来源#2/#3声明文件与映射不同。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

当前没有匹配的已核验请求记录，不能确认本次故障原因。

下一步：已达到人工核查条件，等待真实工单创建结果

人工工单已创建：CS_9dad958fbf774d2fbd3f

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-embedding-api.md
来源#2: qwen-embedding-v4.md
来源#3: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-embedding-api.md`，chunk=20，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
- <strong>输入为字符串</strong>：最长支持 <strong>2,048</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>25</strong> 条（行），每条（行）最长支持 <strong>2,048</strong> Token。

        <strong>dimensions</strong> `integer` <strong>可选</strong>

        指定的向量维度，必须为以下值之一：`2560（仅适用于qwen3.7-text-embedding）、`2048（仅适用于`text-embedding-v4`）、1536（仅适用于`text-embedding-v4`）1024、768、512、256、128 或 64，默认值为1024。

        <strong>encoding\_format</strong> `string` <strong>可选</strong>

        用于控制返回的Embedding格式，入参支持`float`和`base64`，出参的Embedding数据也支持`float`和`base64`两种格式。实际返回格式取决于请求路由到的网关：
~~~~

来源#2：`qwen-embedding-api.md`，chunk=64，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
度和批量大小不同，具体如下：

        - <strong>qwen3.7-text-embedding、qwen3.7-text-embedding-flash 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>128,000</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>20</strong> 条（行），每条（行）最长支持 <strong>128,000</strong> Token。
        - <strong>text-embedding-v3 / v4 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>8,192</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>10</strong> 条（行），每条（行）最长支持 <strong>8,192</strong> Token。
        - <strong>text-embedding-v1 / v2 模型：</strong>
~~~~

来源#3：`qwen-embedding-api.md`，chunk=19，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
（array）或文件（file）。不同模型版本支持的文本长度和批量大小不同，具体如下：

        - <strong>qwen3.7-text-embedding 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>128,000</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>20</strong> 条（行），每条（行）最长支持 <strong>128,000</strong> Token。
        - <strong>text-embedding-v3 / v4 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>8,192</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>10</strong> 条（行），每条（行）最长支持 <strong>8,192</strong> Token。
        - <strong>text-embedding-v1 / v2 模型：</strong>
~~~~

## E06 · qwen · insufficient

Qwen的qwen-demo-exclusive-2099模型最大输出是否为512K？请确认准确的最大输出长度和官方发布日期。

判分要求：指出当前资料不足以确认该型号及限制/发布日期；不能把其他Qwen型号的参数套给该未知型号

审阅：PASS。明确未找到该型号，不能确认512K或发布日期；引用#2/#3是通用参数规则并明确不得外推。参数失败和额外工单保留在轨迹。

### 原始回答

您好，关于您询问的 `qwen-demo-exclusive-2099` 模型，我需要如实说明：**当前已授权的检索结果中没有该模型的任何信息**，因此无法确认其最大输出长度是否为 512K，也无法提供官方发布日期。

已检索到的文档仅包含通用参数说明，例如 `max_tokens` / `max_completion_tokens` 的默认值与最大值均为“模型的最大输出长度”，但未列出该具体型号的规格（来源#2: qwen-dashscope.md、来源#3: qwen-chat-completions.md）。这些通用规则不能用于推断该模型的具体数值。

另外，本次知识检索过程中出现了一次参数错误（INVALID_ARGUMENT），未能完成完整检索，因此证据不充分。

**下一步建议：**
1. 请提供该模型的准确模型名称（或控制台中的模型 ID）、调用接口地址，以及您看到“512K”说法的出处（文档链接或截图）。
2. 如方便，请提供一次实际调用的 `request_id`、HTTP 状态码/错误码及发生时间，便于核实。
3. 我已为您创建人工工单（工单号：CS_166e91644725456ba081），由专员进一步核实该模型的最大输出长度与发布日期。

来源#1: qwen-chat-completions.md
来源#2: qwen-dashscope.md
来源#3: qwen-chat-completions.md
来源#4: qwen-errors.md
来源#5: qwen-chat-completions.md
来源#6: qwen-dashscope.md
来源#7: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-chat-completions.md`，chunk=19，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
ls`。适用型号及取值见下方说明。

              <Accordion title="取值范围">
                - <strong>输入图像：</strong>

                  - `qwen3.8-max`、`qwen3.8-max-0902`、`qwen3.8-flash`、`qwen3.8-2.4t-a95b`、`qwen3.8-27b`、Qwen3.7、Qwen3.6、Qwen3.5、Qwen3-VL：默认值和最小值均为：`65536`
                  - `qwen3.8-omni-flash`、Qwen3.5-Omni ：默认值和最小值均为： `24576`
                  - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值和最小值均为`3136`
                - <strong>输入视频文件或图像列表：</strong>
~~~~

来源#2：`qwen-dashscope.md`，chunk=78，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
trong>`integer`（可选）

        模型输出的最大长度，包含思维链和模型回答。模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。

        默认值与最大值均为模型的最大输出长度。

        与 `max_tokens` 的区别：`max_completion_tokens` 限制模型完整输出（思维链 + 回答），而 `max_tokens` 仅限制回答部分。思考类模型推荐使用 `max_completion_tokens`。

        支持以下模型：

        - 千问 Max：Qwen3.7-Max 及之后的模型
        - 千问 Plus：Qwen3.5-Plus 及之后的模型
        - 千问 Flash：Qwen3.5-Flash 及之后的模型
        - Kimi：kimi-k2.5 及其之后推出的Kimi模型
        - GLM：glm-5 及其之后推出的GLM系列模型
        - MiniMax：MiniMax-M2.5 及之后推出的MiniMax模型
        - DeepSeek：deepseek-v4-pro 及之后推出的DeepSeek模型

        > 以上模型均不包含三方直供模型。
~~~~

来源#3：`qwen-chat-completions.md`，chunk=62，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
trong>`integer`（可选）

        模型输出的最大长度，包含思维链和模型回答。模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。

        默认值与最大值均为模型的最大输出长度。

        与 `max_tokens` 的区别：`max_completion_tokens` 限制模型完整输出（思维链 + 回答），而 `max_tokens` 仅限制回答部分。思考类模型推荐使用 `max_completion_tokens`。

        支持以下模型：

        - 千问 Max：Qwen3.7-Max 及之后的模型
        - 千问 Plus：Qwen3.5-Plus 及之后的模型
        - 千问 Flash：Qwen3.5-Flash 及之后的模型
        - Kimi：kimi-k2.5 及其之后推出的Kimi模型
        - GLM：glm-5 及其之后推出的GLM系列模型
        - MiniMax：MiniMax-M2.5 及之后推出的MiniMax模型
        - DeepSeek：deepseek-v4-pro 及之后推出的DeepSeek模型

        > 以上模型均不包含三方直供模型。
~~~~

来源#4：`qwen-errors.md`，chunk=7，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
eter） <span id="81221bf732m4b" />

<strong>原因：</strong> 调用模型时输入内容长度超过模型上限。

<strong>解决方案：</strong>

- 若通过代码调用，请控制 messages 数组中的 Token 数在模型最大输入Token范围内；
- 使用对话客户端（如Chatbox）或阿里云百炼控制台进行连续对话时，每次请求都会附带历史记录，容易超出模型限制。超出限制后，请开启新对话。

### Range of max\_tokens should be \[1, xxx] <span id="cc5c90b6db061" />

<strong>原因：</strong> `max_tokens` 参数设置未在 \[1, 模型最大输出 Token 数]的范围内。

<strong>解决方案：</strong> `max_tokens`上限请参考模型列表文档中的"最大输出 Token 数"。
~~~~

来源#5：`qwen-chat-completions.md`，chunk=37，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
> 流式输出时，Token 消耗信息仅可出现在响应的最后一个数据块。
        </Accordion>

        <strong>modalities</strong>`array`（可选）默认值为`["text"]`

        输出数据的模态，仅适用于 Qwen-Omni 模型。相关文档：[非实时（Qwen-Omni）](/zh/model-studio/qwen-omni)

        可选值：

        - `["text","audio"]`：输出文本与音频，适用于支持音频输出的型号；
        - `["text"]`：仅输出文本。

        `qwen3.8-omni-flash` 仅输出文本。示例见 [Qwen3.8-Omni-Flash](/zh/model-studio/qwen-omni#qwen38-offline)。

        <strong>audio</strong>`object`（可选）

        输出音频的音色与格式，适用于支持音频输出的 Qwen-Omni 模型，且`modalities`参数需为`["text","audio"]`。相关文档：[非实时（Qwen-Omni）](/zh/model-studio/qwen-omni)
~~~~

来源#6：`qwen-dashscope.md`，chunk=31，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
40`，最大值为：`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值为`1003520` ，最大值为`12845056`

                  - 当`vl_high_resolution_images`为`True`时：

                    - `Qwen3.7、Qwen3.6、Qwen3.5`、Qwen3-VL：`max_pixels`无效，输入图像的最大像素固定为`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：`max_pixels`无效，输入图像的最大像素固定为`12845056`
                - <strong>输入视频文件或图像列表：</strong>
~~~~

来源#7：`qwen-rate-limits.md`，chunk=100，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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
~~~~

## E07 · gpt · fact

OpenAI后台响应处于queued或in_progress时应怎样轮询？何时停止？要启动后台执行应设置哪个参数？

判分要求：background=true启动后台；GET/retrieve响应并在queued或in_progress继续轮询；离开这两种状态即终态，停止轮询

审阅：FAIL。background=true和轮询条件均未回答；后台文档已召回却被诊断门替换。来源#2/#3名称与映射不一致。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

当前没有匹配的已核验请求记录，不能确认本次故障原因。

下一步：补充脱敏请求号或故障发生时间，无需提供完整 Key

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: gpt-background.md
来源#2: gpt-conversation-state.md
来源#3: gpt-webhooks.md

### 实际引用锚点

来源#1：`gpt-background.md`，chunk=11，version=fc4bfe66d6345d5a99f63f24a73252ff，HTTP=200

~~~~text
nt.CreateResponseAsync(options);
Console.WriteLine(response.Status);
```

```ruby
require "openai"

client = OpenAI::Client.new
response = client.responses.create(
  model: "gpt-6-astra",
  input: "Write a detailed market analysis.",
  background: true
)

puts(response.status)
```

## Polling background responses

To check the status of background requests, use the GET endpoint for Responses. Keep polling while the request is in the queued or in_progress state. When it leaves these states, it has reached a final (terminal) state.

Retrieve a response executing in the background
~~~~

来源#2：`gpt-background.md`，chunk=23，version=fc4bfe66d6345d5a99f63f24a73252ff，HTTP=200

~~~~text
client = OpenAI::Client.new
response = client.responses.create(
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true
)

while [:queued, :in_progress].include?(response.status)
  puts("Current status: #{response.status}")
  sleep(2)
  response = client.responses.retrieve(response.id)
end

puts("Final status: #{response.status}")
puts(response.output_text)
```

## Cancelling a background response

You can also cancel an in-flight response like this:

Cancel an ongoing response
~~~~

来源#3：`gpt-background.md`，chunk=16，version=fc4bfe66d6345d5a99f63f24a73252ff，HTTP=200

~~~~text
tring("Write a very long novel about otters in space."),
		},
	})
	if err != nil {
		panic(err)
	}

	for response.Status == "queued" || response.Status == "in_progress" {
		fmt.Println("Current status:", response.Status)
		time.Sleep(2 * time.Second)
		response, err = client.Responses.Get(context.Background(), response.ID, responses.ResponseGetParams{})
		if err != nil {
			panic(err)
		}
	}

	fmt.Printf("Final status: %s\nOutput:\n%s\n", response.Status, response.OutputText())
}
```
~~~~

## E08 · gpt · fact

OpenAI的JSON mode和Structured Outputs，对required字段与枚举约束的保证相同吗？如果模型拒绝，能直接当作符合业务Schema的成功数据吗？

判分要求：JSON mode保证合法JSON，不保证JSON Schema；Structured Outputs约束Schema；拒绝需单独识别处理，不能直接当作Schema业务成功数据

审阅：PARTIAL。Schema保证差异和拒绝处理正确，全文有依据；#1/#2锚点支持JSON/Schema，但实际七个引用锚点未包含显式拒绝规则，严格引用支撑不完整。

### 原始回答

**结论：两者对 required 字段与枚举约束的保证不同；模型拒绝时不能直接当作符合业务 Schema 的成功数据。**

**1. JSON mode 与 Structured Outputs 的保证不同**

- JSON mode 是 Structured Outputs 的更基础版本：它只保证模型输出是有效 JSON（且文档说明存在需要检测和处理的边缘情况），并不保证输出匹配你指定的 Schema。
- Structured Outputs 才会可靠地让模型输出匹配你提供的 JSON Schema，因此不需要担心模型遗漏 required 键或编造无效枚举值。
- 文档建议：如果你的用例支持 Structured Outputs，应优先使用它。

**2. 模型拒绝时不能当作成功数据**

- Structured Outputs 的一个明确优势是“显式拒绝（Explicit refusals）”：基于安全原因的模型拒绝可以被程序化检测。
- 因此，当检测到拒绝时，应将其作为拒绝/异常分支处理，而不是当作符合业务 Schema 的成功数据继续消费。
- 另外，文档提到部分约束（如 minimum/maximum 等）对微调模型尚不支持；若你使用微调模型，需按文档确认约束支持范围。

**3. 建议的落地做法**

- 优先启用 Structured Outputs（`strict: true` + 明确 `required`、`enum`、`additionalProperties: false`）。
- 在客户端同时处理两类分支：① 显式拒绝；② JSON 解析/校验失败（尤其 JSON mode 的边缘情况）。
- 不要仅凭“返回了 JSON”就判定业务成功，仍应做一次 Schema 校验并区分拒绝与成功。

**需要你补充的信息**：以上为通用规则说明，未核验你账户或本次请求的实际状态。如需定位具体问题，请提供 request_id、HTTP 状态/错误码、接口地址（如 Responses/Chat Completions）及发生时间。

来源#1: gpt-structured-outputs.md
来源#2: gpt-structured-outputs.md
来源#3: gpt-structured-outputs.md
来源#4: gpt-structured-outputs.md
来源#5: gpt-function-calling.md
来源#6: gpt-prompt-engineering.md
来源#7: gpt-text.md

### 实际引用锚点

来源#1：`gpt-structured-outputs.md`，chunk=284，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
"additionalProperties": false,
    "required": [
        "linked_list"
    ]
}
```

## JSON mode

JSON mode is a more basic version of the Structured Outputs feature. While
  JSON mode ensures that model output is valid JSON, Structured Outputs reliably
  matches the model's output to the schema you specify. We recommend you use
  Structured Outputs if it is supported for your use case.

When JSON mode is turned on, the model's output is ensured to be valid JSON, except for in some edge cases that you should detect and handle appropriately.
~~~~

来源#2：`gpt-structured-outputs.md`，chunk=1，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
URL.

JSON is one of the most widely used formats in the world for applications to exchange data.

Structured Outputs is a feature that ensures the model will always generate responses that adhere to your supplied [JSON Schema](https://json-schema.org/overview/what-is-jsonschema), so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value.

Some benefits of Structured Outputs include:
~~~~

来源#3：`gpt-structured-outputs.md`，chunk=261，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
eSchema = z.object({
  /* ... */
});
const UnsuccessfulResponseSchema = z.object({
  /* ... */
});

const finalSchema = z.discriminatedUnion("status", [
  BaseResponseSchema,
  UnsuccessfulResponseSchema,
]);

// Invalid JSON Schema for Structured Outputs
const json = zodResponseFormat(finalSchema, "final_schema");
```

#### All fields must be `required`
~~~~

来源#4：`gpt-structured-outputs.md`，chunk=146，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
First you must design the JSON Schema that the model should be constrained to follow. See the [examples](https://developers.openai.com/api/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) for more details.

#### Tips for your JSON Schema

To maximize the quality of model generations, we recommend the following:
~~~~

来源#5：`gpt-function-calling.md`，chunk=106，version=7a0be2a962bb5fa88c0d0bb7f6bc3995，HTTP=200

~~~~text
elsius", "fahrenheit"],
                "description": "Units the temperature will be returned in."
            }
        },
        //highlight-start
        "required": ["location"],
        //highlight-end
    }
}
```

All schemas generated in the
  [playground](https://platform.openai.com/playground) have strict mode enabled.

While we recommend you enable strict mode, it has a few limitations:

1. Some features of JSON schema are not supported. (See [supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs?context=with_parse#supported-schemas).)
~~~~

来源#6：`gpt-prompt-engineering.md`，chunk=12，version=06a6f123d65e5c8da62ec8967759ee00，HTTP=200

~~~~text
model into a single string. This may be useful as a shortcut to access text output from the model.

In addition to plain text, you can also have the model return structured data in JSON format - this feature is called [**Structured Outputs**](https://developers.openai.com/api/docs/guides/structured-outputs).

## Choosing a model
~~~~

来源#7：`gpt-text.md`，chunk=47，version=2f96fd65e2fb5f66ab164fb97fc9c821，HTTP=200

~~~~text
Use the Playground to develop and iterate on prompts.](https://platform.openai.com/chat/edit)

[Generate JSON data with Structured Outputs

      Ensure JSON data emitted from a model conforms to a JSON schema.](https://developers.openai.com/api/docs/guides/structured-outputs)

[Full API reference

      Check out all the options for text generation in the API reference.](https://developers.openai.com/api/reference/resources/responses)
~~~~

## E09 · gpt · insufficient

仅凭OpenAI官方文档，能确认我的组织已启用Zero Data Retention，且下周所有请求均不留存吗？请判断我的组织实际状态。

判分要求：无法从通用文档确认组织开通状态或所有请求未来行为；不能把后台模式或通用保留规则等同于个人组织配置

审阅：PASS。明确不能由通用规则确认组织配置或未来全部请求，未编造个人状态；#1 chunk35直接支撑其缓存默认规则说明。

### 原始回答

**不能确认。** 仅凭 OpenAI 官方文档无法判断您组织的实际状态，也无法确认下周所有请求是否都不留存。

**原因说明：**

1. **文档只说明通用规则，不反映您组织的配置。** 检索到的文档提到：未启用 Zero Data Retention（ZDR）的组织默认缓存保留 `24h`；已启用 ZDR 的组织默认 `in_memory`。这是通用规则描述，不能证明您的组织属于哪一种，也不能证明您已启用 ZDR。

2. **“下周所有请求均不留存”属于未来状态，文档无法证明。** 文档中的保留策略说明是规则层面的，不能替代对您组织账户配置的核查，也不能对未来请求的实际留存情况作出保证。

3. **本次没有可核验的组织事实。** 已确认事实为空，没有账户配置、组织 ID 或保留策略查询结果等证据支持“已启用 ZDR”这一结论。

**建议下一步：**

- 请在 OpenAI 平台的组织设置中核实 Zero Data Retention 的实际启用状态，以及当前模型/组织可用的保留策略（文档也提示：选择前应核实您的模型和组织可用的保留策略）。
- 如需我们进一步协助排查，请提供：组织 ID、request_id、HTTP 状态/错误码、接口地址及发生时间，以便定位具体请求。

本次未创建人工工单（handoff 未成功执行，无工单号）。

来源#1: gpt-prompt-caching.md
来源#2: gpt-conversation-state.md
来源#3: gpt-overview.md

### 实际引用锚点

来源#1：`gpt-prompt-caching.md`，chunk=35，version=a338ee9707c1548d9fc03fe54bf3257f，HTTP=200

~~~~text
- Organizations _without_ Zero Data Retention enabled default to `24h`.
- Organizations _with_ Zero Data Retention enabled default to `in_memory`.

Verify the available retention policies for your model and organization before selecting a value.

<a id="where-caching-happens-and-how-long-it-lasts"></a>

<a id="cache-location-and-duration"></a>

<a id="cache-location-and-lifetime"></a>

## Cache location
~~~~

来源#2：`gpt-conversation-state.md`，chunk=0，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
# GPT / OpenAI API：多轮会话状态

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Conversation state

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI provides a few ways to manage conversation state, which is important for preserving information across multiple messages or turns in a conversation.
~~~~

来源#3：`gpt-overview.md`，chunk=0，version=9feabad921a156d9a4741c5a7765bf77，HTTP=200

~~~~text
# GPT / OpenAI API：接入认证与请求追踪

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# API Overview

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.
~~~~

## E10 · ambiguous · clarification

我想做JSON结构化输出，怎样设置参数才能保证符合Schema？

判分要求：先询问厂商/模型或明确按厂商区分；不能给所有厂商通用的schema保证或混合参数

审阅：FAIL。未先确认厂商/模型，也未明确首段适用Qwen，将其response_format和max_tokens规则表述为通用方案；后补DeepSeek Responses参数不能消除范围歧义。

### 原始回答

要让输出严格符合 Schema，应使用 **JSON Schema 模式**，而不是 JSON Object 模式。两者的区别如下：

**1. 选择 JSON Schema 模式**

在请求体中把 `response_format` 设置为：

```json
{"type": "json_schema", "json_schema": {..., "strict": true}}
```

该模式确保输出内容为指定的结构；JSON Object 模式只保证输出是标准 JSON 字符串，**不保证符合特定结构**。使用 JSON Schema 模式时，提示词无需包含 JSON 关键词。

**2. 生产环境注意事项**

- **有效性校验**：若使用 JSON Object 模式，建议在下游使用 jsonschema（Python）、Ajv（JavaScript）、Everit（Java）等工具校验输出是否符合指定 Schema；失败时可通过重试或大模型改写修复。
- **不要设置 `max_tokens`**：开启结构化输出时设置该参数可能导致 JSON 字符串被截断，产生无效 JSON，导致下游解析失败。
- **用 SDK 辅助生成 Schema**：推荐用 SDK 自动生成 Schema（如 Python 中直接传入 Pydantic 模型），避免手动维护出错，并可自动验证和解析。

**3. 其他厂商的对应参数（供参考）**

DeepSeek Responses API 中，`text.format` 支持 `{"type": "json_schema", "name": ..., "schema": ...}`，此时 `name` 和 `schema` 为必填项，输出符合给定的 JSON Schema。

以上为文档中的通用规则说明。如果你在具体调用中遇到报错或输出不符合预期，请提供 request_id、HTTP 状态码/错误码、接口地址及发生时间，以便进一步排查。

来源#1: qwen-structured-outputs.md
来源#2: qwen-structured-outputs.md
来源#3: deepseek-responses.md

### 实际引用锚点

来源#1：`qwen-structured-outputs.md`，chunk=1，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
Object 与 JSON Schema两种模式：

- <strong>JSON Object 模式</strong>：确保输出为标准格式的 JSON 字符串，但不保证符合特定结构。使用方式：

  1. <strong>设置</strong>`response_format`<strong>参数</strong>：在请求体中，将 `response_format` 参数设置为 `{"type": "json_object"}`。
  2. <strong>提示词包含 JSON 关键词</strong>：System Message 或 User Message 中需要包含 "JSON" 关键词（不区分大小写），否则会报错：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`
~~~~

来源#2：`qwen-structured-outputs.md`，chunk=183，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
规范导致下游系统解析失败、数据丢失或业务逻辑中断。失败时可通过重试、大模型改写等策略进行修复。
- <strong>禁用</strong> <strong>max\_tokens</strong>

  开启结构化输出时，请勿设置 `max_tokens`。该参数限制模型输出的 Token 数（默认值为模型最大输出 Token 数），设置后可能导致JSON字符串在输出过程中被截断，产生无效 JSON，下游解析将失败。
- <strong>使用 SDK 辅助生成 Schema</strong>

  推荐使用 SDK 自动生成 Schema，避免手动维护导致的错误，并可以自动验证和解析。

  <CodeGroup dropdown>
    ```python Python expandable
    from pydantic import BaseModel, Field
    from typing import Optional
    from openai import OpenAI
    import os
~~~~

来源#3：`deepseek-responses.md`，chunk=12，version=47a4c8df60e15d7982216687963fc076，HTTP=200

~~~~text
输出格式。`{"type": "text"}`（默认）为纯文本输出；`{"type": "json_object"}` 为 JSON 模式；`{"type": "json_schema", "name": ..., "schema": ...}` 为结构化输出，输出符合给定的 JSON Schema。

type string

Possible values: [`text`, `json_object`, `json_schema`]

Default value: `text`

name string

schema 的名称。`type` 为 `json_schema` 时必填。

schema object

输出必须符合的 JSON Schema。`type` 为 `json_schema` 时必填。

tools

object[]

nullable
~~~~

## E11 · comparison · comparison

比较DeepSeek的JSON Output和OpenAI的Structured Outputs：前者是否自动约束JSON Schema？后者的Schema保证是什么？请分别标注依据。

判分要求：DeepSeek JSON Output保证合法JSON，不自动承诺Schema约束；OpenAI Structured Outputs支持JSON Schema约束；两家事实分别引用对应官方资料

审阅：PARTIAL。OpenAI部分正确并有锚点；DeepSeek部分未完成，还称结构化证据没有正文，而#6可访问锚点含JSON Output说明。暴露证据传递/消费缺口，不算完成比较。

### 原始回答

关于您提出的对比问题，我需要先说明证据情况：本次检索到的可引用文档中，**只有 OpenAI Structured Outputs 的相关内容**；DeepSeek JSON Output 的两条引用（deepseek-tool-calling.md、deepseek-json-output.md）在本次答复所依据的结构化证据中**没有提供正文内容**，因此我无法就“DeepSeek 的 JSON Output 是否自动约束 JSON Schema”给出有依据的结论，也不能推测。

**OpenAI Structured Outputs 的 Schema 保证（有文档依据）：**
- 使用方式：在 API 调用中指定 `text: { format: { type: "json_schema", "strict": true, "schema": … } }`，即由客户提供 JSON Schema 并开启 strict。
- 保证程度：文档明确区分了 JSON mode 与 Structured Outputs——JSON mode 只保证输出是合法 JSON（且存在需自行检测处理的边缘情况），而 **Structured Outputs 会可靠地使模型输出匹配客户指定的 schema**（"Structured Outputs reliably matches the model's output to the schema you specify"）。
- 支持范围：Structured Outputs 支持 JSON Schema 的一个子集，部分特性因性能或技术原因不可用；支持的类型包括 String、Number、Boolean、Integer、Object、Array、Enum、anyOf。

**DeepSeek JSON Output 部分：** 证据不足，无法确认其是否自动约束 JSON Schema。建议您提供 DeepSeek 侧的具体接口地址、请求参数（如是否传入 response_format/schema）、request_id 及发生时间，以便进一步核实。

另外，本次已为您创建人工工单跟进（工单号：CS_7abdbd3419c74b60be84），可由专员补充 DeepSeek 侧的对比说明。

来源#1: gpt-structured-outputs.md
来源#2: gpt-structured-outputs.md
来源#3: gpt-structured-outputs.md
来源#4: gpt-structured-outputs.md
来源#5: deepseek-tool-calling.md
来源#6: deepseek-json-output.md

### 实际引用锚点

来源#1：`gpt-structured-outputs.md`，chunk=146，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
First you must design the JSON Schema that the model should be constrained to follow. See the [examples](https://developers.openai.com/api/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) for more details.

#### Tips for your JSON Schema

To maximize the quality of model generations, we recommend the following:
~~~~

来源#2：`gpt-structured-outputs.md`，chunk=284，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
"additionalProperties": false,
    "required": [
        "linked_list"
    ]
}
```

## JSON mode

JSON mode is a more basic version of the Structured Outputs feature. While
  JSON mode ensures that model output is valid JSON, Structured Outputs reliably
  matches the model's output to the schema you specify. We recommend you use
  Structured Outputs if it is supported for your use case.

When JSON mode is turned on, the model's output is ensured to be valid JSON, except for in some edge cases that you should detect and handle appropriately.
~~~~

来源#3：`gpt-structured-outputs.md`，chunk=252，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
json_schema,
      name: "entities",
      strict: true,
      schema: entities_schema
    }
  }
)

stream.each do |event|
  case event
  when OpenAI::Models::Responses::ResponseRefusalDeltaEvent,
       OpenAI::Models::Responses::ResponseTextDeltaEvent
    print(event.delta)
  when OpenAI::Models::Responses::ResponseErrorEvent
    warn(event.message)
  when OpenAI::Models::Responses::ResponseCompletedEvent
    puts("\nCompleted")
  end
end
```

## Supported schemas

Structured Outputs supports a subset of the [JSON Schema](https://json-schema.org/docs) language.

#### Supported types
~~~~

来源#4：`gpt-structured-outputs.md`，chunk=28，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
.com/api/docs/guides/function-calling#strict-mode)
    guide.

### Structured Outputs vs JSON mode

Structured Outputs is the evolution of [JSON mode](#json-mode). While both ensure valid JSON is produced, only Structured Outputs ensure schema adherence. Both Structured Outputs and JSON mode are supported in the Responses API, Chat Completions API, Assistants API, Fine-tuning API and Batch API.

We recommend always using Structured Outputs instead of JSON mode when possible.
~~~~

来源#5：`deepseek-tool-calling.md`，chunk=6，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
JSON Schema 的格式要求，以确保模型输出的 Function 符合用户的定义。在思考与非思考模式下的工具调用，均可使用 `strict` 模式。

要使用 `strict` 模式，需要：

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能

- 在传入的 `tools` 列表中，所有 `function` 均需设置 `strict` 属性为 `true`

- 服务端会对用户传入的 Function 的 JSON Schema 进行校验，如不符合规范，或遇到服务端不支持的 JSON Schema 类型，将返回错误信息

以下是 `strict` 模式下 tool 的定义样例：
~~~~

来源#6：`deepseek-json-output.md`，chunk=0，version=8ca3370a65d15df5b4e04f783542de05，HTTP=200

~~~~text
# DeepSeek API：JSON 输出

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[JSON Output](https://api-docs.deepseek.com/zh-cn/guides/json_mode/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# JSON Output

在很多场景下，用户需要让模型严格按照 JSON 格式来输出，以实现输出的结构化，便于后续逻辑进行解析。

DeepSeek 提供了 JSON Output 功能，来确保模型输出合法的 JSON 字符串。

## 注意事项

- 设置 `response_format` 参数为 `{'type': 'json_object'}`。

- 用户传入的 system 或 user prompt 中必须含有 `json` 字样，并给出希望模型输出的 JSON 格式的样例，以指导模型来输出合法 JSON。

- 需要合理设置 `max_tokens` 参数，防止 JSON 字符串被中途截断。
~~~~

## E12 · qwen · insufficient

请按Qwen 2099-01-01版官方规范确认text-embedding-v4当时支持的全部维度；当前2026快照是否足以给出该版本结论？

判分要求：不能用2026快照确认2099版本；允许明确标作当前快照规则，不得冒充未来官方规范

审阅：PASS。明确2026快照不能确认2099规范；把64~2048和1024示例标为当前快照，#1及其余参数示例可支撑。额外工单单列。

### 原始回答

关于您的问题，需要先说明两点：

**1. 无法确认“Qwen 2099-01-01版官方规范”**
现有检索到的文档是核对日期为 2026-10-19 的官方正文快照，文档中并未出现“2099-01-01版”这一版本标识，也没有任何按版本号区分的历史规范内容。因此，无法依据现有证据确认该版本下 text-embedding-v4 支持的全部维度。

**2. 当前 2026 快照不足以给出该版本结论**
该快照仅能反映其自身记载的内容，不能作为“2099-01-01版”规范的依据。快照中可确认的通用信息是：text-embedding-v4 支持 64~2048 维用户自定义向量维度，且 dimension 参数在调用示例中可指定（示例值为 1024）。但这只是该快照的记载，不能推断为其他版本或历史时点的规则。

**下一步建议**
- 如需确认特定版本规范，请提供该版本规范的官方链接或文档编号，以便核对；
- 若您实际遇到调用问题，请提供 request_id、HTTP 状态/错误码、接口地址及发生时间，我们再据此排查。

已为您创建人工工单（工单号：CS_426bfbb0b0e1403099ca），可由专员进一步协助核实版本规范问题。

来源#1: qwen-embedding-v4.md
来源#2: qwen-embedding-api.md
来源#3: qwen-embedding-api.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-api.md
来源#6: qwen-batch.md
来源#7: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-embedding-v4.md`，chunk=0，version=52339fbb07d75e06a3325c666b05528e，HTTP=200

~~~~text
# Qwen / 阿里云百炼：text-embedding-v4

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[text-embedding-v4](https://help.aliyun.com/zh/model-studio/text-embedding-v4)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# text-embedding-v4

> 通用文本向量V4版本，是通义实验室基于Qwen3训练的多语言文本统一向量模型，相较V3版本在文本检索、聚类、分类性能大幅提升；在MTEB多语言、中英、Code检索等评测任务上效果提升15%~40%；支持64~2048维用户自定义向量维度。

<meta property="og:title" content="text-embedding-v4" />

## 推理服务供应商 <span id="h-490b2834e6" />

`text-embedding-v4`模型的推理服务供应商为阿里云百炼。

## 模型能力 <span id="h-55c4216db8" />
~~~~

来源#2：`qwen-embedding-api.md`，chunk=93，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
# 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                    )

                    if resp.status_code == HTTPStatus.OK:
                        print(resp)
                    else:
                        print(resp)
                ```
              </Tab>
~~~~

来源#3：`qwen-embedding-api.md`，chunk=73，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
TextEmbeddingParam param = TextEmbeddingParam
                                  .builder()
                                  .model("qwen3.7-text-embedding")  // 使用text-embedding-v4模型
                                  .texts(Arrays.asList("衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买"))  // 输入文本
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();
~~~~

来源#4：`qwen-embedding-api.md`，chunk=85，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
.model("qwen3.7-text-embedding")
                                  .texts(batch)
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();
~~~~

来源#5：`qwen-embedding-api.md`，chunk=37，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
mbedding")
                                      .input(EmbeddingCreateParams.Input.ofString(text))
                                      // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                      .dimensions(1024)
                                      .build();
~~~~

来源#6：`qwen-batch.md`，chunk=5，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
2、text-embedding-v3、text-embedding-v4、qwen3.7-text-embedding、qwen3.7-text-embedding-flash
  </Tab>

  <Tab title="新加坡">
    <strong>支持的模型</strong>：qwen3.7-plus、qwen-max、qwen-plus。
  </Tab>
</Tabs>

<Tip>
  - 在Batch 场景下，`qwen3.8-max`、`qwen3.8-flash`、`qwen3.7-max`、`qwen3.7-plus`、`qwen3.6-plus`、`qwen3.7-flash`、`qwen3.6-flash`、`qwen3.5-plus`、`qwen3.5-flash`和`qwen3.5-omni-plus`单次请求的上下文 Token 数最大支持 256K，`qwen3.5-omni-plus`不支持语音输出。
  - 部分模型支持思考模式，开启后会产生思考`tokens`导致成本增加。
  - `qwen3.8`、`qwen3.7`、`qwen3.6`和`qwen3.5` 系列模型默认开启思考模式。建议使用混合思考模型时，显式设置`enable_thinking`参数（`true`开启/`false`关闭）。
~~~~

来源#7：`qwen-rate-limits.md`，chunk=751，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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
~~~~
