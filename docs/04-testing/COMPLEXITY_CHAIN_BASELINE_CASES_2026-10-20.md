# 独立端到端回答评测：逐题原始回答与审阅证据

2026-10-20；本轮逐题原始输出，各轮证据分开保存，不覆盖历史失败。引用令牌不公开，正文与锚点摘要保留。

## C01 · deepseek · fact

DeepSeek JSON Output接入时response_format和提示词应如何配置？

判分要求：json_object；提示含json并提供格式示例；max_tokens合理

审阅：PASS。json_object、prompt 包含 json、格式示例与截断提醒正确；代码为片段，messages 需调用方定义。

### 原始回答

针对 DeepSeek API 的 JSON Output 接入，配置要点如下（以下为 DeepSeek 厂商通用规则，不代表您账户的实际状态）：

## 1. response_format 配置

将 `response_format` 参数设置为：

```json
{"type": "json_object"}
```

该参数用于启用 JSON 模式，模型会保证生成的消息是有效 JSON。`type` 的可选值为 `text`（默认）或 `json_object`。来源#1、来源#5

## 2. 提示词（prompt）配置

- **必须包含 `json` 字样**：传入的 system 或 user prompt 中必须含有 "json" 字样，否则模型可能持续生成空白字符直到达到 token 限制，导致请求长时间运行、看起来"卡住"。来源#1、来源#5
- **给出 JSON 格式样例**：在提示词中提供希望模型输出的 JSON 结构示例，以指导模型生成合法 JSON。来源#1

官方样例中的 system prompt 写法（节选）：

```
The user will provide some exam text. Please parse the "question" and "answer"
and output them in JSON format.

EXAMPLE INPUT: Which is the highest mountain in the world? Mount Everest.

EXAMPLE JSON OUTPUT:
{
    "question": "Which is the highest mountain in the world?",
    "answer": "Mount Everest"
}
```


## 3. 其他注意事项

- **合理设置 `max_tokens`**：防止 JSON 字符串被中途截断。若 `finish_reason="length"`，说明生成超过 `max_tokens` 或对话超过最大上下文长度，消息内容可能被部分截断。来源#1、来源#5
- **空 content 概率**：使用 JSON Output 时 API 有概率返回空的 content，官方正在优化，可尝试修改 prompt 缓解。来源#1
- **模型支持**：`deepseek-flash` 与 `deepseek-v4-pro` 均支持 JSON Output。来源#2

以上为文档层面的通用配置规则；如需核查某次具体调用是否异常，请提供 request_id、HTTP 状态/错误码、接口地址或发生时间。

来源#1: deepseek-json-output.md
来源#2: deepseek-models-pricing.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-rate-limits.md
来源#5: deepseek-chat-completions.md
来源#6: deepseek-anthropic-protocol.md
来源#7: deepseek-quickstart.md

### 实际引用锚点

来源#1：`deepseek-json-output.md`，chunk=0，version=8ca3370a65d15df5b4e04f783542de05，HTTP=200

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

[同版本引用上下文]
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

- 在使用 JSON Output 功能时，API 有概率会返回空的 content。我们正在积极优化该问题，您可以尝试修改 prompt 以缓解此类问题。

## 样例代码

这里展示了使用 JSON Output 功能的完整 Python 代码：

```
import jsonfrom openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com",)system_prompt = """The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. EXAMPLE INPUT: Which is the highest mountain in the world? Mount Everest.EXAMPLE JSON OUTPUT:{    "question": "Which is the highest mountain in the world?",    "answer": "Mount Everest"}"""user_prompt = "Which is the longest river in the world? The Nile River."messages = [{"role": "system", "content": system_prompt},            {"role": "user", "content": user_prompt}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    response_format={        'type': 'json_object',    },)print(json.loads(response.choices[0].message.content))
```

模型将会输出：

```
{    "question": "Which is the longest river in the world?",    "answer": "The Nile River"}
```
~~~~

来源#2：`deepseek-models-pricing.md`，chunk=1，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

~~~~text
百万 tokens”为单位。Token 是模型用来表示自然语言文本的的最小单位，可以是一个词、一个数字或一个标点符号等。我们将根据模型输入和输出的总 token 数进行计量计费。

## 模型细节

| 模型 | deepseek-flash (1) | deepseek-v4-pro |  |  |
| --- | --- | --- | --- | --- |
| BASE URL (OpenAI 格式) | https://api.deepseek.com |  |  |  |
| BASE URL (Anthropic 格式) | https://api.deepseek.com/anthropic |  |  |  |
| 模型版本 | DeepSeek-V4.1-Flash-1017 | DeepSeek-V4-Pro-0813 |  |  |
| 思考模式 | 支持非思考与思考模式（默认） 切换方式详见 思考模式 |  |  |  |
| 上下文长度 | 1M |  |  |  |
| 输出长度 | 最大 384K |  |  |  |
| 功能 | Json Output | 支持 | 支持 |  |
| Tool Calls | 支持 | 支持 |  |  |
| Responses API | 支持 | 支持 |  |  |

[同版本引用上下文]
# DeepSeek API：模型与价格

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[模型 & 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 模型 & 价格

下表所列模型价格以“百万 tokens”为单位。Token 是模型用来表示自然语言文本的的最小单位，可以是一个词、一个数字或一个标点符号等。我们将根据模型输入和输出的总 token 数进行计量计费。

## 模型细节

| 模型 | deepseek-flash (1) | deepseek-v4-pro |  |  |
| --- | --- | --- | --- | --- |
| BASE URL (OpenAI 格式) | https://api.deepseek.com |  |  |  |
| BASE URL (Anthropic 格式) | https://api.deepseek.com/anthropic |  |  |  |
| 模型版本 | DeepSeek-V4.1-Flash-1017 | DeepSeek-V4-Pro-0813 |  |  |
| 思考模式 | 支持非思考与思考模式（默认） 切换方式详见 思考模式 |  |  |  |
| 上下文长度 | 1M |  |  |  |
| 输出长度 | 最大 384K |  |  |  |
| 功能 | Json Output | 支持 | 支持 |  |
| Tool Calls | 支持 | 支持 |  |  |
| Responses API | 支持 | 支持 |  |  |
| Anthropic API | 支持 | 支持 |  |  |
| 对话前缀续写（Beta） | 支持 | 支持 |  |  |
| FIM 补全（Beta） | 仅非思考模式支持 | 仅非思考模式支持 |  |  |
| 图像理解 | 支持 | 不支持 |  |  |
| 价格 (2) | 百万tokens输入 （缓存命中） | 空闲时段 | 0.02元 | 0.15元 |
| 高峰时段 | 0.04元 | 0.30元 |  |  |
| 百万tokens输入 （缓存未命中） | 空闲时段 | 1元 | 4.5元 |  |
| 高峰时段 | 2元 | 9.0元 |  |  |
| 百万tokens输出 | 空闲时段 | 4元 | 13.5元 |  |
| 高峰时段 | 8元 | 27.0元 |  |  |
| 并发限制 (3) | 2500 | 500 |  |  |

(1) 模型名请使用 `deepseek-flash`。旧模型名 `deepseek-v4-flash`、`deepseek-v4-flash-vision-exp` 仍可调用，但对应模型已下线，请求将由 DeepSeek-V4.1-Flash-1017 模型提供服务，并按 Flash 价格计费。

(2) 空闲时段价格为高峰时段价格的一半。北京时间周一至周五（不含中国法定节假日）9:00 - 12:00、14:00 - 18:00 为高峰时段；其余时段，包括周末及中国法定节假日全天均为空闲时段。

(3) 更多并发限制细节，请参考[限速与隔离](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit)。

## 网页搜索与抓取价格

Search 和 Fetch 是独立的 API，按请求次数计费。

| API | 计费单位 | 价格 |
| --- | --- | --- |
| Search | 每 1,000 次成功请求 | 5元 |
| Fetch | 每 1,000 次成功请求 | 5元 |
~~~~

来源#3：`deepseek-fim-api.md`，chunk=0，version=915e523f4c295d7081edf327bf11171e，HTTP=200

~~~~text
# DeepSeek API：补全接口参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全 API（Beta）](https://api-docs.deepseek.com/zh-cn/api/create-completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全 API（Beta）

```
POST /completions
```

FIM (Fill In the Middle) 补全 API。
用户需要设置 `base_url="https://api.deepseek.com/beta"` 来使用此功能。

## Request

- application/json

### Body

required

model stringrequired

Possible values: [`deepseek-flash`, `deepseek-v4-pro`]

模型的 ID。请使用 `deepseek-flash` 或 `deepseek-v4-pro`。

prompt stringrequired

用于生成完成内容的提示

[同版本引用上下文]
# DeepSeek API：补全接口参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全 API（Beta）](https://api-docs.deepseek.com/zh-cn/api/create-completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全 API（Beta）

```
POST /completions
```

FIM (Fill In the Middle) 补全 API。
用户需要设置 `base_url="https://api.deepseek.com/beta"` 来使用此功能。

## Request

- application/json

### Body

required

model stringrequired

Possible values: [`deepseek-flash`, `deepseek-v4-pro`]

模型的 ID。请使用 `deepseek-flash` 或 `deepseek-v4-pro`。

prompt stringrequired

用于生成完成内容的提示

echo booleannullable

在输出中，把 prompt 的内容也输出出来。不能与 `suffix` 或 `logprobs` 一起使用。

logprobs integernullable

Possible values: `<= 20`

制定输出中包含 logprobs 最可能输出 token 的对数概率，包含采样的 token。例如，如果 logprobs 是 20，API 将返回一个包含 20 个最可能的 token 的列表。API 将始终返回采样 token 的对数概率，因此响应中可能会有最多 logprobs+1 个元素。

logprobs 的最大值是 20。

max_tokens integernullable

最大生成 token 数量。

stop string | string[]

nullable

一个 string 或最多包含 16 个 string 的 list，在遇到这些词时，API 将停止生成更多的 token。

oneOf

- MOD1

- MOD2

string

-

Array [

string

-

]

stream booleannullable

如果设置为 True，将会以 SSE（server-sent events）的形式以流式发送消息增量。消息流以 `data: [DONE]` 结尾。

stream_options

object

nullable

流式输出相关选项。必须与 `stream: true` 一起使用；如果 `stream` 未设置为 `true`，API 会返回 `400` 错误。

include_usage boolean

如果设置为 `true`，流式返回的所有块都会包含 `usage` 字段，其中除最后一个块外，该字段的值均为 `null`。如果不设置或设置为 `false`，则除最后一个块外，其余块都不含 `usage` 字段。

无论是否设置，`data: [DONE]` 之前的最后一个块都会在其 `usage` 字段中给出整个请求的 token 使用统计信息。请注意，这里不会单独下发一个只含 usage 的块：统计信息附加在最后一个内容块上，该块的 `choices` 数组始终只包含一个元素，其中不含新增内容且 `finish_reason` 非 null。

suffix stringnullable

制定被补全内容的后缀。

temperature numbernullable

Possible values: `<= 2`

Default value: `1`
~~~~

来源#4：`deepseek-rate-limits.md`，chunk=4，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
```
{    "model": "deepseek-flash",    "messages": [{"role": "user", "content": "Hello!"}],    "metadata": {"user_id": "your_user_id"},    "max_tokens": 1024}
```

如果您使用的是 Anthropic SDK，调用方式如下：

```
message = client.messages.create(    model="deepseek-flash",    messages=[{"role": "user", "type": "text", "content": "Hello!"}],    metadata={"user_id": "your_user_id"},    max_tokens=1024,)
```

## 请求保活机制

您的请求发出后，有时需要等待一段时间才能获取服务器的响应。在这段时间里，您的 HTTP 请求会保持连接，并持续收到如下格式的返回内容：

- 非流式请求：持续返回空行

- 流式请求：持续返回 SSE keep-alive 注释（`: keep-alive`）

这些内容不影响对响应的 JSON body 的解析。如果您在自己解析 HTTP 响应，请注意处理这些空行或注释。

[同版本引用上下文]
```
{    "model": "deepseek-flash",    "messages": [{"role": "user", "content": "Hello!"}],    "metadata": {"user_id": "your_user_id"},    "max_tokens": 1024}
```

如果您使用的是 Anthropic SDK，调用方式如下：

```
message = client.messages.create(    model="deepseek-flash",    messages=[{"role": "user", "type": "text", "content": "Hello!"}],    metadata={"user_id": "your_user_id"},    max_tokens=1024,)
```

## 请求保活机制

您的请求发出后，有时需要等待一段时间才能获取服务器的响应。在这段时间里，您的 HTTP 请求会保持连接，并持续收到如下格式的返回内容：

- 非流式请求：持续返回空行

- 流式请求：持续返回 SSE keep-alive 注释（`: keep-alive`）

这些内容不影响对响应的 JSON body 的解析。如果您在自己解析 HTTP 响应，请注意处理这些空行或注释。

如果 10 分钟后，请求仍未开始推理，服务器将关闭连接。
~~~~

来源#5：`deepseek-chat-completions.md`，chunk=9，version=acb1ddea03df5b2cb00d72d0f989cf84，HTTP=200

~~~~text
默认强度为 `high`。出于兼容考虑，`minimal` 映射为 `low`，`medium` / `xhigh` 映射为 `high`。

max_tokens integernullable

限制一次请求中模型生成 completion 的最大 token 数。取值范围为 1 到 384K（393216）。未设置时，非思考模式默认 8K，思考模式默认 64K（`reasoning_effort` 为 `max` 时为 128K）。输入 token 和输出 token 的总长度受模型的上下文长度的限制。详见[模型 & 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)。

response_format

object

nullable

一个 object，指定模型必须输出的格式。

设置为 { "type": "json_object" } 以启用 JSON 模式，该模式保证模型生成的消息是有效的 JSON。

[同版本引用上下文]
tool_call_id stringrequired

此消息所响应的 tool call 的 ID。

-

]

model stringrequired

Possible values: [`deepseek-flash`, `deepseek-v4-pro`]

使用的模型的 ID。请使用 `deepseek-flash` 或 `deepseek-v4-pro`。

thinking

object

nullable

控制思考模式与非思考模式的转换

type string

Possible values: [`enabled`, `disabled`]

Default value: `enabled`

如果设为 `enabled`，则使用思考模式。如果设为 `disabled`，则使用非思考模式

reasoning_effort string

Possible values: [`none`, `low`, `high`, `max`]

控制思考模式开关与思考强度。`none` 关闭思考模式；`low` / `high` / `max` 开启思考模式。默认强度为 `high`。出于兼容考虑，`minimal` 映射为 `low`，`medium` / `xhigh` 映射为 `high`。

max_tokens integernullable

限制一次请求中模型生成 completion 的最大 token 数。取值范围为 1 到 384K（393216）。未设置时，非思考模式默认 8K，思考模式默认 64K（`reasoning_effort` 为 `max` 时为 128K）。输入 token 和输出 token 的总长度受模型的上下文长度的限制。详见[模型 & 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)。

response_format

object

nullable

一个 object，指定模型必须输出的格式。

设置为 { "type": "json_object" } 以启用 JSON 模式，该模式保证模型生成的消息是有效的 JSON。

注意: 使用 JSON 模式时，你还必须通过系统或用户消息指示模型生成 JSON。否则，模型可能会生成不断的空白字符，直到生成达到 token 限制，从而导致请求长时间运行并显得“卡住”。此外，如果 finish_reason="length"，这表示生成超过了 max_tokens 或对话超过了最大上下文长度，消息内容可能会被部分截断。

type string

Possible values: [`text`, `json_object`]

Default value: `text`

Must be one of `text` or `json_object`.

stop string | string[]

nullable

一个 string 或最多包含 16 个 string 的 list，在遇到这些词时，API 将停止生成更多的 token。

oneOf

- Single stop sequence

- Stop sequence list

string

-

Array [

string

-

]

stream booleannullable

如果设置为 True，将会以 SSE（server-sent events）的形式以流式发送消息增量。消息流以 `data: [DONE]` 结尾。

stream_options

object

nullable

流式输出相关选项。必须与 `stream: true` 一起使用；如果 `stream` 未设置为 `true`，API 会返回 `400` 错误。

include_usage boolean

如果设置为 `true`，流式返回的所有块都会包含 `usage` 字段，其中除最后一个块外，该字段的值均为 `null`。如果不设置或设置为 `false`，则除最后一个块外，其余块都不含 `usage` 字段。
~~~~

来源#6：`deepseek-anthropic-protocol.md`，chunk=0，version=12aa812fcd145127be54a33418c8237e，HTTP=200

~~~~text
# DeepSeek API：Anthropic 兼容协议

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[使用 Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 使用 Anthropic API

为了满足大家对 Anthropic API 生态的使用需求，我们的 API 新增了对 Anthropic API 格式的支持，其 `base_url` 为 `https://api.deepseek.com/anthropic`。

通过简单的配置，即可将 DeepSeek 的能力，接入到 Anthropic API 生态中。

## 将 DeepSeek 模型接入 Claude Code

请参考[接入 Claude Code](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code)

## 通过 Anthropic API 调用 DeepSeek 模型

[同版本引用上下文]
# DeepSeek API：Anthropic 兼容协议

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[使用 Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 使用 Anthropic API

为了满足大家对 Anthropic API 生态的使用需求，我们的 API 新增了对 Anthropic API 格式的支持，其 `base_url` 为 `https://api.deepseek.com/anthropic`。

通过简单的配置，即可将 DeepSeek 的能力，接入到 Anthropic API 生态中。

## 将 DeepSeek 模型接入 Claude Code

请参考[接入 Claude Code](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code)

## 通过 Anthropic API 调用 DeepSeek 模型

- 安装 Anthropic SDK

```
pip install anthropic
```

- 配置环境变量

```
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropicexport ANTHROPIC_API_KEY=${YOUR_API_KEY}
```

- 调用 API

```
import anthropicclient = anthropic.Anthropic()message = client.messages.create(    model="deepseek-flash",    max_tokens=1000,    system="You are a helpful assistant.",    messages=[        {            "role": "user",            "content": [                {                    "type": "text",                    "text": "Hi, how are you?"                }            ]        }    ])print(message.content)
```

注意：以 `claude` 开头的不支持的模型名仍会被接受：`claude-opus*` 会映射到 `deepseek-v4-pro`，其它 `claude*` 模型名会映射到 `deepseek-flash`。不以 `claude` 开头的未知模型名会返回 `400` 错误。

## Anthropic 模型映射

您在使用 Anthropic API 时，我们会对您传入的 claude 模型名进行映射：

- claude-opus 开头的模型，会映射到 `deepseek-v4-pro`

- claude-haiku、claude-sonnet 开头的模型，会映射到 `deepseek-flash`

claude-opus 映射到的 `deepseek-v4-pro` 按 V4 Pro 价格计费。

通过这样的映射，您在使用新版 Claude Desktop APP 的 developer 模式时，可以绕过 APP 对模型名的限制，只需改动 base_url 和 api_key，即可在其中接入 DeepSeek 模型。

## Anthropic API 兼容性细节
~~~~

来源#7：`deepseek-quickstart.md`，chunk=2，version=62d53d8cc8cd54c0ae8b8af34e7acf41，HTTP=200

~~~~text
AI Agent 与编程助手工具。如果你使用 Claude Code、GitHub Copilot、OpenCode 等工具，可以直接将 DeepSeek 作为后端模型，无需编写代码即可开始使用。

详见 [Agent 工具接入指南](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code)。

## 调用对话 API

在创建 API key 之后，你可以使用以下样例脚本，通过 OpenAI API 格式来访问 DeepSeek 模型。样例为非流式输出，您可以将 stream 设置为 true 来使用流式输出。

Anthropic API 格式的访问样例，请参考[Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)。

- curl

- python

- nodejs

[同版本引用上下文]
# DeepSeek API：首次调用

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[首次调用 API](https://api-docs.deepseek.com/zh-cn/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 首次调用 API

DeepSeek API 使用与 OpenAI/Anthropic 兼容的 API 格式，通过修改配置，您可以使用 OpenAI/Anthropic SDK 来访问 DeepSeek API，或使用与 OpenAI/Anthropic API 兼容的软件。

| PARAM | VALUE |
| --- | --- |
| base_url (OpenAI) | https://api.deepseek.com |
| base_url (Anthropic) | https://api.deepseek.com/anthropic |
| api_key | 申请一个 API key |
| model | deepseek-flash (1) deepseek-v4-pro |

(1) 模型名请使用 `deepseek-flash`。该模型现已升级为 DeepSeek-V4.1-Flash-1017，调用方式保持不变。旧模型名 `deepseek-v4-flash`、`deepseek-v4-flash-vision-exp` 仍可调用，但对应模型已下线，请求由 DeepSeek-V4.1-Flash-1017 模型提供服务，并按 Flash 价格计费。

## 接入 Agent 工具

DeepSeek Harness 开发者预览版面向全球 Harness 开发者开放测试。详见 [DeepSeek Harness 入门](https://deepseek-harness.github.io/deepseek-harness/guide/quickstart)。

DeepSeek API 已接入多种主流 AI Agent 与编程助手工具。如果你使用 Claude Code、GitHub Copilot、OpenCode 等工具，可以直接将 DeepSeek 作为后端模型，无需编写代码即可开始使用。

详见 [Agent 工具接入指南](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code)。

## 调用对话 API

在创建 API key 之后，你可以使用以下样例脚本，通过 OpenAI API 格式来访问 DeepSeek 模型。样例为非流式输出，您可以将 stream 设置为 true 来使用流式输出。

Anthropic API 格式的访问样例，请参考[Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)。

- curl

- python

- nodejs
~~~~

## C02 · qwen · fact

Qwen北京地域的API Key应配哪里的Base URL，还要匹配什么计费方案？

判分要求：同地域Key与Base URL配套；同一计费方案，不能跨地域混用

审阅：PASS。北京兼容地址、同地域及同计费方案匹配正确；未冒充查询个人账户。

### 原始回答

**Qwen 北京地域（华北2）的 Base URL 与计费方案匹配**

**1. Base URL（OpenAI 兼容接口）**

北京地域应使用：
`https://dashscope.aliyuncs.com/compatible-mode/v1`

如果使用 Anthropic 兼容接口，北京地域对应：
`https://dashscope.aliyuncs.com/apps/anthropic`

**2. 需要匹配的计费方案**

Base URL 必须与**同一计费方案**的 API Key 配套使用，否则会报 401。也就是说，按量付费的 API Key 要配按量付费的 Base URL，不能与套餐专属（如 Coding Plan / Token Plan 团队版）的 Key 或地址混用。此外，各地域的 API Key 相互独立、不能跨地域使用，北京地域的 Key 只能配北京地域的地址。

**3. 补充说明**

- 上述 `dashscope.aliyuncs.com` 属于 Dashscope 共享域名，当前可继续使用，官方建议生产环境迁移至业务空间专属域名（`[workspace-id].[region].maas.aliyuncs.com`）。
- 若使用 Coding Plan 或 Token Plan 团队版等套餐，其专属 API Key 以 `sk-sp-` 开头，必须配合各自的专属 Base URL（如 Coding Plan 为 `https://coding.dashscope.aliyuncs.com/v1`），不可与通用 Key/Base URL 混用。
- 切换地域时，API Key 也需要对应更换。

以上为文档中的通用配置规则，不代表您个人账户的实际状态。

来源#1: qwen-base-url.md
来源#2: qwen-api-key.md
来源#3: qwen-errors.md
来源#4: qwen-api-key.md
来源#5: qwen-batch.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

### 实际引用锚点

来源#1：`qwen-base-url.md`，chunk=0，version=72cb3bb8918b53828c09820e34321827，HTTP=200

~~~~text
# Qwen / 阿里云百炼：接入地址

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[Base URL总览](https://help.aliyun.com/zh/model-studio/base-url)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Base URL总览

> Base URL 是模型 API 的调用地址。Base URL必须与同一计费方案的 API Key 配套使用，否则会报错 401。各地域的 API Key 相互独立、不能跨地域使用。

<meta property="og:title" content="Base URL总览" />

## 按量付费 <span id="187a3e1ee50yt" />

根据使用场景选择合适的域名：

[同版本引用上下文]
# Qwen / 阿里云百炼：接入地址

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[Base URL总览](https://help.aliyun.com/zh/model-studio/base-url)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Base URL总览

> Base URL 是模型 API 的调用地址。Base URL必须与同一计费方案的 API Key 配套使用，否则会报错 401。各地域的 API Key 相互独立、不能跨地域使用。

<meta property="og:title" content="Base URL总览" />

## 按量付费 <span id="187a3e1ee50yt" />

根据使用场景选择合适的域名：

- Dashscope 域名（`dashscope.aliyuncs.com` 等）：原有中心化共享域名，当前可继续使用，建议迁移至业务空间专属域名。
- 业务空间专属域名（`[workspace-id].[region].maas.aliyuncs.com`）：推荐用于生产环境，提供更高吞吐、更低时延与业务空间级流量隔离。
- 试用域名（`trial.[region].maas.aliyuncs.com`）：适用于临时测试与快速验证，限流值较小。

### Dashscope 域名 <span id="0af2c6a67bsob" />

支持跨业务空间的 [API Key](https://bailian.console.aliyun.com/cn-beijing/settings/api-key) 调用。

<table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /></colgroup><thead><tr><th><p><strong>地域</strong></p></th><th><p><strong>OpenAI 兼容</strong></p></th><th><p><strong>Anthropic 兼容</strong></p></th></tr></thead><tbody><tr><td><p>华北2（北京）</p></td><td><p><code>[https://dashscope.aliyuncs.com/compatible-mode/v1](https://dashscope.aliyuncs.com/compatible-mode/v1)</code></p></td><td><p><code>[https://dashscope.aliyuncs.com/apps/anthropic](https://dashscope.aliyuncs.com/apps/anthropic)</code></p></td></tr><tr><td><p>新加坡</p></td><td><p><code>[https://dashscope-intl.aliyuncs.com/compatible-mode/v1](https://dashscope-intl.aliyuncs.com/compatible-mode/v1)</code></p></td><td><p><code>[https://dashscope-intl.aliyuncs.com/apps/anthropic](https://dashscope-intl.aliyuncs.com/apps/anthropic)</code></p></td></tr><tr><td><p>美国（弗吉尼亚）</p></td><td><p><code>[https://dashscop
~~~~

来源#2：`qwen-api-key.md`，chunk=0，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
# Qwen / 阿里云百炼：获取 API Key

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[获取与配置 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 获取与配置 API Key

> 在控制台获取或创建 API Key 后，您将使用它来安全地调用百炼的模型服务。

<meta property="og:title" content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

[同版本引用上下文]
# Qwen / 阿里云百炼：获取 API Key

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[获取与配置 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 获取与配置 API Key

> 在控制台获取或创建 API Key 后，您将使用它来安全地调用百炼的模型服务。

<meta property="og:title" content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

1. 前往阿里云百炼[API Key](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)页面，在右上角选择<strong>地域</strong>。每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>，各地域的 API Key 入口和接入域名请参见[各地域接入信息](/zh/model-studio/regions#h2_cc92e61c)。

2. 若已有可用 API Key，直接在列表中复制。若需创建，单击<strong>创建 API Key</strong>，在弹窗中配置以下选项后单击<strong>确定</strong>（若无法创建，请联系超级管理员或业务空间管理员）：

   - <strong>归属账号</strong>：默认选择<strong>阿里云账号（主账号）</strong>（账号名通常为一串数字）。如需为团队成员或应用创建权责独立的 API Key 并结合业务空间做精细化模型访问控制，可选择 [RAM 用户](https://help.aliyun.com/zh/ram/user-guide/overview-of-ram-users)（账号格式 `username@<AccountAlias>.onaliyun.com`）。
   - <strong>归属业务空间</strong>：默认选择<strong>默认业务空间</strong>（数量上限与主账号配额见[时效性与限制](#apikey-limits)）。如需权限隔离、精细化模型访问控制或独立成本核算，请选择非默认业务空间，参见[业务空间管理](/zh/model-studio/permission-management-overview)。
   - <strong>权限</strong>：建议选择<strong>全部</strong>。如需精细控制，可选择<strong>自定义</strong>，配置可访问 IP 和可访问模型范围（数量限制见[时效性与限制](#apikey-limits)）。

3. 点击新创建的 API Key 旁的<Image src="https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/8412544571/p994217.png" alt="image" className="inline" noZoom />图标复制 API Key。

## 配置 API Key 到环境变量 <span id="20b17d4430qvt" /> <span id="6a82f1a968bhf" />

- <strong>方式一：在</strong>[<strong>第三方工具</strong>](/zh/model-studio/use-chat-client-or-development-tool)<strong>中进行配置</strong>

  如果在 Chatbox 等工具或平台中调用模型，您可能需要输入三个信息：

  - 本文获取的 API Key
  - Base URL：
~~~~

来源#3：`qwen-errors.md`，chunk=145，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
.dashscope.aliyuncs.com/v1)</a>；Token Plan 团队版的专属 Base URL 可在控制台<strong>我的订阅</strong>的 API Key 区域查看。请确认同时更新了 API Key 和 Base URL，具体配置方法请分别参见接入AI工具与[快速开始](/zh/model-studio/token-plan-team-quickstart)。
- <strong>地域不匹配</strong>：API Key 和 Base URL 属于不同的地域，例如使用了华北2（北京）地域的 API Key 和新加坡地域的 Base URL。请确认您使用的 API Key 位于[北京](https://bailian.console.aliyun.com/settings/api-key)地域页面或[新加坡](https://bailian.console.aliyun.com/settings/api-key)地域页面，或[美国](https://bailian.console.aliyun.com/us-east-1)地域页面。各地域对应的 Base URL 如下：

[同版本引用上下文]
> 此方式便于调试，请勿用于生产环境。
- <strong>填写错误</strong>：阿里云百炼的 API Key 以 `sk-` 开头，请确认未误填其他模型提供商的密钥，且复制时未包含多余空格或换行符。
- <strong>套餐专属 API Key（Coding Plan / Token Plan 团队版）</strong>：Coding Plan 与 Token Plan 团队版均提供以 `sk-sp-` 开头的专属 API Key，<strong>必须配合各自的专属 Base URL 使用</strong>，不可与通用 API Key/Base URL 混用（混用会返回本鉴权错误）。其中 Coding Plan 的专属地址为 <a href="https://coding.dashscope.aliyuncs.com/v1">[https://coding.dashscope.aliyuncs.com/v1](https://coding.dashscope.aliyuncs.com/v1)</a>；Token Plan 团队版的专属 Base URL 可在控制台<strong>我的订阅</strong>的 API Key 区域查看。请确认同时更新了 API Key 和 Base URL，具体配置方法请分别参见接入AI工具与[快速开始](/zh/model-studio/token-plan-team-quickstart)。
- <strong>地域不匹配</strong>：API Key 和 Base URL 属于不同的地域，例如使用了华北2（北京）地域的 API Key 和新加坡地域的 Base URL。请确认您使用的 API Key 位于[北京](https://bailian.console.aliyun.com/settings/api-key)地域页面或[新加坡](https://bailian.console.aliyun.com/settings/api-key)地域页面，或[美国](https://bailian.console.aliyun.com/us-east-1)地域页面。各地域对应的 Base URL 如下：
~~~~

来源#4：`qwen-api-key.md`，chunk=5，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
- 华北2（北京）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
    - 其他地域：请参见[Base URL 总览](/zh/model-studio/base-url)
  - 模型名称，如 qwen-plus、qwen-max、deepseek-v4-pro 等。

  我们也提供了一些常用工具的配置方法：[Dify](/zh/model-studio/dify)、[Chatbox](/zh/model-studio/chatbox)、[Cline](/zh/model-studio/cline)、[Claude Code](/zh/model-studio/claude-code)、[Postman](/zh/model-studio/first-call-to-image-and-video-api)。
- <strong>方式二：配置 API Key 到环境变量，后续支持 cURL 和代码调用</strong>

  <Tip>
    请勿在客户端代码（如浏览器、移动应用）或不可信环境中配置或使用长期有效的 API Key。可以使用[临时 API Key](/zh/model-studio/generate-temporary-api-key)（最长 1800 秒）。
  </Tip>

[同版本引用上下文]
- 华北2（北京）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
    - 其他地域：请参见[Base URL 总览](/zh/model-studio/base-url)
  - 模型名称，如 qwen-plus、qwen-max、deepseek-v4-pro 等。

  我们也提供了一些常用工具的配置方法：[Dify](/zh/model-studio/dify)、[Chatbox](/zh/model-studio/chatbox)、[Cline](/zh/model-studio/cline)、[Claude Code](/zh/model-studio/claude-code)、[Postman](/zh/model-studio/first-call-to-image-and-video-api)。
- <strong>方式二：配置 API Key 到环境变量，后续支持 cURL 和代码调用</strong>

  <Tip>
    请勿在客户端代码（如浏览器、移动应用）或不可信环境中配置或使用长期有效的 API Key。可以使用[临时 API Key](/zh/model-studio/generate-temporary-api-key)（最长 1800 秒）。
  </Tip>

  以下示例中的 `<YOUR_API_KEY>` 需替换为真实的 API Key。

  <Tabs>
    <Tab title="Linux系统">
      <Tabs>
        <Tab title="添加永久性环境变量">
          将环境变量设置追加到`~/.bashrc`文件中。

          ```bash
          echo "export DASHSCOPE_API_KEY='<YOUR_API_KEY>'" >> ~/.bashrc
          source ~/.bashrc
          echo "百炼 API Key 永久配置为：${DASHSCOPE_API_KEY:0:10}*********"
          ```
        </Tab>

        <Tab title="添加临时性环境变量">
          ```bash
          export DASHSCOPE_API_KEY='<YOUR_API_KEY>'
          echo "当前会话百炼 API Key 配置为：${DASHSCOPE_API_KEY:0:10}*********"
          ```
        </Tab>

        <Tab title="服务管理器 (systemd)">
          以下操作适用于将应用作为后台服务部署的场景。

          1. <strong>创建环境文件</strong>

          ```bash
          sudo sh -c "echo 'DASHSCOPE_API_KEY=<YOUR_API_KEY>' > /etc/your-app/env"
          sudo chmod 600 /etc/your-app/env # 限制只有root用户有访问权限
          ```

          2. <strong>修改 systemd 服务文件</strong>（如 `/etc/systemd/system/your-app.service`）：

          ```zsh
          [Service]
          # 加载密钥文件
          EnvironmentFile=/etc/your-app/env
          ExecStart=/usr/bin/python /opt/your-app/main.py
          ```

          3. <strong>重载服务</strong>
~~~~

来源#5：`qwen-batch.md`，chunk=104，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
// 北京地域配置（默认）
          private static final String BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
          // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
          // private static final String BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
          // 注意：切换地域时，API Key也需要对应更换

          private static String API_KEY;

[同版本引用上下文]
// 北京地域配置（默认）
          private static final String BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
          // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
          // private static final String BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
          // 注意：切换地域时，API Key也需要对应更换

          private static String API_KEY;

          public static void main(String[] args) throws Exception {
              API_KEY = System.getenv("DASHSCOPE_API_KEY");
              if (API_KEY == null || API_KEY.isEmpty()) {
                  System.err.println("错误: 请设置环境变量 DASHSCOPE_API_KEY");
                  System.err.println("或在代码中设置: API_KEY = \"sk-xxx\";");
                  System.exit(1);
              }

      String fileId = uploadFile("test.jsonl");
              System.out.println("文件ID: " + fileId);
          }

          // === 工具方法 ===

          private static String uploadFile(String filePath) throws Exception {
              String boundary = "----WebKitFormBoundary" + System.currentTimeMillis();
              URL url = new URL(BASE_URL + "/files");
              HttpURLConnection conn = (HttpURLConnection) url.openConnection();
              conn.setDoOutput(true);
              conn.setRequestMethod("POST");
              conn.setRequestProperty("Authorization", "Bearer " + API_KEY);
              conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

              try (DataOutputStream out = new DataOutputStream(conn.getOutputStream())) {
                  // 添加 purpose 字段
                  out.writeBytes("--" + boundary + "\r\n");
                  out.writeBytes("Content-Disposition: form-data; name=\"purpose\"\r\n\r\n");
                  out.writeBytes("batch\r\n");
~~~~

来源#6：`qwen-quickstart.md`，chunk=3，version=d3261e119d9e5592b95c436578b3b214，HTTP=200

~~~~text
ailian.console.aliyun.com/model/settings/api-key)页面，单击<strong>创建API Key，</strong>即可通过API KEY调用大模型。

   创建 API Key 时无需选择模型，调用时通过请求体中的`model`参数指定要调用的模型（例如`model="qwen-plus"`），可用模型请参见[模型列表](/zh/model-studio/models)。如需限制该 API Key 可调用的模型范围，创建时选择<strong>自定义</strong>权限，并开启<strong>访问模型范围</strong>开关，开启后该 API Key 仅能调用已选择的模型。
4. <strong>获取业务空间ID：</strong>使用<strong>华北2（北京）</strong>、<strong>新加坡</strong>、<strong>日本（东京）</strong>、<strong>德国（法兰克福）</strong>或<strong>中国香港</strong>地域的模型时，需在Base URL中填入业务空间ID（WorkspaceId），可在[业务空间管理](https://bailian.console.aliyun.com/cn-beijing/settings/workspace)页面中查看。

[同版本引用上下文]
# Qwen / 阿里云百炼：首次调用

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[首次调用千问API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 首次调用千问API

> 阿里云百炼支持通过API调用大模型，涵盖OpenAI兼容接口、DashScope SDK等接入方式。

<meta property="og:title" content="首次调用千问API" />

<Note>
  - 若您熟悉大模型调用，可直接查看API参考文档[文本生成](/zh/model-studio/qwen-api-reference)。
  - 若您不熟悉编程，可参考[Chatbox](https://help.aliyun.com/zh/model-studio/cline-tool)，通过图形化界面与千问模型对话。
  - API调用与操作系统版本无关，只要网络能连通即可正常使用。
</Note>

本文以千问为例，引导您完成大模型API调用。您将了解到：

- 如何获取 API Key
- 如何配置本地开发环境
- 如何调用千问 API

## 账号设置 <span id="f92b9b9cc7huw" />

1. <strong>注册账号</strong>：若无阿里云账号，需首先[注册](https://account.aliyun.com/register/qr_register.htm)。

   > 如遇问题，请参见[注册阿里云账号](https://help.aliyun.com/zh/account/step-1-register-an-alibaba-cloud-account)。
2. <strong>开通阿里云百炼：</strong>使用<strong>阿里云主账号</strong>前往[阿里云百炼大模型服务平台](https://bailian.console.aliyun.com/model/market)，阅读并同意协议后，将自动开通阿里云百炼，如果未弹出服务协议，则表示您已经开通。

   > 如果开通服务时提示“您尚未进行实名认证”，请先进行[实名认证](https://help.aliyun.com/zh/account/verify-your-identity-individual-account)。
3. <strong>获取API Key：</strong>前往[API Key](https://bailian.console.aliyun.com/model/settings/api-key)页面，单击<strong>创建API Key，</strong>即可通过API KEY调用大模型。

   创建 API Key 时无需选择模型，调用时通过请求体中的`model`参数指定要调用的模型（例如`model="qwen-plus"`），可用模型请参见[模型列表](/zh/model-studio/models)。如需限制该 API Key 可调用的模型范围，创建时选择<strong>自定义</strong>权限，并开启<strong>访问模型范围</strong>开关，开启后该 API Key 仅能调用已选择的模型。
4. <strong>获取业务空间ID：</strong>使用<strong>华北2（北京）</strong>、<strong>新加坡</strong>、<strong>日本（东京）</strong>、<strong>德国（法兰克福）</strong>或<strong>中国香港</strong>地域的模型时，需在Base URL中填入业务空间ID（WorkspaceId），可在[业务空间管理](https://bailian.console.aliyun.com/cn-beijing/settings/workspace)页面中查看。
~~~~

来源#7：`qwen-regions.md`，chunk=36，version=d3a82cffaca35834b0a443d899c1c294，HTTP=200

~~~~text
{{ verticalAlign: "top" }}><p>不支持</p></td></tr></tbody></table>

## 相关文档 <span id="h2_2caf88e3" />

- [通义千问 API 参考](/zh/model-studio/qwen-api-reference)
- [选择模型](/zh/model-studio/models) — 各地域模型及上下文长度
- [模型调用计费](/zh/model-studio/model-pricing) — 各地域价格
- [限流](/zh/model-studio/rate-limit)— RPM、TPM 限制
- [获取与配置 API Key](/zh/model-studio/get-api-key) — 创建和管理 Key
- [Base URL总览](/zh/model-studio/base-url) — 模型服务调用地址
- [Realtime API 协议选型](/zh/model-studio/realtime-api-overview#rtov-protocol-selection)

[同版本引用上下文]
lign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型调优</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>应用开发</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr></tbody></table>

## 相关文档 <span id="h2_2caf88e3" />

- [通义千问 API 参考](/zh/model-studio/qwen-api-reference)
- [选择模型](/zh/model-studio/models) — 各地域模型及上下文长度
- [模型调用计费](/zh/model-studio/model-pricing) — 各地域价格
- [限流](/zh/model-studio/rate-limit)— RPM、TPM 限制
- [获取与配置 API Key](/zh/model-studio/get-api-key) — 创建和管理 Key
- [Base URL总览](/zh/model-studio/base-url) — 模型服务调用地址
- [Realtime API 协议选型](/zh/model-studio/realtime-api-overview#rtov-protocol-selection)
~~~~

## C03 · gpt · fact

OpenAI后台响应如何开启，queued和in_progress时怎样轮询？

判分要求：background=true；GET/retrieve继续轮询两种状态，终态停止

审阅：PASS。background 开启和 queued/in_progress 继续 retrieve，退出后停止轮询正确。

### 原始回答

## 开启后台响应（Background mode）

在创建 Response 时把后台模式开关设为 true 即可。不同语言 SDK 的写法：

- **C#**：`CreateResponseOptions` 中设置 `BackgroundModeEnabled = true`（来源#1）
- **Ruby**：`client.responses.create(..., background: true)`（来源#1、来源#2）
- **Python**：`client.responses.create(..., background=True)`（来源#5）
- **Go**：`responses.ResponseNewParams{ Background: openai.Bool(true), ... }`（来源#5）
- **JavaScript**：`client.responses.create({ ..., background: true })`（来源#1）

创建后返回的 `response.status` 即为当前状态（来源#1）。

## queued / in_progress 时的轮询方式

规则：用 Responses 的 **GET 接口**查询状态；只要状态仍是 `queued` 或 `in_progress` 就继续轮询，一旦离开这两个状态即进入终态（来源#1）。

**HTTP 方式**（来源#1）：

```bash
curl https://api.openai.com/v1/responses/resp_123 \
  -H "Content-Type: application/json" \
  -H "Authorization: [REDACTED] $OPENAI_API_KEY"
```

**JavaScript 循环示例**（来源#1）：

```javascript
let resp = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true,
});

while (resp.status === "queued" || resp.status === "in_progress") {
  console.log("Current status: " + resp.status);
  await new Promise((resolve) => setTimeout(resolve, 2000)); // 等 2 秒
  resp = await client.responses.retrieve(resp.id);
}
console.log("Final status: " + resp.status);
```

**Python 循环示例**（来源#5）：

```python
resp = client.responses.create(
    model="gpt-6-astra",
    input="Write a very long novel about otters in space.",
    background=True,
)

while resp.status in {"queued", "in_progress"}:
    print(f"Current status: {resp.status}")
    sleep(2)
    resp = client.responses.retrieve(resp.id)

print(f"Final status: {resp.status}\nOutput:\n{resp.output_text}")
```

**Ruby 循环示例**（来源#2）：

```ruby
while [:queued, :in_progress].include?(response.status)
  puts("Current status: #{response.status}")
  sleep(2)
  response = client.responses.retrieve(response.id)
end
```

**Go 循环示例**（来源#5）：在 `for response.Status == "queued" || response.Status == "in_progress"` 中 `time.Sleep(2 * time.Second)` 后调用 `client.Responses.Get(...)` 重新获取。

## 补充说明

- 文档示例中的轮询间隔为 2 秒，可按需调整（来源#1、来源#2、来源#5）。
- 后台响应也支持取消：`POST https://api.openai.com/v1/responses/resp_123/cancel`（来源#2）。
- 除轮询外，也可通过 webhook 接收 `response.completed` 事件，再按 response id 调 `responses.retrieve` 取结果（来源#6）；webhook 签名可用 SDK 的 `unwrap()` 校验（来源#7）。

以上均为文档中的通用用法说明，不代表你账户的具体配置状态。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-quickstart.md
来源#4: gpt-rate-limits.md
来源#5: gpt-background.md
来源#6: gpt-webhooks.md
来源#7: gpt-webhooks.md

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

[同版本引用上下文]
string key = Environment.GetEnvironmentVariable("OPENAI_API_KEY")!;
ResponsesClient client = new(key);

CreateResponseOptions options = new()
{
    Model = "gpt-6-astra",
    BackgroundModeEnabled = true,
};
options.InputItems.Add(
    ResponseItem.CreateUserMessageItem("Write a very long novel about otters in space.")
);

ResponseResult response = await client.CreateResponseAsync(options);
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

```bash
curl https://api.openai.com/v1/responses/resp_123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

```javascript
import OpenAI from "openai";
const client = new OpenAI();

let resp = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true,
});

while (resp.status === "queued" || resp.status === "in_progress") {
  console.log("Current status: " + resp.status);
  await new Promise((resolve) => setTimeout(resolve, 2000)); // wait 2 seconds
  resp = await client.responses.retrieve(resp.id);
}

console.log("Final status: " + resp.status + "\nOutput:\n" + resp.output_text);
```

```python
from openai import OpenAI
from time import sleep

client = OpenAI()
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

[同版本引用上下文]
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

```bash
curl -X POST https://api.openai.com/v1/responses/resp_123/cancel \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

```javascript
import OpenAI from "openai";
const client = new OpenAI();

const resp = await client.responses.cancel("resp_123");

console.log(resp.status);
```

```python
import os

from openai import OpenAI

response_id = os.environ["OPENAI_RESPONSE_ID"]
client = OpenAI()

resp = client.responses.cancel(response_id)

print(resp.status)
```

```go
package main

import (
	"context"
	"fmt"

	"github.com/openai/openai-go/v3"
)

func main() {
	client := openai.NewClient()

	canceled, err := client.Responses.Cancel(context.Background(), "resp_123")
	if err != nil {
		panic(err)
	}

	fmt.Println(canceled.Status)
}
```

```java
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;

String responseId = "resp_123";

var response = client.responses().cancel(responseId);

System.out.println(response.status());
```

```csharp
using OpenAI.Responses;
#pragma warning disable OPENAI001

string key = Environment.GetEnvironmentVariable("OPENAI_API_KEY")!;
ResponsesClient client = new(key);
~~~~

来源#3：`gpt-quickstart.md`，chunk=119，version=a1f4e1679fcb52ac90881307538f7489，HTTP=200

~~~~text
t events from the API

```javascript
import { OpenAI } from "openai";
const client = new OpenAI();

const stream = await client.responses.create({
  model: "gpt-6-astra",
  input: [
    {
      role: "user",
      content: "Say 'double bubble bath' ten times fast.",
    },
  ],
  stream: true,
});

for await (const event of stream) {
  console.log(event);
}
```

```python
from openai import OpenAI

client = OpenAI()

[同版本引用上下文]
Learn to enable the model to call your own custom code.](https://developers.openai.com/api/docs/guides/function-calling)

## Stream responses and build real-time apps

Use server‑sent [streaming events](https://developers.openai.com/api/docs/guides/streaming-responses) to show results as they’re generated, or use the [Realtime API](https://developers.openai.com/api/docs/guides/realtime) for interactive voice apps and apps with text, audio, and image inputs.

Stream server-sent events from the API

```javascript
import { OpenAI } from "openai";
const client = new OpenAI();

const stream = await client.responses.create({
  model: "gpt-6-astra",
  input: [
    {
      role: "user",
      content: "Say 'double bubble bath' ten times fast.",
    },
  ],
  stream: true,
});

for await (const event of stream) {
  console.log(event);
}
```

```python
from openai import OpenAI

client = OpenAI()

stream = client.responses.create(
    model="gpt-6-astra",
    input=[
        {
            "role": "user",
            "content": "Say 'double bubble bath' ten times fast.",
        },
    ],
    stream=True,
)

for event in stream:
    print(event)
```

```go
package main

import (
	"context"
	"fmt"

	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/responses"
)

func main() {
	client := openai.NewClient()
	stream := client.Responses.NewStreaming(context.Background(), responses.ResponseNewParams{
		Model: "gpt-6-astra",
		Input: responses.ResponseNewParamsInputUnion{OfString: openai.String("Say 'double bubble bath' ten times fast.")},
	})
	for stream.Next() {
		fmt.Println(stream.Current().Type)
	}
	if err := stream.Err(); err != nil {
		panic(err)
	}
}
```
~~~~

来源#4：`gpt-rate-limits.md`，chunk=7，version=7c736b1dd2a954cc9f41609a86e3a928，HTTP=200

~~~~text
as 20), even if you didn't send 150k tokens (if your TPM limit was 150k) within those 20 requests.

[Batch API](https://developers.openai.com/api/reference/resources/batches/methods/create) queue limits are calculated based on the total number of input tokens queued for a given model. Tokens from pending batch jobs are counted against your queue limit. Once a batch job is completed, its tokens are no longer counted against that model's limit.

Other important things worth noting:

[同版本引用上下文]
Please work through this document in its entirety to better understand how
  OpenAI’s rate limit system works. We include code examples and possible
  solutions to handle common issues. We also include details around how your
  rate limits are automatically increased in the usage tiers section below.

## How do these rate limits work?

Rate limits use metrics such as **RPM** (requests per minute), **RPD** (requests per day), **TPM** (tokens per minute), **TPD** (tokens per day), **IPM** (images per minute), and audio minutes per minute for some streaming audio models. Rate limits can be hit across any of the options depending on what occurs first. For example, you might send 20 requests with only 100 tokens to the ChatCompletions endpoint and that would fill your limit (if your RPM was 20), even if you didn't send 150k tokens (if your TPM limit was 150k) within those 20 requests.

[Batch API](https://developers.openai.com/api/reference/resources/batches/methods/create) queue limits are calculated based on the total number of input tokens queued for a given model. Tokens from pending batch jobs are counted against your queue limit. Once a batch job is completed, its tokens are no longer counted against that model's limit.

Other important things worth noting:
~~~~

来源#5：`gpt-background.md`，chunk=16，version=fc4bfe66d6345d5a99f63f24a73252ff，HTTP=200

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

[同版本引用上下文]
resp = client.responses.create(
    model="gpt-6-astra",
    input="Write a very long novel about otters in space.",
    background=True,
)

while resp.status in {"queued", "in_progress"}:
    print(f"Current status: {resp.status}")
    sleep(2)
    resp = client.responses.retrieve(resp.id)

print(f"Final status: {resp.status}\nOutput:\n{resp.output_text}")
```

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/responses"
)

func main() {
	client := openai.NewClient()

	response, err := client.Responses.New(context.Background(), responses.ResponseNewParams{
		Model:      "gpt-6-astra",
		Background: openai.Bool(true),
		Input: responses.ResponseNewParamsInputUnion{
			OfString: openai.String("Write a very long novel about otters in space."),
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

```java
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.responses.ResponseCreateParams;
import com.openai.models.responses.ResponseStatus;

ResponseCreateParams params =
    ResponseCreateParams.builder()
        .model("gpt-6-astra")
        .input("Write a very long novel about otters in space.")
        .background(true)
        .build();
~~~~

来源#6：`gpt-webhooks.md`，chunk=5，version=044234a8b47552e9be6fe27688178fdd，HTTP=200

~~~~text
Below are examples of servers capable of ingesting webhooks from OpenAI, specifically for the [`response.completed`](https://developers.openai.com/api/reference/resources/webhooks) event.

For the Ruby examples, install the required dependencies with
`gem install openai webrick`, then set `OPENAI_API_KEY` and
`OPENAI_WEBHOOK_SECRET`.

Webhooks server

```javascript
import OpenAI from "openai";
import express from "express";

const app = express();
const client = new OpenAI({ webhookSecret: process.env.OPENAI_WEBHOOK_SECRET });

[同版本引用上下文]
Below are examples of servers capable of ingesting webhooks from OpenAI, specifically for the [`response.completed`](https://developers.openai.com/api/reference/resources/webhooks) event.

For the Ruby examples, install the required dependencies with
`gem install openai webrick`, then set `OPENAI_API_KEY` and
`OPENAI_WEBHOOK_SECRET`.

Webhooks server

```javascript
import OpenAI from "openai";
import express from "express";

const app = express();
const client = new OpenAI({ webhookSecret: process.env.OPENAI_WEBHOOK_SECRET });

// Don't use express.json() because signature verification needs the raw text body
app.use(express.text({ type: "application/json" }));

app.post("/webhook", async (req, res) => {
  try {
    const event = await client.webhooks.unwrap(req.body, req.headers);

    if (event.type === "response.completed") {
      const response_id = event.data.id;
      const response = await client.responses.retrieve(response_id);
      const output_text = response.output
        .filter((item) => item.type === "message")
        .flatMap((item) => item.content)
        .filter((contentItem) => contentItem.type === "output_text")
        .map((contentItem) => contentItem.text)
        .join("");

      console.log("Response output:", output_text);
    }
    res.status(200).send();
  } catch (error) {
    if (error instanceof OpenAI.InvalidWebhookSignatureError) {
      console.error("Invalid signature", error);
      res.status(400).send("Invalid signature");
    } else {
      throw error;
    }
  }
});

app.listen(8000, () => {
  console.log("Webhook server is running on port 8000");
});
```

```python
import os
from openai import OpenAI, InvalidWebhookSignatureError
from flask import Flask, request, Response
~~~~

来源#7：`gpt-webhooks.md`，chunk=33，version=044234a8b47552e9be6fe27688178fdd，HTTP=200

~~~~text
from openai import OpenAI

client = OpenAI()
webhook_secret = os.environ["OPENAI_WEBHOOK_SECRET"]

# will raise if the signature is invalid
event = client.webhooks.unwrap(
    request.data,
    request.headers,
    secret=webhook_secret,
)
```

[同版本引用上下文]
- [ngrok](https://ngrok.com/) which can expose your localhost server on a public URL
- Cloud development environments like [Replit](https://replit.com/), [GitHub Codespaces](https://github.com/features/codespaces), [Cloudflare Workers](https://workers.cloudflare.com/), or [v0 from Vercel](https://v0.dev/).

## Verifying webhook signatures

While you can receive webhook events from OpenAI and process the results without any verification, you should verify that incoming requests are coming from OpenAI, especially if your webhook will take any kind of action on the backend. The headers sent along with webhook requests contain information that can be used in combination with a webhook secret key to verify that the webhook originated from OpenAI.

When you create a webhook endpoint in the OpenAI dashboard, you'll be given a signing secret that you should make available on your server as an environment variable:

```
export OPENAI_WEBHOOK_SECRET="<your secret here>"
```

The simplest way to verify webhook signatures is by using the `unwrap()` method of the official OpenAI SDK helpers:

Signature verification with the OpenAI SDK

```javascript
const client = new OpenAI();
const webhook_secret = process.env.OPENAI_WEBHOOK_SECRET;
if (!webhook_secret) throw new Error("Set OPENAI_WEBHOOK_SECRET.");

// will throw if the signature is invalid
const event = await client.webhooks.unwrap(
  req.body,
  req.headers,
  webhook_secret
);
```

```python
import os

from flask import request
from openai import OpenAI

client = OpenAI()
webhook_secret = os.environ["OPENAI_WEBHOOK_SECRET"]

# will raise if the signature is invalid
event = client.webhooks.unwrap(
    request.data,
    request.headers,
    secret=webhook_secret,
)
```
~~~~

## C04 · qwen · fact

Qwen的OpenAI兼容流式聊天，stream_options.include_usage应如何配置？

判分要求：stream=true；stream_options.include_usage=true，位置正确

审阅：PASS。stream 与 include_usage 配置、最后 usage 块及空 choices 处理正确。

### 原始回答

针对 Qwen 的 OpenAI 兼容流式聊天，`stream_options.include_usage` 的配置方式如下：

**1. 配置方式**

在调用 `chat.completions.create` 时，将 `stream` 设为 `true`，并同时传入：

```python
stream=True,
stream_options={"include_usage": True}
```

OpenAI 协议默认不返回 Token 消耗量；设置 `stream_options={"include_usage": true}` 后，**最后一个返回的数据块**会包含 Token 消耗信息（来源#1）。在思考模式（如 qwen3.8-max）的 OpenAI 兼容示例中，也是同样写法，注释说明为“使流式返回的最后一个数据包包含 Token 消耗信息”（来源#5）。

**2. 解析时的注意事项**

开启该选项后，最后一个 chunk 的 `choices` 字段为空列表，需要通过 `chunk.usage` 获取 Token 使用量；遍历时需跳过该空 `choices` 的块，避免取值报错（来源#2、来源#6）。

**3. 非流式调用时不能设置**

`stream=False`（非流式/同步）时**不能**设置 `stream_options` 参数（来源#4）。因此该参数仅适用于流式调用场景。

**4. 适用范围说明**

以上规则来自 Alibaba Cloud（阿里云百炼）Qwen API 的 OpenAI 兼容接口文档，仅适用于该厂商的 Qwen API；其他厂商或接口的 `stream_options` 行为需以其各自文档为准（来源#1、来源#7）。

来源#1: qwen-streaming.md
来源#2: qwen-streaming.md
来源#3: qwen-streaming.md
来源#4: qwen-thinking.md
来源#5: qwen-thinking.md
来源#6: qwen-streaming.md
来源#7: qwen-chat-completions.md

### 实际引用锚点

来源#1：`qwen-streaming.md`，chunk=2，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
.5-Omni、Qwen3-Omni-Flash 仅支持流式输出方式调用。
</Tip>

### 步骤一：配置 API Key 并选择地域 <span id="c9d7f901b4l4q" />

您需要已[获取与配置 API Key](/zh/model-studio/get-api-key)。

> 将API Key配置为环境变量（`DASHSCOPE_API_KEY`）比在代码中硬编码更安全。

### 步骤二：发起流式请求 <span id="e265f9c0b3e82" />

<Tabs>
  <Tab title="OpenAI兼容">
    - <strong>如何开启</strong>

      设置 `stream` 为 `true` 即可。
    - <strong>查看 Token 消耗</strong>

      OpenAI 协议默认不返回 Token 消耗量，需设置`stream_options={"include_usage": true}`，使<strong>最后一个返回的数据块</strong>包含Token消耗信息。

[同版本引用上下文]
# Qwen / 阿里云百炼：流式输出

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[流式输出](https://help.aliyun.com/zh/model-studio/stream)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 流式输出

> 在实时聊天或长文本生成应用中，长时间的等待会损害用户体验并可能导致触发服务端超时，导致任务失败。流式输出通过持续返回模型生成的文本片段，解决了这两个核心问题。

<meta property="og:title" content="流式输出" />

## 工作原理 <span id="4880e0d360hlk" />

流式输出基于 Server-Sent Events (SSE) 协议。发起流式请求后，服务端与客户端建立持久化 HTTP 连接。模型每生成一个文本块（称为 chunk），立即通过连接推送。全部内容生成后，服务端发送结束信号。

客户端监听事件流，实时接收并处理文本块，例如逐字渲染界面。这与非流式调用（一次性返回所有内容）形成对比。

> 以上组件仅供您参考，并未真实发送请求。

<Note>
  流式与非流式的响应结构不同：非流式返回单个 JSON 对象，正文位于 `choices[0].message.content`；流式通过 SSE 逐块返回，正文位于 `choices[0].delta.content`，需客户端拼接，以 `data: [DONE]` 结束。
</Note>

## 计费说明 <span id="602f9a76a45wc" />

流式输出计费规则与非流式调用完全相同，根据请求的输入Token数和输出Token数计费。

请求中断时，输出 Token 仅计算服务端收到终止请求前已生成的部分。

## 如何使用 <span id="c494533e4cot6" />

<Tip>
  Qwen3 开源版、QwQ 商业版与开源版、QVQ，以及 Qwen3.5-Omni、Qwen3-Omni-Flash 仅支持流式输出方式调用。
</Tip>

### 步骤一：配置 API Key 并选择地域 <span id="c9d7f901b4l4q" />

您需要已[获取与配置 API Key](/zh/model-studio/get-api-key)。

> 将API Key配置为环境变量（`DASHSCOPE_API_KEY`）比在代码中硬编码更安全。

### 步骤二：发起流式请求 <span id="e265f9c0b3e82" />

<Tabs>
  <Tab title="OpenAI兼容">
    - <strong>如何开启</strong>

      设置 `stream` 为 `true` 即可。
    - <strong>查看 Token 消耗</strong>

      OpenAI 协议默认不返回 Token 消耗量，需设置`stream_options={"include_usage": true}`，使<strong>最后一个返回的数据块</strong>包含Token消耗信息。

    <Tabs>
      <Tab title="Python">
        ```python expandable
        import os
        from openai import OpenAI
~~~~

来源#2：`qwen-streaming.md`，chunk=57，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
sage": True}
      )
      full_content = ""
      print("流式输出内容为：")
      for chunk in completion:
          # 如果stream_options.include_usage为True，则最后一个chunk的choices字段为空列表，需要跳过（可以通过chunk.usage获取 Token 使用量）
          if chunk.choices and chunk.choices[0].delta.content != "":
              full_content += chunk.choices[0].delta.content
              print(chunk.choices[0].delta.content)
      print(f"完整内容为：{full_content}")
      ```

      ```javascript Node.js expandable
      import OpenAI from "openai";

[同版本引用上下文]
completion = client.chat.completions.create(
          model="qwen3-vl-plus",  # 可按需更换为其它多模态模型，并修改相应的 messages
          messages=[
              {"role": "user",
               "content": [{"type": "image_url",
                          "image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"},},
                          {"type": "text", "text": "图中描绘的是什么景象？"}]}],
          stream=True,
        # stream_options={"include_usage": True}
      )
      full_content = ""
      print("流式输出内容为：")
      for chunk in completion:
          # 如果stream_options.include_usage为True，则最后一个chunk的choices字段为空列表，需要跳过（可以通过chunk.usage获取 Token 使用量）
          if chunk.choices and chunk.choices[0].delta.content != "":
              full_content += chunk.choices[0].delta.content
              print(chunk.choices[0].delta.content)
      print(f"完整内容为：{full_content}")
      ```

      ```javascript Node.js expandable
      import OpenAI from "openai";

      const openai = new OpenAI(
          {
              // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey: "sk-xxx"
              // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
              apiKey: process.env.DASHSCOPE_API_KEY,
              // 以下为华北2（北京）地域的URL，调用时请将WorkspaceId替换为真实的业务空间ID，各地域的URL不同。
              baseURL: "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
          }
      );
~~~~

来源#3：`qwen-streaming.md`，chunk=77，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
<Tabs>
  <Tab title="OpenAI兼容">
    以下是使用 OpenAI Python SDK 以流式方式调用思考模式 qwen-plus 模型时返回的数据格式：

    ```plaintext
    # 思考阶段
    ...
    ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content='覆盖所有要点，同时')
    ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content='自然流畅。')
    # 回复阶段
    ChoiceDelta(content='你好！我是**通', function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content=None)

[同版本引用上下文]
<Tabs>
  <Tab title="OpenAI兼容">
    以下是使用 OpenAI Python SDK 以流式方式调用思考模式 qwen-plus 模型时返回的数据格式：

    ```plaintext
    # 思考阶段
    ...
    ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content='覆盖所有要点，同时')
    ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content='自然流畅。')
    # 回复阶段
    ChoiceDelta(content='你好！我是**通', function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content=None)
    ChoiceDelta(content='义千问**（', function_call=None, refusal=None, role=None, tool_calls=None, reasoning_content=None)
    ...
    ```

    - 若`reasoning_content`不为 None，`content` 为 `None`，则当前处于思考阶段；
    - 若`reasoning_content`为 None，`content` 不为 `None`，则当前处于回复阶段；
    - 若两者均为 `None`，则阶段与前一包一致。

    <Tabs>
      <Tab title="Python">
        ### 示例代码 <span id="476b0d8764uct" />

        ```python expandable
        from openai import OpenAI
        import os

        # 初始化OpenAI客户端
        client = OpenAI(
            # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
            # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            # 以下为华北2（北京）地域的URL，调用时请将WorkspaceId替换为真实的业务空间ID，各地域的URL不同。
            base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        )

        messages = [{"role": "user", "content": "你是谁"}]
~~~~

来源#4：`qwen-thinking.md`，chunk=224，version=e6859f3d2b78563c809872285470797d，HTTP=200

~~~~text
<Accordion title="Q：如何以非流式（同步）方式调用深度思考模型？">
  本文示例默认采用流式输出（推荐，可实时查看思考过程、避免长时间等待）。商业版深度思考模型（如 qwen-plus、qwen-flash 等）也支持非流式（同步）输出，一次性返回完整的思考过程与回复。

  > 将流式示例改为非流式时，请同步修改<strong>结果解析代码</strong>：非流式调用返回的是完整的响应对象（`completion`），<strong>不能</strong>再像流式示例那样通过 `for chunk in completion` 迭代（否则会报错 `'tuple' object has no attribute 'choices'`），而应直接读取 `completion.choices[0].message.reasoning_content`（思考过程）与 `completion.choices[0].message.content`（回复内容）。此外，`stream=False` 时不能设置 `stream_options` 参数。

  以下以 OpenAI 兼容接口、非流式调用 qwen3.8-max 开启思考模式为例：

  ```python
  from openai import OpenAI
  import os

[同版本引用上下文]
<Accordion title="Q：如何以非流式（同步）方式调用深度思考模型？">
  本文示例默认采用流式输出（推荐，可实时查看思考过程、避免长时间等待）。商业版深度思考模型（如 qwen-plus、qwen-flash 等）也支持非流式（同步）输出，一次性返回完整的思考过程与回复。

  > 将流式示例改为非流式时，请同步修改<strong>结果解析代码</strong>：非流式调用返回的是完整的响应对象（`completion`），<strong>不能</strong>再像流式示例那样通过 `for chunk in completion` 迭代（否则会报错 `'tuple' object has no attribute 'choices'`），而应直接读取 `completion.choices[0].message.reasoning_content`（思考过程）与 `completion.choices[0].message.content`（回复内容）。此外，`stream=False` 时不能设置 `stream_options` 参数。

  以下以 OpenAI 兼容接口、非流式调用 qwen3.8-max 开启思考模式为例：

  ```python
  from openai import OpenAI
  import os

  client = OpenAI(
      # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
      # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
      api_key=os.getenv("DASHSCOPE_API_KEY"),
      # 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
      base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
  )

  completion = client.chat.completions.create(
      model="qwen3.8-max",  # 请替换为支持非流式输出的深度思考模型
      messages=[{"role": "user", "content": "你是谁"}],
      extra_body={"enable_thinking": True},
      stream=False,  # 非流式（同步）输出；stream=False 时不能设置 stream_options
  )

  # 非流式返回完整响应对象，直接读取 message，无需（也不能）迭代
  message = completion.choices[0].message
  print("=" * 20 + "思考过程" + "=" * 20 + "\n")
  print(getattr(message, "reasoning_content", "") or "")
  print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
  print(message.content)
  ```

  > 部分模型（如 qwen3.5-122b-a10b、qwen3.5-27b 等开源版）仅支持流式输出，非流式调用会报错 `parameter.enable_thinking only support stream call`，此类模型请使用流式调用。
</Accordion>

<Accordion title="Q： 免费额度 用完后如何购买 Token？">
  前往[费用与成本](https://usercenter2.aliyun.com/home)中心充值，保持账户余额充足即可正常调用模型。
~~~~

来源#5：`qwen-thinking.md`，chunk=4，version=e6859f3d2b78563c809872285470797d，HTTP=200

~~~~text
<Tabs>
    <Tab title="OpenAI 兼容">
      ```python
      # 导入依赖与创建客户端...
      completion = client.chat.completions.create(
          model="qwen3.8-max", # 选择模型
          messages=[{"role": "user", "content": "你是谁"}],
          # 由于 enable_thinking 非 OpenAI 标准参数，需要通过 extra_body 传入
          extra_body={"enable_thinking":True},
          # 流式输出方式调用
          stream=True,
          # 使流式返回的最后一个数据包包含Token消耗信息
          stream_options={
              "include_usage": True
          }
      )
      ```
    </Tab>

[同版本引用上下文]
<Tabs>
    <Tab title="OpenAI 兼容">
      ```python
      # 导入依赖与创建客户端...
      completion = client.chat.completions.create(
          model="qwen3.8-max", # 选择模型
          messages=[{"role": "user", "content": "你是谁"}],
          # 由于 enable_thinking 非 OpenAI 标准参数，需要通过 extra_body 传入
          extra_body={"enable_thinking":True},
          # 流式输出方式调用
          stream=True,
          # 使流式返回的最后一个数据包包含Token消耗信息
          stream_options={
              "include_usage": True
          }
      )
      ```
    </Tab>

    <Tab title="DashScope">
      > Qwen3.5 系列的 DashScope API采用多模态接口，以下示例会报错 `url error` ，调用方式请参见 [开启/关闭思考模式](/zh/model-studio/vision#bc67a9a2bd2of) 。

      ```python
      # 导入依赖...

      response = MultiModalConversation.call(
          # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key = "sk-xxx",
          api_key=os.getenv("DASHSCOPE_API_KEY"),
          # 可按需更换为其它深度思考模型
          model="qwen3.8-max",
          messages=messages,
          enable_thinking=True,
          stream=True,
          incremental_output=True
      )
      ```
    </Tab>
  </Tabs>
- <strong>仅思考模式</strong>：模型始终在回复前进行思考，无法关闭。除无需设置 `enable_thinking` 参数外，请求格式与混合思考模式一致。

思考内容通过`reasoning_content`字段返回，回复内容通过`content`字段返回。深度思考需要额外推理时间，本文示例默认采用流式调用（推荐，可实时查看思考过程、避免长时间等待）。商业版深度思考模型同时支持非流式（同步）输出，用法及注意事项参见下方<strong>常见问题</strong>；部分模型（如 qwen3.5-122b-a10b、qwen3.5-27b 等开源版）仅支持流式输出，非流式调用会报错。

## 支持的模型 <span id="78286fdc35hlw" />

<Tabs>
  <Tab title="Qwen3.8">
    <strong>千问3.8 Max系列</strong>（混合思考模式，<strong>默认开启思考模式</strong>）：qwen3.8-max、qwen3.8-max-0902

    <strong>千问3.8 Flash系列</strong>（混合思考模式，<strong>默认开启思考模式</strong>）：qwen3.8-flash

    <strong>千问3.8 开源系列</strong>（混合思考模式，<strong>默认开启思考模式</strong>）：qwen3.8-27b

    <strong>千问3.8 开源系列</strong>（<strong>仅支持思考模式</strong>）：qwen3.8-2.4t-a95b
~~~~

来源#6：`qwen-streaming.md`，chunk=60，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
是什么景象？"}]}],
          stream: true,
       // stream_options: { include_usage: true },

      });

      let fullContent = ""
      console.log("流式输出内容为：")
      for await (const chunk of completion) {
          // 如果stream_options.include_usage为true，则最后一个chunk的choices字段为空数组，需要跳过（可以通过chunk.usage获取 Token 使用量）
          if (chunk.choices[0] && chunk.choices[0].delta.content != null) {
            fullContent += chunk.choices[0].delta.content;
            console.log(chunk.choices[0].delta.content);
          }
      }
      console.log(`完整输出内容为：${fullContent}`)
      ```

[同版本引用上下文]
const completion = await openai.chat.completions.create({
          model: "qwen3-vl-plus",  // 可按需更换为其它多模态模型，并修改相应的 messages
          messages: [
              {role: "user",
              content: [{"type": "image_url",
                          "image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"},},
                          {"type": "text", "text": "图中描绘的是什么景象？"}]}],
          stream: true,
       // stream_options: { include_usage: true },

      });

      let fullContent = ""
      console.log("流式输出内容为：")
      for await (const chunk of completion) {
          // 如果stream_options.include_usage为true，则最后一个chunk的choices字段为空数组，需要跳过（可以通过chunk.usage获取 Token 使用量）
          if (chunk.choices[0] && chunk.choices[0].delta.content != null) {
            fullContent += chunk.choices[0].delta.content;
            console.log(chunk.choices[0].delta.content);
          }
      }
      console.log(`完整输出内容为：${fullContent}`)
      ```

      ```bash curl expandable
      # ======= 重要提示 =======
      # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
      # 以下为华北2（北京）地域的URL，调用时请将WorkspaceId替换为真实的业务空间ID，各地域的URL不同。
      # === 执行时请删除该注释 ===
~~~~

来源#7：`qwen-chat-completions.md`，chunk=0，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
# Qwen / 阿里云百炼：Chat Completions 参数

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[OpenAI兼容-Chat](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# OpenAI兼容-Chat

> 通过兼容 OpenAI 格式的 Chat API 调用模型，查看输入输出参数说明及调用示例。

<meta property="og:title" content="OpenAI兼容-Chat" />

<Tabs>
  <Tab title="华北2（北京）">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`

[同版本引用上下文]
# Qwen / 阿里云百炼：Chat Completions 参数

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[OpenAI兼容-Chat](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# OpenAI兼容-Chat

> 通过兼容 OpenAI 格式的 Chat API 调用模型，查看输入输出参数说明及调用示例。

<meta property="og:title" content="OpenAI兼容-Chat" />

<Tabs>
  <Tab title="华北2（北京）">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`

    HTTP 请求地址：`POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>

  <Tab title="新加坡">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`

    HTTP 请求地址：`POST https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>

  <Tab title="美国（弗吉尼亚）">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.us-east-1.maas.aliyuncs.com/compatible-mode/v1`

    HTTP 请求地址：`POST https://{WorkspaceId}.us-east-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>

  <Tab title="德国（法兰克福）">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.eu-central-1.maas.aliyuncs.com/compatible-mode/v1`

    HTTP 请求地址：`POST https://{WorkspaceId}.eu-central-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>

  <Tab title="日本（东京）">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1`

    HTTP 请求地址：`POST https://{WorkspaceId}.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>

  <Tab title="中国香港">
    SDK 调用配置的`base_url`：`https://{WorkspaceId}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1`
~~~~

## G01 · comparison · comparison

对比DeepSeek JSON Output与OpenAI Structured Outputs的Schema约束，分别给出依据。

判分要求：DeepSeek仅合法JSON，OpenAI支持Schema约束；两家分别引用，不混用参数

审阅：PASS。区分合法 JSON 与 Schema 约束，保留厂商边界及支持子集限制。

### 原始回答

**结论：两者对 Schema 的约束强度不同。** DeepSeek 的 JSON Output 只保证输出是合法 JSON 字符串，不保证严格匹配某个 Schema；OpenAI 的 Structured Outputs 则要求先设计 JSON Schema，并通过 `strict: true` 让输出遵循该 Schema（受其支持的 Schema 子集限制）。

**1. DeepSeek JSON Output 的 Schema 约束**
- 开启方式：`response_format` 设为 `{'type': 'json_object'}`。
- 约束性质：官方表述是“确保模型输出合法的 JSON 字符串”，即保证 JSON 语法合法，而非按某个 Schema 校验字段结构。
- 使用要求：system 或 user prompt 中必须含有 `json` 字样，并给出希望输出的 JSON 格式样例，以“指导”模型输出合法 JSON——这属于提示词引导，不是服务端 Schema 强制。
- 其他注意点：需合理设置 `max_tokens` 防止 JSON 被截断；该功能有概率返回空 content。
- 适用范围：DeepSeek API；据模型价格表，`deepseek-flash` 与 `deepseek-v4-pro` 均支持 Json Output。
- 补充区分：DeepSeek 另有 `strict` 模式（Beta），但那是针对 **Function 调用** 的 JSON Schema 严格遵循，需使用 `base_url="https://api.deepseek.com/beta"`，且 tools 中所有 function 都要设 `strict: true`，服务端会校验 Schema 并可能返回错误。这与 JSON Output 不是同一功能，不能混为一谈。

**2. OpenAI Structured Outputs 的 Schema 约束**
- 开启方式：`text: { format: { type: "json_schema", "strict": true, "schema": … } }`。
- 约束性质：必须先设计模型应遵循的 JSON Schema；官方对比表明确：Structured Outputs“Adheres to schema = Yes（见 supported schemas）”，而 JSON Mode 为“No”。
- 限制：Structured Outputs 支持 JSON Schema 的大部分能力，但部分特性因性能或技术原因不可用，需查阅其 supported schemas。
- 兼容模型：`gpt-4o-mini`、`gpt-4o-2024-08-06` 及之后版本。
- 与 JSON Mode 的区别：JSON Mode 只保证输出为合法 JSON（且存在需自行检测处理的边缘情况），不匹配 Schema；官方建议在适用时优先用 Structured Outputs。

**3. 对比要点**
| 维度 | DeepSeek JSON Output | OpenAI Structured Outputs |
|---|---|---|
| 是否保证合法 JSON | 是 | 是 |
| 是否强制遵循 Schema | 否，靠 prompt 样例引导 | 是（`strict: true` + `json_schema`，受支持子集限制） |
| 配置方式 | `response_format: {'type':'json_object'}` | `text.format: {type:"json_schema", strict:true, schema:…}` |
| 额外前提 | prompt 含 `json` 字样并给样例；注意 `max_tokens` 与空 content 风险 | 需先设计 Schema；部分 Schema 特性不可用 |

以上均为对应厂商文档中的通用规则说明，不代表任何具体账户或单次调用的实际状态。

来源#1: deepseek-json-output.md
来源#2: gpt-structured-outputs.md
来源#3: gpt-structured-outputs.md
来源#4: gpt-structured-outputs.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-tool-calling.md
来源#7: gpt-text.md

### 实际引用锚点

来源#1：`deepseek-json-output.md`，chunk=0，version=8ca3370a65d15df5b4e04f783542de05，HTTP=200

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

[同版本引用上下文]
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

- 在使用 JSON Output 功能时，API 有概率会返回空的 content。我们正在积极优化该问题，您可以尝试修改 prompt 以缓解此类问题。

## 样例代码

这里展示了使用 JSON Output 功能的完整 Python 代码：

```
import jsonfrom openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com",)system_prompt = """The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. EXAMPLE INPUT: Which is the highest mountain in the world? Mount Everest.EXAMPLE JSON OUTPUT:{    "question": "Which is the highest mountain in the world?",    "answer": "Mount Everest"}"""user_prompt = "Which is the longest river in the world? The Nile River."messages = [{"role": "system", "content": system_prompt},            {"role": "user", "content": user_prompt}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    response_format={        'type': 'json_object',    },)print(json.loads(response.choices[0].message.content))
```

模型将会输出：

```
{    "question": "Which is the longest river in the world?",    "answer": "The Nile River"}
```
~~~~

来源#2：`gpt-structured-outputs.md`，chunk=146，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
First you must design the JSON Schema that the model should be constrained to follow. See the [examples](https://developers.openai.com/api/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) for more details.

#### Tips for your JSON Schema

To maximize the quality of model generations, we recommend the following:

[同版本引用上下文]
First you must design the JSON Schema that the model should be constrained to follow. See the [examples](https://developers.openai.com/api/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) for more details.

#### Tips for your JSON Schema

To maximize the quality of model generations, we recommend the following:

- Name keys clearly and intuitively
- Create clear titles and descriptions for important keys in your structure
- Create and use evals to determine the structure that works best for your use case

## Step 2: Supply your schema in the API call

To use Structured Outputs, simply specify

```json
text: { format: { type: "json_schema", "strict": true, "schema": … } }
```

For example:
~~~~

来源#3：`gpt-structured-outputs.md`，chunk=30，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
|                                            | Structured Outputs                                                                                                             | JSON Mode                                  |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|

[同版本引用上下文]
|                                            | Structured Outputs                                                                                                             | JSON Mode                                  |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| **Outputs valid JSON**                     | Yes                                                                                                                            | Yes                                        |
| **Adheres to schema**                      | Yes (see [supported schemas](#supported-schemas))                                               | No                                         |
| **Compatible models**                      | `gpt-4o-mini`, `gpt-4o-2024-08-06`, and later                                                                                  | `gpt-3.5-turbo`, `gpt-4-*`, `gpt-4o-*`, and compatible GPT-5 models |
| **Enabling**                               | `text: { format: { type: "json_schema", "strict": true, "schema": ... } }`                                       | `text: { format: { type: "json_object" } }` |

## Examples

Chain of thought

### Chain of thought

You can ask the model to output an answer in a structured, step-by-step way, to guide the user through the solution.

  Structured Outputs for chain-of-thought math tutoring

```javascript
import OpenAI from "openai";
import { zodTextFormat } from "openai/helpers/zod";
import { z } from "zod";

const openai = new OpenAI();

const Step = z.object({
  explanation: z.string(),
  output: z.string(),
});
~~~~

来源#4：`gpt-structured-outputs.md`，chunk=284，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

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

[同版本引用上下文]
```json
{
    "type": "object",
    "properties": {
        "linked_list": {
            "$ref": "#/$defs/linked_list_node"
        }
    },
    "$defs": {
        "linked_list_node": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number"
                },
                "next": {
                    "anyOf": [
                        {
                            "$ref": "#/$defs/linked_list_node"
                        },
                        {
                            "type": "null"
                        }
                    ]
                }
            },
            "additionalProperties": false,
            "required": [
                "next",
                "value"
            ]
        }
    },
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

To turn on JSON mode with the Responses API you can set the `text.format` to `{ "type": "json_object" }`. If you are using function calling, JSON mode is always turned on.

Important notes:
~~~~

来源#5：`deepseek-models-pricing.md`，chunk=1，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

~~~~text
百万 tokens”为单位。Token 是模型用来表示自然语言文本的的最小单位，可以是一个词、一个数字或一个标点符号等。我们将根据模型输入和输出的总 token 数进行计量计费。

## 模型细节

| 模型 | deepseek-flash (1) | deepseek-v4-pro |  |  |
| --- | --- | --- | --- | --- |
| BASE URL (OpenAI 格式) | https://api.deepseek.com |  |  |  |
| BASE URL (Anthropic 格式) | https://api.deepseek.com/anthropic |  |  |  |
| 模型版本 | DeepSeek-V4.1-Flash-1017 | DeepSeek-V4-Pro-0813 |  |  |
| 思考模式 | 支持非思考与思考模式（默认） 切换方式详见 思考模式 |  |  |  |
| 上下文长度 | 1M |  |  |  |
| 输出长度 | 最大 384K |  |  |  |
| 功能 | Json Output | 支持 | 支持 |  |
| Tool Calls | 支持 | 支持 |  |  |
| Responses API | 支持 | 支持 |  |  |

[同版本引用上下文]
# DeepSeek API：模型与价格

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[模型 & 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 模型 & 价格

下表所列模型价格以“百万 tokens”为单位。Token 是模型用来表示自然语言文本的的最小单位，可以是一个词、一个数字或一个标点符号等。我们将根据模型输入和输出的总 token 数进行计量计费。

## 模型细节

| 模型 | deepseek-flash (1) | deepseek-v4-pro |  |  |
| --- | --- | --- | --- | --- |
| BASE URL (OpenAI 格式) | https://api.deepseek.com |  |  |  |
| BASE URL (Anthropic 格式) | https://api.deepseek.com/anthropic |  |  |  |
| 模型版本 | DeepSeek-V4.1-Flash-1017 | DeepSeek-V4-Pro-0813 |  |  |
| 思考模式 | 支持非思考与思考模式（默认） 切换方式详见 思考模式 |  |  |  |
| 上下文长度 | 1M |  |  |  |
| 输出长度 | 最大 384K |  |  |  |
| 功能 | Json Output | 支持 | 支持 |  |
| Tool Calls | 支持 | 支持 |  |  |
| Responses API | 支持 | 支持 |  |  |
| Anthropic API | 支持 | 支持 |  |  |
| 对话前缀续写（Beta） | 支持 | 支持 |  |  |
| FIM 补全（Beta） | 仅非思考模式支持 | 仅非思考模式支持 |  |  |
| 图像理解 | 支持 | 不支持 |  |  |
| 价格 (2) | 百万tokens输入 （缓存命中） | 空闲时段 | 0.02元 | 0.15元 |
| 高峰时段 | 0.04元 | 0.30元 |  |  |
| 百万tokens输入 （缓存未命中） | 空闲时段 | 1元 | 4.5元 |  |
| 高峰时段 | 2元 | 9.0元 |  |  |
| 百万tokens输出 | 空闲时段 | 4元 | 13.5元 |  |
| 高峰时段 | 8元 | 27.0元 |  |  |
| 并发限制 (3) | 2500 | 500 |  |  |

(1) 模型名请使用 `deepseek-flash`。旧模型名 `deepseek-v4-flash`、`deepseek-v4-flash-vision-exp` 仍可调用，但对应模型已下线，请求将由 DeepSeek-V4.1-Flash-1017 模型提供服务，并按 Flash 价格计费。

(2) 空闲时段价格为高峰时段价格的一半。北京时间周一至周五（不含中国法定节假日）9:00 - 12:00、14:00 - 18:00 为高峰时段；其余时段，包括周末及中国法定节假日全天均为空闲时段。

(3) 更多并发限制细节，请参考[限速与隔离](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit)。

## 网页搜索与抓取价格

Search 和 Fetch 是独立的 API，按请求次数计费。

| API | 计费单位 | 价格 |
| --- | --- | --- |
| Search | 每 1,000 次成功请求 | 5元 |
| Fetch | 每 1,000 次成功请求 | 5元 |
~~~~

来源#6：`deepseek-tool-calling.md`，chunk=6，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
JSON Schema 的格式要求，以确保模型输出的 Function 符合用户的定义。在思考与非思考模式下的工具调用，均可使用 `strict` 模式。

要使用 `strict` 模式，需要：

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能

- 在传入的 `tools` 列表中，所有 `function` 均需设置 `strict` 属性为 `true`

- 服务端会对用户传入的 Function 的 JSON Schema 进行校验，如不符合规范，或遇到服务端不支持的 JSON Schema 类型，将返回错误信息

以下是 `strict` 模式下 tool 的定义样例：

[同版本引用上下文]
- 模型：返回 function `get_weather({location: 'Hangzhou'})`

- 用户：调用 function `get_weather({location: 'Hangzhou'})`，并传给模型。

- 模型：返回自然语言，"The current temperature in Hangzhou is 24°C."

注：上述代码中 `get_weather` 函数功能需由用户提供，模型本身不执行具体函数。

## 思考模式

从 DeepSeek-V3.2 开始，API 支持了思考模式下的工具调用能力，详见[思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode#tool-calls)。

## 在对话中间插入工具调用

在部分 Agent 场景中，客户端需要把并非由模型生成的工具调用及其结果，动态插入到对话历史的中间。各 API 格式对此的支持情况不同：

- [Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)（`/messages`）与 [Responses API](https://api-docs.deepseek.com/zh-cn/guides/responses_api) 支持在对话中间插入工具调用消息，也支持在对话中间插入 `system` 消息；

- Chat Completion 接口不支持在对话中间插入工具调用，但支持在对话中间插入 `system` 消息；如需插入工具调用，请改用 Anthropic API 或 Responses API。

## `strict` 模式（Beta）

在 `strict` 模式下，模型在输出 Function 调用时会严格遵循 Function 的 JSON Schema 的格式要求，以确保模型输出的 Function 符合用户的定义。在思考与非思考模式下的工具调用，均可使用 `strict` 模式。

要使用 `strict` 模式，需要：

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能

- 在传入的 `tools` 列表中，所有 `function` 均需设置 `strict` 属性为 `true`

- 服务端会对用户传入的 Function 的 JSON Schema 进行校验，如不符合规范，或遇到服务端不支持的 JSON Schema 类型，将返回错误信息

以下是 `strict` 模式下 tool 的定义样例：

```
{    "type": "function",    "function": {        "name": "get_weather",        "strict": true,        "description": "Get weather of a location, the user should supply a location first.",        "parameters": {            "type": "object",            "properties": {                "location": {                    "type": "string",                    "description": "The city and state, e.g. San Francisco, CA"                }            },            "required": ["location"],            "additionalProperties": false        }    }}
```

### `strict` 模式支持的 JSON Schema 类型

- object

- string

- number

- integer

- boolean

- array
~~~~

来源#7：`gpt-text.md`，chunk=47，version=2f96fd65e2fb5f66ab164fb97fc9c821，HTTP=200

~~~~text
Use the Playground to develop and iterate on prompts.](https://platform.openai.com/chat/edit)

[Generate JSON data with Structured Outputs

      Ensure JSON data emitted from a model conforms to a JSON schema.](https://developers.openai.com/api/docs/guides/structured-outputs)

[Full API reference

      Check out all the options for text generation in the API reference.](https://developers.openai.com/api/reference/resources/responses)

[同版本引用上下文]
- Keep prompt builders in a small module near the feature they support.
- Use typed function arguments or schemas for dynamic values such as customer data, files, or task options.
- Pass the generated `instructions` and `input` directly to the [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create).
- Add representative fixtures, tests, and evaluation checks before changing production prompts.
- Roll out prompt changes through your deployment system, using feature flags or configuration when you need staged releases.

If your integration already calls a saved prompt with a prompt ID or version, use the [prompt object migration guide](https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object) to move that prompt into code.

## Next steps

Now that you know the basics of text inputs and outputs, you might want to check out one of these resources next.

[Build a prompt in the Playground

      Use the Playground to develop and iterate on prompts.](https://platform.openai.com/chat/edit)

[Generate JSON data with Structured Outputs

      Ensure JSON data emitted from a model conforms to a JSON schema.](https://developers.openai.com/api/docs/guides/structured-outputs)

[Full API reference

      Check out all the options for text generation in the API reference.](https://developers.openai.com/api/reference/resources/responses)
~~~~

## G02 · ambiguous · clarification

JSON结构化输出要设置什么参数才能保证Schema？

判分要求：确认厂商模型和接口；不提供通用跨厂商保证

审阅：PASS。缺少厂商、模型及接口时追问，没有承诺通用 Schema 保证。

### 原始回答

请先确认使用的厂商（DeepSeek、Qwen 或 OpenAI）、模型和接口类型；JSON/Schema 模式及 strict 参数的支持范围不同，不能给出适用于所有 API 的配置保证。

### 实际引用锚点

## D01 · demo · diagnosis

本地Demo API请求 req_chain_37_expired 返回401，请核查原因并说明修正后怎么复查。

判分要求：核验本次请求KEY_EXPIRED，不以当前ACTIVE状态否定历史过期；提示配置有效凭据并用新请求复查，不声称已恢复

审阅：PASS。基于 Demo 调用时证据识别过期 Key；要求修正后新请求复查。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

请求 req_chain_37_expired 在 2026-10-19T20:43:29.682849Z 返回 HTTP 401；该记录只说明当时的事件。

请求时观测支持的候选原因：Key 在请求时已过期。

建议：由拥有者检查有效期并配置有效凭据，随后发送新请求。

下一步：由拥有者检查有效期并配置有效凭据，随后发送新请求；完成后提供新请求号复查

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-batch.md
来源#2: qwen-batch.md
来源#3: qwen-api-key.md
来源#4: gpt-overview.md
来源#5: qwen-api-key.md
来源#6: qwen-batch.md

### 实际引用锚点

来源#1：`qwen-batch.md`，chunk=156，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

[同版本引用上下文]
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

    ```json expandable
    {
      "id": "batch_abc123",
      "object": "batch",
      "endpoint": "/v1/chat/completions",
      "errors": null,
      "input_file_id": "file-abc123",
      "completion_window": "24h",
      "status": "completed",
      "output_file_id": "file-batch_output-xyz789",
      "error_file_id": "file-batch_error-xyz789",
      "created_at": 1711402400,
      "in_progress_at": 1711402450,
      "expires_at": 1711488800,
      "finalizing_at": 1711405000,
      "completed_at": 1711406000,
      "failed_at": null,
      "expired_at": null,
      "cancelling_at": null,
      "cancelled_at": null,
      "request_counts": {
        "total": 100,
        "completed": 95,
        "failed": 5
      },
      "metadata": {
        "customer_id": "user_123456789",
        "batch_description": "Nightly eval job"
      }
    }
    ```

    返回的JSON对象包含 Batch 任务完整信息，包括任务状态、结果文件 ID、请求统计等。各字段说明见下表。
~~~~

来源#2：`qwen-batch.md`，chunk=89，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
确保 `model` 和 `url` 字段正确。

### 2. 修改快速开始的代码 <span id="9e8d214ec6w42" /> <span id="c9d67eab84owy" />

1. 输入文件路径更改为您的文件名
2. 将 endpoint 参数值修改为与输入文件中URL字段一致的值

### 3. 运行代码并等待结果 <span id="38f1a37efdb21" /> <span id="d180ad81a8g6y" />

任务完成后，成功请求的结果保存在本地 result.jsonl 文件中。如有请求失败，错误详情保存在 error.jsonl 文件中。

- 成功结果（`output_file_id`）：每一行对应一个成功的原始请求，包含 `custom_id` 和 `response`。

[同版本引用上下文]
<table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "50.78%" }} /><col style={{ width: "49.22%" }} /></colgroup><thead><tr><th><p><strong>模型类型</strong></p></th><th><p><strong>url</strong></p></th></tr></thead><tbody><tr><td><p>文本生成/多模态模型</p></td><td><p><code>/v1/chat/completions</code></p></td></tr><tr><td><p>向量模型</p></td><td><p><code>/v1/embeddings</code></p></td></tr></tbody></table>
- 或使用上方的“JSONL 批量生成工具”为正式任务生成一个新的文件。关键是确保 `model` 和 `url` 字段正确。

### 2. 修改快速开始的代码 <span id="9e8d214ec6w42" /> <span id="c9d67eab84owy" />

1. 输入文件路径更改为您的文件名
2. 将 endpoint 参数值修改为与输入文件中URL字段一致的值

### 3. 运行代码并等待结果 <span id="38f1a37efdb21" /> <span id="d180ad81a8g6y" />

任务完成后，成功请求的结果保存在本地 result.jsonl 文件中。如有请求失败，错误详情保存在 error.jsonl 文件中。

- 成功结果（`output_file_id`）：每一行对应一个成功的原始请求，包含 `custom_id` 和 `response`。

```json
{"id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","custom_id":"req-001","response":{"status_code":200,"request_id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","body":{"created":1768306034,"usage":{"completion_tokens":654,"prompt_tokens":14,"total_tokens":668},"model":"qwen-plus","id":"chatcmpl-3a5c39d5-3981-4e4c-97f2-e0e821893f03","choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"你好！杭州西湖是中国著名的风景名胜区，位于浙江省杭州市西部，因此得名“西湖”。它是中国十大风景名胜之一，也是世界文化遗产（2011年被联合国教科文组织列入《世界遗产名录》），以其秀丽的自然风光与深厚的人文底蕴闻名于世。\n\n### 一、自然景观\n西湖三面环山，一面邻城，湖面面积约6.39平方公里，形似如意，碧波荡漾。湖中被孤山、白堤、苏堤、杨公堤等自然或人工分隔成多个水域，形成“一山二塔三岛三堤”的格局。\n\n主要景点包括：\n- **苏堤春晓**：北宋大文豪苏东坡任杭州知州时主持疏浚西湖，用挖出的淤泥堆筑成堤，后人称为“苏堤”。春天桃红柳绿，景色如画。\n- **断桥残雪**：位于白堤东端，是白蛇传中“断桥相会”的发生地，冬日雪后银装素裹，尤为著名。\n- **雷峰夕照**：雷峰塔在夕阳映照下金光熠熠，曾是“西湖十景”之一。\n- **三潭印月**：湖中小瀛洲上的三座石塔，中秋夜可在塔内点灯，月影、灯光、湖光交相辉映。\n- **平湖秋月**：位于白堤西端，是观赏湖上明月的绝佳地点。\n- **花港观鱼**：以赏花和观鱼著称，园内牡丹、锦鲤相映成趣。
~~~~

来源#3：`qwen-api-key.md`，chunk=25，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
务空间的API Key调用。

如需在业务空间之外做更细粒度的控制，可在创建或编辑 API Key 时将<strong>权限</strong>切换为<strong>自定义</strong>，配置：

- <strong>IP 白名单规则</strong>：默认放通全部 IPv4，完整规则参见[时效性与限制](#apikey-limits)。
- <strong>访问模型范围</strong>：开关开启后，该 API Key 仅能调用已勾选的模型（限于该业务空间已授权的模型，数量限制参见[时效性与限制](#apikey-limits)）。

### 环境变量已设置，为何代码仍提示找不到 API Key？ <span id="a486eb2dc2p5y" />

具体原因如下：

- 情况一：<strong>没有设置永久性环境变量</strong>。临时环境变量只在当前终端会话中有效，对于已经启动的 IDE 或其他应用程序并不会生效。请参考本文中设置永久性环境变量的方法。
- 情况二：<strong>没有重启IDE、命令行工具或应用</strong>。

[同版本引用上下文]
- <strong>API Key 数量</strong>：账号+地域维度最多 50 个，不按业务空间限制；单个主账号最多 20 个业务空间（含默认业务空间）。
- <strong>自定义权限可选模型</strong>：最多 30 个，限于该业务空间已授权的模型。
- <strong>IP 白名单</strong>：最多 20 个地址或网段；IPv6 仅华北2（北京）地域支持，美国（弗吉尼亚）地域仅支持 IPv4；批量输入用英文逗号隔开。
- <strong>临时 API Key</strong>：最长 1800 秒。

## API 调用 <span id="4dd13345796cg" /> <span id="68bf80d8faprx" />

请访问[文本生成](/zh/model-studio/qwen-api-reference)以及更多模型的 API 参考。

OpenAI SDK 支持的模型，请参考[OpenAI 兼容](/zh/model-studio/toolkits-and-frameworks)。

## 常见问题 <span id="e6a57c054bfzy" /> <span id="4ed8cb6687hz6" />

### 无法创建 API Key？ <span id="9603b994a7nx6" />

API Key 的创建需使用[超级管理员](/zh/model-studio/permission-management-overview#982297bd47p3i)或[业务空间管理员](/zh/model-studio/permission-management-overview#c82f37c2033vw)操作。

### 如何管理 API Key 的权限？ <span id="44eed06516tbh" />

API Key 的调用权限完全由其<strong>归属业务空间</strong>决定。<strong>同一空间内的 API Key 权限相同</strong>，无需为不同模型（如文生文、文生图、语音合成）创建不同的 API Key。

- <strong>默认业务空间下的 API Key：</strong>可调用所有[标准模型](/zh/model-studio/models)，以及默认业务空间内的[应用](/zh/model-studio/application-introduction)。
- <strong>子业务空间下的 API Key：</strong>可调用该子业务空间已获得[模型调用授权](/zh/model-studio/permission-management-overview)的标准模型，以及该业务空间内的应用。

<strong>调用在阿里云百炼</strong>[<strong>调优后的模型</strong>](/zh/model-studio/model-training-overview)<strong>：</strong>此类模型部署成功后，仅能用其所在业务空间的API Key调用。

如需在业务空间之外做更细粒度的控制，可在创建或编辑 API Key 时将<strong>权限</strong>切换为<strong>自定义</strong>，配置：

- <strong>IP 白名单规则</strong>：默认放通全部 IPv4，完整规则参见[时效性与限制](#apikey-limits)。
- <strong>访问模型范围</strong>：开关开启后，该 API Key 仅能调用已勾选的模型（限于该业务空间已授权的模型，数量限制参见[时效性与限制](#apikey-limits)）。

### 环境变量已设置，为何代码仍提示找不到 API Key？ <span id="a486eb2dc2p5y" />

具体原因如下：

- 情况一：<strong>没有设置永久性环境变量</strong>。临时环境变量只在当前终端会话中有效，对于已经启动的 IDE 或其他应用程序并不会生效。请参考本文中设置永久性环境变量的方法。
- 情况二：<strong>没有重启IDE、命令行工具或应用</strong>。
~~~~

来源#4：`gpt-overview.md`，chunk=0，version=9feabad921a156d9a4741c5a7765bf77，HTTP=200

~~~~text
# GPT / OpenAI API：接入认证与请求追踪

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# API Overview

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：接入认证与请求追踪

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# API Overview

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

Use this reference to look up OpenAI API endpoints, request and response
schemas, streaming events, client library methods, and shared behavior such as
authentication, errors, rate limits, and request IDs.

## Start here

1. Choose the API surface for your application:
   - [Responses](https://developers.openai.com/api/reference/responses/overview) for direct model requests, tool use, audio, image, and text inputs, and stateful interactions.
   - [Realtime API](https://developers.openai.com/api/docs/guides/realtime) for low-latency voice or audio sessions over WebRTC, WebSocket, or SIP. Use the [client events](https://developers.openai.com/api/reference/resources/realtime/client-events) and [server events](https://developers.openai.com/api/reference/resources/realtime/server-events) references while building sessions.
   - [Administration](https://developers.openai.com/api/reference/administration/overview) for organization workflows such as users, invites, projects, API keys, and audit logs.
2. Create credentials. Use a standard [API key](https://platform.openai.com/settings/organization/api-keys) for application requests, an [Admin API key](https://platform.openai.com/settings/organization/admin-keys) for Administration endpoints, or [workload identity federation](https://developers.openai.com/api/docs/guides/workload-identity-federation) for short-lived access tokens.
~~~~

来源#5：`qwen-api-key.md`，chunk=1，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

1. 前往阿里云百炼[API Key](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)页面，在右上角选择<strong>地域</strong>。每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>，各地域的 API Key 入口和接入域名请参见[各地域接入信息](/zh/model-studio/regions#h2_cc92e61c)。

2. 若已有可用 API Key，直接在列表中复制。若需创建，单击<strong>创建 API Key</strong>，在弹窗中配置以下选项后单击<strong>确定</strong>（若无法创建，请联系超级管理员或业务空间管理员）：

[同版本引用上下文]
# Qwen / 阿里云百炼：获取 API Key

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[获取与配置 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 获取与配置 API Key

> 在控制台获取或创建 API Key 后，您将使用它来安全地调用百炼的模型服务。

<meta property="og:title" content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

1. 前往阿里云百炼[API Key](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)页面，在右上角选择<strong>地域</strong>。每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>，各地域的 API Key 入口和接入域名请参见[各地域接入信息](/zh/model-studio/regions#h2_cc92e61c)。

2. 若已有可用 API Key，直接在列表中复制。若需创建，单击<strong>创建 API Key</strong>，在弹窗中配置以下选项后单击<strong>确定</strong>（若无法创建，请联系超级管理员或业务空间管理员）：

   - <strong>归属账号</strong>：默认选择<strong>阿里云账号（主账号）</strong>（账号名通常为一串数字）。如需为团队成员或应用创建权责独立的 API Key 并结合业务空间做精细化模型访问控制，可选择 [RAM 用户](https://help.aliyun.com/zh/ram/user-guide/overview-of-ram-users)（账号格式 `username@<AccountAlias>.onaliyun.com`）。
   - <strong>归属业务空间</strong>：默认选择<strong>默认业务空间</strong>（数量上限与主账号配额见[时效性与限制](#apikey-limits)）。如需权限隔离、精细化模型访问控制或独立成本核算，请选择非默认业务空间，参见[业务空间管理](/zh/model-studio/permission-management-overview)。
   - <strong>权限</strong>：建议选择<strong>全部</strong>。如需精细控制，可选择<strong>自定义</strong>，配置可访问 IP 和可访问模型范围（数量限制见[时效性与限制](#apikey-limits)）。

3. 点击新创建的 API Key 旁的<Image src="https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/8412544571/p994217.png" alt="image" className="inline" noZoom />图标复制 API Key。

## 配置 API Key 到环境变量 <span id="20b17d4430qvt" /> <span id="6a82f1a968bhf" />

- <strong>方式一：在</strong>[<strong>第三方工具</strong>](/zh/model-studio/use-chat-client-or-development-tool)<strong>中进行配置</strong>

  如果在 Chatbox 等工具或平台中调用模型，您可能需要输入三个信息：

  - 本文获取的 API Key
  - Base URL：
~~~~

来源#6：`qwen-batch.md`，chunk=70，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
- <strong>唯一标识</strong>：每个请求必须包含文件内唯一的 custom\_id 字段，用于匹配请求与结果

<strong>场景1：文本对话</strong>

示例文件内容：

```json
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
```

[同版本引用上下文]
```json
{"id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","custom_id":"1","response":{"status_code":200,"request_id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-bca7295b-67c3-4b1f-8239-d78323bb669f","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
{"id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","custom_id":"2","response":{"status_code":200,"request_id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-1e32a8ba-2b69-4dc4-be42-e2897eac9e84","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
```

## 执行正式任务 <span id="bad4ef1522g5k" /> <span id="759dd0eccesua" />

### 输入文件要求 <span id="0214fa4f9dxb3" /> <span id="bbf6655574dbn" />

- <strong>格式</strong>：UTF-8 编码的 JSONL（每行一个独立JSON对象）
- <strong>规模限制</strong>：单文件最多 50,000 个请求，且不超过 500 MB
- <strong>单行限制</strong>：每个JSON对象不超过 6 MB，且不超过模型上下文长度
- <strong>一致性要求</strong>：同一文件内所有请求须使用相同的模型及思考模式（如适用）
- <strong>唯一标识</strong>：每个请求必须包含文件内唯一的 custom\_id 字段，用于匹配请求与结果

<strong>场景1：文本对话</strong>

示例文件内容：

```json
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
```
~~~~

## D02 · demo · diagnosis

我已配置有效凭据，新请求 req_chain_37_fixed_{phase} 返回200，请复查刚才的401是否已解决。

判分要求：同一会话复查新请求200；根据新证据确认已解决，保留旧请求历史原因

审阅：PASS。同一诊断的新请求 200，RESOLVED 仅限该应用与接口；不扩大到账户整体。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

复查请求 req_chain_37_fixed_baseline_v2 返回 HTTP 200，已确认该应用和接口的新请求范围内恢复。

这不代表所有接口或账户整体均已恢复，也不能证明某个处理动作的因果关系。

下一步：新请求在同一应用和接口范围内已成功；这不代表所有接口或账户状态均已恢复

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-batch.md
来源#2: qwen-api-key.md
来源#3: qwen-batch.md
来源#4: qwen-batch.md
来源#5: qwen-api-key.md
来源#6: qwen-api-key.md
来源#7: qwen-errors.md
来源#8: qwen-errors.md
来源#9: deepseek-errors.md
来源#10: qwen-errors.md
来源#11: qwen-streaming.md
来源#12: qwen-streaming.md
来源#13: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-batch.md`，chunk=156，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

[同版本引用上下文]
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

    ```json expandable
    {
      "id": "batch_abc123",
      "object": "batch",
      "endpoint": "/v1/chat/completions",
      "errors": null,
      "input_file_id": "file-abc123",
      "completion_window": "24h",
      "status": "completed",
      "output_file_id": "file-batch_output-xyz789",
      "error_file_id": "file-batch_error-xyz789",
      "created_at": 1711402400,
      "in_progress_at": 1711402450,
      "expires_at": 1711488800,
      "finalizing_at": 1711405000,
      "completed_at": 1711406000,
      "failed_at": null,
      "expired_at": null,
      "cancelling_at": null,
      "cancelled_at": null,
      "request_counts": {
        "total": 100,
        "completed": 95,
        "failed": 5
      },
      "metadata": {
        "customer_id": "user_123456789",
        "batch_description": "Nightly eval job"
      }
    }
    ```

    返回的JSON对象包含 Batch 任务完整信息，包括任务状态、结果文件 ID、请求统计等。各字段说明见下表。
~~~~

来源#2：`qwen-api-key.md`，chunk=25，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
务空间的API Key调用。

如需在业务空间之外做更细粒度的控制，可在创建或编辑 API Key 时将<strong>权限</strong>切换为<strong>自定义</strong>，配置：

- <strong>IP 白名单规则</strong>：默认放通全部 IPv4，完整规则参见[时效性与限制](#apikey-limits)。
- <strong>访问模型范围</strong>：开关开启后，该 API Key 仅能调用已勾选的模型（限于该业务空间已授权的模型，数量限制参见[时效性与限制](#apikey-limits)）。

### 环境变量已设置，为何代码仍提示找不到 API Key？ <span id="a486eb2dc2p5y" />

具体原因如下：

- 情况一：<strong>没有设置永久性环境变量</strong>。临时环境变量只在当前终端会话中有效，对于已经启动的 IDE 或其他应用程序并不会生效。请参考本文中设置永久性环境变量的方法。
- 情况二：<strong>没有重启IDE、命令行工具或应用</strong>。

[同版本引用上下文]
- <strong>API Key 数量</strong>：账号+地域维度最多 50 个，不按业务空间限制；单个主账号最多 20 个业务空间（含默认业务空间）。
- <strong>自定义权限可选模型</strong>：最多 30 个，限于该业务空间已授权的模型。
- <strong>IP 白名单</strong>：最多 20 个地址或网段；IPv6 仅华北2（北京）地域支持，美国（弗吉尼亚）地域仅支持 IPv4；批量输入用英文逗号隔开。
- <strong>临时 API Key</strong>：最长 1800 秒。

## API 调用 <span id="4dd13345796cg" /> <span id="68bf80d8faprx" />

请访问[文本生成](/zh/model-studio/qwen-api-reference)以及更多模型的 API 参考。

OpenAI SDK 支持的模型，请参考[OpenAI 兼容](/zh/model-studio/toolkits-and-frameworks)。

## 常见问题 <span id="e6a57c054bfzy" /> <span id="4ed8cb6687hz6" />

### 无法创建 API Key？ <span id="9603b994a7nx6" />

API Key 的创建需使用[超级管理员](/zh/model-studio/permission-management-overview#982297bd47p3i)或[业务空间管理员](/zh/model-studio/permission-management-overview#c82f37c2033vw)操作。

### 如何管理 API Key 的权限？ <span id="44eed06516tbh" />

API Key 的调用权限完全由其<strong>归属业务空间</strong>决定。<strong>同一空间内的 API Key 权限相同</strong>，无需为不同模型（如文生文、文生图、语音合成）创建不同的 API Key。

- <strong>默认业务空间下的 API Key：</strong>可调用所有[标准模型](/zh/model-studio/models)，以及默认业务空间内的[应用](/zh/model-studio/application-introduction)。
- <strong>子业务空间下的 API Key：</strong>可调用该子业务空间已获得[模型调用授权](/zh/model-studio/permission-management-overview)的标准模型，以及该业务空间内的应用。

<strong>调用在阿里云百炼</strong>[<strong>调优后的模型</strong>](/zh/model-studio/model-training-overview)<strong>：</strong>此类模型部署成功后，仅能用其所在业务空间的API Key调用。

如需在业务空间之外做更细粒度的控制，可在创建或编辑 API Key 时将<strong>权限</strong>切换为<strong>自定义</strong>，配置：

- <strong>IP 白名单规则</strong>：默认放通全部 IPv4，完整规则参见[时效性与限制](#apikey-limits)。
- <strong>访问模型范围</strong>：开关开启后，该 API Key 仅能调用已勾选的模型（限于该业务空间已授权的模型，数量限制参见[时效性与限制](#apikey-limits)）。

### 环境变量已设置，为何代码仍提示找不到 API Key？ <span id="a486eb2dc2p5y" />

具体原因如下：

- 情况一：<strong>没有设置永久性环境变量</strong>。临时环境变量只在当前终端会话中有效，对于已经启动的 IDE 或其他应用程序并不会生效。请参考本文中设置永久性环境变量的方法。
- 情况二：<strong>没有重启IDE、命令行工具或应用</strong>。
~~~~

来源#3：`qwen-batch.md`，chunk=90，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
求失败，错误详情保存在 error.jsonl 文件中。

- 成功结果（`output_file_id`）：每一行对应一个成功的原始请求，包含 `custom_id` 和 `response`。

```json
{"id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","custom_id":"req-001","response":{"status_code":200,"request_id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","body":{"created":1768306034,"usage":{"completion_tokens":654,"prompt_tokens":14,"total_tokens":668},"model":"qwen-plus","id":"chatcmpl-3a5c39d5-3981-4e4c-97f2-e0e821893f03","choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"你好！杭州西湖是中国著名的风景名胜区，位于浙江省杭州市西部，因此得名“西湖”。

[同版本引用上下文]
<table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "50.78%" }} /><col style={{ width: "49.22%" }} /></colgroup><thead><tr><th><p><strong>模型类型</strong></p></th><th><p><strong>url</strong></p></th></tr></thead><tbody><tr><td><p>文本生成/多模态模型</p></td><td><p><code>/v1/chat/completions</code></p></td></tr><tr><td><p>向量模型</p></td><td><p><code>/v1/embeddings</code></p></td></tr></tbody></table>
- 或使用上方的“JSONL 批量生成工具”为正式任务生成一个新的文件。关键是确保 `model` 和 `url` 字段正确。

### 2. 修改快速开始的代码 <span id="9e8d214ec6w42" /> <span id="c9d67eab84owy" />

1. 输入文件路径更改为您的文件名
2. 将 endpoint 参数值修改为与输入文件中URL字段一致的值

### 3. 运行代码并等待结果 <span id="38f1a37efdb21" /> <span id="d180ad81a8g6y" />

任务完成后，成功请求的结果保存在本地 result.jsonl 文件中。如有请求失败，错误详情保存在 error.jsonl 文件中。

- 成功结果（`output_file_id`）：每一行对应一个成功的原始请求，包含 `custom_id` 和 `response`。

```json
{"id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","custom_id":"req-001","response":{"status_code":200,"request_id":"3a5c39d5-3981-4e4c-97f2-e0e821893f03","body":{"created":1768306034,"usage":{"completion_tokens":654,"prompt_tokens":14,"total_tokens":668},"model":"qwen-plus","id":"chatcmpl-3a5c39d5-3981-4e4c-97f2-e0e821893f03","choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"你好！杭州西湖是中国著名的风景名胜区，位于浙江省杭州市西部，因此得名“西湖”。它是中国十大风景名胜之一，也是世界文化遗产（2011年被联合国教科文组织列入《世界遗产名录》），以其秀丽的自然风光与深厚的人文底蕴闻名于世。\n\n### 一、自然景观\n西湖三面环山，一面邻城，湖面面积约6.39平方公里，形似如意，碧波荡漾。湖中被孤山、白堤、苏堤、杨公堤等自然或人工分隔成多个水域，形成“一山二塔三岛三堤”的格局。\n\n主要景点包括：\n- **苏堤春晓**：北宋大文豪苏东坡任杭州知州时主持疏浚西湖，用挖出的淤泥堆筑成堤，后人称为“苏堤”。春天桃红柳绿，景色如画。\n- **断桥残雪**：位于白堤东端，是白蛇传中“断桥相会”的发生地，冬日雪后银装素裹，尤为著名。\n- **雷峰夕照**：雷峰塔在夕阳映照下金光熠熠，曾是“西湖十景”之一。\n- **三潭印月**：湖中小瀛洲上的三座石塔，中秋夜可在塔内点灯，月影、灯光、湖光交相辉映。\n- **平湖秋月**：位于白堤西端，是观赏湖上明月的绝佳地点。\n- **花港观鱼**：以赏花和观鱼著称，园内牡丹、锦鲤相映成趣。
~~~~

来源#4：`qwen-batch.md`，chunk=6，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
`qwen3.7`、`qwen3.6`和`qwen3.5` 系列模型默认开启思考模式。建议使用混合思考模型时，显式设置`enable_thinking`参数（`true`开启/`false`关闭）。
  - 在 JSONL 请求体中，`enable_thinking` 为 `body` 的顶层参数，须与 `model` 同级传入，不能放在 `extra_body` 中。
</Tip>

## 快速开始 <span id="abe0ee0bfd5dc" /> <span id="b056ab78e5blg" />

在处理正式任务前，使用测试模型`batch-test-model`进行全链路闭环测试。该模型跳过推理过程，直接返回固定的成功响应，用于验证API调用链路和数据格式是否正确。

<Note>
  <strong>测试模型（batch-test-model）的限制：</strong>

[同版本引用上下文]
- [图像与视频理解](/zh/model-studio/vision)：qwen3.8-max、qwen3.8-flash、qwen3.7-plus、qwen3.6-plus、qwen3.7-flash、qwen3.6-flash、qwen3.5-plus、qwen3.5-flash、qwen3-vl-plus
      - [文字提取](/zh/model-studio/qwen-vl-ocr)：qwen-vl-ocr
      - [全模态](/zh/model-studio/qwen-omni)：qwen3.5-omni-plus
    - [<strong>向量模型</strong>](https://help.aliyun.com/zh/model-studio/user-guide/embedding)<strong>：</strong>text-embedding-v1、text-embedding-v2、text-embedding-v3、text-embedding-v4、qwen3.7-text-embedding、qwen3.7-text-embedding-flash
  </Tab>

  <Tab title="新加坡">
    <strong>支持的模型</strong>：qwen3.7-plus、qwen-max、qwen-plus。
  </Tab>
</Tabs>

<Tip>
  - 在Batch 场景下，`qwen3.8-max`、`qwen3.8-flash`、`qwen3.7-max`、`qwen3.7-plus`、`qwen3.6-plus`、`qwen3.7-flash`、`qwen3.6-flash`、`qwen3.5-plus`、`qwen3.5-flash`和`qwen3.5-omni-plus`单次请求的上下文 Token 数最大支持 256K，`qwen3.5-omni-plus`不支持语音输出。
  - 部分模型支持思考模式，开启后会产生思考`tokens`导致成本增加。
  - `qwen3.8`、`qwen3.7`、`qwen3.6`和`qwen3.5` 系列模型默认开启思考模式。建议使用混合思考模型时，显式设置`enable_thinking`参数（`true`开启/`false`关闭）。
  - 在 JSONL 请求体中，`enable_thinking` 为 `body` 的顶层参数，须与 `model` 同级传入，不能放在 `extra_body` 中。
</Tip>

## 快速开始 <span id="abe0ee0bfd5dc" /> <span id="b056ab78e5blg" />

在处理正式任务前，使用测试模型`batch-test-model`进行全链路闭环测试。该模型跳过推理过程，直接返回固定的成功响应，用于验证API调用链路和数据格式是否正确。

<Note>
  <strong>测试模型（batch-test-model）的限制：</strong>

  - 测试文件需满足[输入文件要求](/zh/model-studio/batch-interfaces-compatible-with-openai#0214fa4f9dxb3)，且文件大小不超过 <strong>1 MB</strong>，行数不超过<strong>100行</strong>。
  - 并发限制：最大并行任务数 <strong>2 个</strong>。
  - 费用：测试模型不产生模型推理费用。
</Note>

### 第 1 步：准备输入文件 <span id="a687b7c50ej0t" /> <span id="eb771197c0u9g" />

准备一个名为[test\_model.jsonl](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250403/ilveat/test_model.jsonl)的文件，内容如下：
~~~~

来源#5：`qwen-api-key.md`，chunk=13，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
```powershell
          Write-Host "百炼 API Key 永久配置为：$($env:DASHSCOPE_API_KEY.Substring(0, [Math]::Min(10, $env:DASHSCOPE_API_KEY.Length)))*********"
          ```
        </Tab>

        <Tab title="CMD">
          <Tabs>
            <Tab title="添加永久性环境变量">
              如果您希望API Key环境变量在当前用户的所有新会话中生效，可以按如下操作。

              1. 在CMD中运行以下命令。

              ```bash
              setx DASHSCOPE_API_KEY "<YOUR_API_KEY>"
              ```

              2. 打开一个新的CMD窗口。
              3. 在新的CMD窗口运行以下命令，检查环境变量是否生效。

[同版本引用上下文]
```powershell
          Write-Host "百炼 API Key 永久配置为：$($env:DASHSCOPE_API_KEY.Substring(0, [Math]::Min(10, $env:DASHSCOPE_API_KEY.Length)))*********"
          ```
        </Tab>

        <Tab title="CMD">
          <Tabs>
            <Tab title="添加永久性环境变量">
              如果您希望API Key环境变量在当前用户的所有新会话中生效，可以按如下操作。

              1. 在CMD中运行以下命令。

              ```bash
              setx DASHSCOPE_API_KEY "<YOUR_API_KEY>"
              ```

              2. 打开一个新的CMD窗口。
              3. 在新的CMD窗口运行以下命令，检查环境变量是否生效。

              ```bash
              echo 百炼 API Key 永久配置为：%DASHSCOPE_API_KEY:~0,10%*********
              ```
            </Tab>

            <Tab title="添加临时性环境变量">
              如果您仅希望在当前会话中使用该环境变量，可以在CMD中运行以下命令。

              ```bash
              set "DASHSCOPE_API_KEY=<YOUR_API_KEY>"
              ```

              您可以在当前会话运行以下命令检查环境变量是否生效。

              ```bash
              echo 当前会话百炼 API Key 配置为：%DASHSCOPE_API_KEY:~0,10%*********
              ```
            </Tab>
          </Tabs>
        </Tab>

        <Tab title="PowerShell">
          <Tabs>
            <Tab title="添加永久性环境变量">
              如果您希望API Key环境变量在当前用户的所有新会话中生效，可以按如下操作。

              1. 在PowerShell中运行以下命令。

              ```powershell height="62"
              [Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "<YOUR_API_KEY>", [EnvironmentVariableTarget]::User)
              ```

              2. 打开一个新的PowerShell窗口。
              3. 在新的PowerShell窗口运行以下命令，检查环境变量是否生效。

              ```powershell
              Write-Host "百炼 API Key 永久配置为：$($env:DASHSCOPE_API_KEY.Substring(0, [Math]::Min(10, $env:DASHSCOPE_API_KEY.Length)))*********"
              ```
            </Tab>

            <Tab title="添加临时性环境变量">
              如果您仅希望在当前会话中使用该环境变量，可以在PowerShell中运行以下命令。
~~~~

来源#6：`qwen-api-key.md`，chunk=12，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
g>变量值</strong>填入您的DashScope API Key。
          3. 依次单击三个窗口的<strong>确定</strong>，关闭系统属性配置页面，完成环境变量配置。
          4. 打开CMD（命令提示符）窗口或Windows PowerShell窗口，执行如下命令检查环境变量是否生效。

             - CMD查询命令：

          ```bash
          echo 百炼 API Key 永久配置为：%DASHSCOPE_API_KEY:~0,10%*********
          ```

          - Windows PowerShell查询命令：

[同版本引用上下文]
```bash
          sudo systemctl daemon-reload
          sudo systemctl restart your-app
          ```
        </Tab>
      </Tabs>
    </Tab>

    <Tab title="macOS系统">
      <Tabs>
        <Tab title="添加永久性环境变量">
          将环境变量设置追加到`~/.bash_profile`或`~/.zshrc`文件中。

          ```bash
          VAR_VALUE="<YOUR_API_KEY>"; \
          echo "export DASHSCOPE_API_KEY='$VAR_VALUE'" >> ~/.zshrc 2>/dev/null
          echo "export DASHSCOPE_API_KEY='$VAR_VALUE'" >> ~/.bash_profile 2>/dev/null
          source ~/."${SHELL##*/}rc" 2>/dev/null
          echo "百炼 API Key 永久配置为：${DASHSCOPE_API_KEY:0:10}*********"
          ```
        </Tab>

        <Tab title="添加临时性环境变量">
          ```bash
          export DASHSCOPE_API_KEY='<YOUR_API_KEY>'
          echo "当前会话百炼 API Key 配置为：${DASHSCOPE_API_KEY:0:10}*********"
          ```
        </Tab>
      </Tabs>
    </Tab>

    <Tab title="Windows系统">
      在Windows系统中，您可以通过系统属性、CMD或PowerShell配置环境变量。

      <Tabs>
        <Tab title="系统属性">
          系统属性方式注意事项：

          - 环境变量永久生效。
          - 修改系统环境变量需具备管理员权限。
          - 配置后不会立即影响已经打开的命令窗口、IDE或其他正在运行的应用程序，需重启这些程序或打开新的命令行使环境变量生效。

          1. 在Windows系统桌面中按`Win+Q`键，在搜索框中搜索<strong>编辑系统环境变量</strong>，单击打开<strong>系统属性</strong>界面。
          2. 在<strong>系统属性</strong>窗口，单击<strong>环境变量</strong>，然后在<strong>系统变量</strong>区域下单击<strong>新建</strong>，<strong>变量名</strong>填入`DASHSCOPE_API_KEY`，<strong>变量值</strong>填入您的DashScope API Key。
          3. 依次单击三个窗口的<strong>确定</strong>，关闭系统属性配置页面，完成环境变量配置。
          4. 打开CMD（命令提示符）窗口或Windows PowerShell窗口，执行如下命令检查环境变量是否生效。

             - CMD查询命令：

          ```bash
          echo 百炼 API Key 永久配置为：%DASHSCOPE_API_KEY:~0,10%*********
          ```

          - Windows PowerShell查询命令：
~~~~

来源#7：`qwen-errors.md`，chunk=138，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
方案：</strong> 内容合规检查，请检查输入，确保不包含引发侵权风险的内容。

## 400-UnsupportedOperation <span id="d91dc0bf42k4t" />

### The operation is unsupported on the referee object. <span id="2761c10d0aond" />

<strong>原因：</strong> 关联的对象不支持该操作。

<strong>解决方案：</strong> 请检查操作对象和操作类型是否匹配。

### The fine-tune job can not be deleted because it is succeeded,failed or canceled. <span id="55b762964bdft" />

<strong>原因：</strong> 无法删除该微调任务，因为其状态已是“成功”、“失败”或“已取消”。

<strong>解决方案：</strong> 只有处于特定状态的任务才能被删除，请勿删除已终结状态的任务。

## 400-CustomRoleBlocked <span id="46a93eb6dfugb" />

[同版本引用上下文]
### Role must be user or assistant and Content length must be greater than 0. <span id="35c9c8e907hba" />

<strong>原因：</strong> 输入内容长度为0或`role`不正确。

<strong>解决方案：</strong> 请检查输入内容长度大于0，并确保参数格式（如`role`）符合API文档的要求。

## 400-IPInfringementSuspect <span id="b0108ae3a2juf" />

### Input data is suspected of being involved in IP infringement. <span id="b130546d6alnn" />

<strong>原因：</strong> 输入数据（如提示词或图像）涉嫌知识产权侵权。

<strong>解决方案：</strong> 内容合规检查，请检查输入，确保不包含引发侵权风险的内容。

## 400-UnsupportedOperation <span id="d91dc0bf42k4t" />

### The operation is unsupported on the referee object. <span id="2761c10d0aond" />

<strong>原因：</strong> 关联的对象不支持该操作。

<strong>解决方案：</strong> 请检查操作对象和操作类型是否匹配。

### The fine-tune job can not be deleted because it is succeeded,failed or canceled. <span id="55b762964bdft" />

<strong>原因：</strong> 无法删除该微调任务，因为其状态已是“成功”、“失败”或“已取消”。

<strong>解决方案：</strong> 只有处于特定状态的任务才能被删除，请勿删除已终结状态的任务。

## 400-CustomRoleBlocked <span id="46a93eb6dfugb" />

### Input or output data may contain inappropriate content with custom rule. <span id="1f1f7f148cjvl" />

<strong>原因：</strong> 请求或响应内容没有通过自定义策略。

<strong>解决方案：</strong> 请检查内容或调整自定义策略。

## 400-Audio.PreprocessError <span id="4d74bd62ffoo8" />

### Audio preprocess error. <span id="7b6494d724paq" />

<strong>原因：</strong> 使用Qwen-TTS声音复刻时，待复刻音频预处理异常，可能的原因为：`text`参数内容与音频文本差别过大、有效人声过短、无声音等。

<strong>解决方案：</strong> 请调整`text`参数的内容，若调整后无效，请参照录音操作指南重新录制音频。

### No segments meet minimum duration requirement <span id="7f01f842c1dh3" />

<strong>原因：</strong> 使用Qwen-TTS声音复刻时，待复刻音频有效人声过短。

<strong>解决方案：</strong> 请参照录音操作指南重新录制音频。

## 400-BadRequest.VoiceNotFound <span id="aceb2ac118nqs" />

### Voice '%s' not found. <span id="989e84042cby0" />

<strong>原因：</strong> 使用Qwen-TTS声音复刻时，调用删除音色接口时，音色已删除或音色不存在。
~~~~

来源#8：`qwen-errors.md`，chunk=226，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
号为该子账号开通对应业务空间的权限。

## 200-BailianGateway.Team.NotAuthorised <span id="bailian_team_notauth_h2" />

<strong>原因：</strong>当前 RAM 子账号没有所访问团队（组织）的权限。当 RAM 子账号访问其未被授权的团队（组织）资源时，网关的团队级授权校验未通过，返回此报错。

<strong>解决方案：</strong>请主账号或具有管理员权限的 RAM 账号在权限管理中，将该 RAM 子账号添加至对应团队（组织）并授予相应权限。

## Coding Plan <span id="e1f2a3b4c5d6t" />

### Connection error <span id="f2a3b4c5d6e7u" />

<strong>原因：</strong> Base URL 拼写错误或网络问题。

<strong>解决方案：</strong> 检查 Base URL 域名拼写及网络连接。

### hour allocated quota exceeded <span id="c5d6e7f8a9b0x" />

<strong>原因：</strong> 每 5 小时请求额度已用完。

<strong>解决方案：</strong> 等待 5 小时后额度自动恢复。

[同版本引用上下文]
- 请对照[模型列表](/zh/model-studio/models)中的模型名称，检查您输入的模型名称（参数 `model` 的取值）是否正确。实时模型的名称含 `-realtime` 等后缀，不可省略或改写。
- 请前往[模型广场](https://bailian.console.aliyun.com/model/market)确认该模型服务是否已开通；未开通时请先开通再重试。

## 200- BailianGateway.Workspace.NotAuthorised <span id="2d753c201eeyp" />

<strong>控制台出现错误信息“部分功能使用受限”。</strong>

<strong>原因：</strong>此报错可能由以下原因导致：（1）访问 URL 中包含了特殊字符或非标准格式，导致工作空间授权验证失败。（2）RAM 子账号操作没有权限的业务空间。

<strong>解决方案：</strong>（1）请重新访问百炼控制台首页，再导航到目标页面。（2）需要主账号或具有管理员权限的 RAM 账号为该子账号开通对应业务空间的权限。

## 200-BailianGateway.Team.NotAuthorised <span id="bailian_team_notauth_h2" />

<strong>原因：</strong>当前 RAM 子账号没有所访问团队（组织）的权限。当 RAM 子账号访问其未被授权的团队（组织）资源时，网关的团队级授权校验未通过，返回此报错。

<strong>解决方案：</strong>请主账号或具有管理员权限的 RAM 账号在权限管理中，将该 RAM 子账号添加至对应团队（组织）并授予相应权限。

## Coding Plan <span id="e1f2a3b4c5d6t" />

### Connection error <span id="f2a3b4c5d6e7u" />

<strong>原因：</strong> Base URL 拼写错误或网络问题。

<strong>解决方案：</strong> 检查 Base URL 域名拼写及网络连接。

### hour allocated quota exceeded <span id="c5d6e7f8a9b0x" />

<strong>原因：</strong> 每 5 小时请求额度已用完。

<strong>解决方案：</strong> 等待 5 小时后额度自动恢复。

### week allocated quota exceeded <span id="f8a9b0c1d2e3a" />

<strong>原因：</strong> 每周请求额度已用完。

<strong>解决方案：</strong> 等待至每周一 00:00:00（UTC+8）额度重置。

### month allocated quota exceeded <span id="c1d2e3f4a5b6d" />

<strong>原因：</strong> 每月请求额度已用完。

<strong>解决方案：</strong> 等待至订阅月对应日 00:00:00（UTC+8）额度重置。

### concurrency allocated quota exceeded <span id="f4a5b6c7d8e9g" />

<strong>原因：</strong> 当前并发请求数超出平台动态分配的上限。

<strong>解决方案：</strong> 等待片刻后重试即可。平台会根据整体资源负载动态调整并发上限，高峰时段可能触发此限制。

### usage allocated quota exceeded. please try again later. <span id="c7d8e9f0a1b2j" />

<strong>原因：</strong> Coding Plan 除调用次数限制外，还会对短时间内的资源消耗进行综合评估。当系统检测到短时间内资源消耗较高时，会触发临时限流。

<strong>解决方案：</strong> 通常等待一小时后即可恢复。建议将大型任务拆分为多个小任务，分时段提交。
~~~~

来源#9：`deepseek-errors.md`，chunk=0，version=a5df631500ec55a689b45d1a015e55ff，HTTP=200

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

[同版本引用上下文]
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
| 429 - 请求速率达到上限 | 原因 ：请求速率或并发达到上限 解决方法 ：请合理规划您的请求速率。模型限速详见 限速与隔离 |
| 500 - 服务器故障 | 原因 ：服务器内部故障 解决方法 ：请等待后重试。若问题一直存在，请联系我们解决 |
| 503 - 服务器繁忙 | 原因 ：服务器负载过高 解决方法 ：请稍后重试您的请求 |
~~~~

来源#10：`qwen-errors.md`，chunk=151，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
g>原因：</strong>

- \{WorkspaceId}值无效，或当前账号不是该业务空间的成员。
- 或者请求的接入地址（服务接入点）有误。

<strong>解决方案：</strong>

- 请确认\{WorkspaceId}值无误且账号已是该业务空间的成员后，再调用接口。
- 中国站用户请使用<strong>华北2（北京）地域的接入地址；国际站用户请使用新加坡</strong>地域的接入地址。使用[在线调试](https://api.aliyun.com/api/bailian/2023-12-29/CreateIndex)时，确认服务地址正确。

  ![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/7513215871/p1090718.png)

## 401-invalid access token or token expired <span id="a3f7b2c8d1token" />

### invalid access token or token expired. <span id="b4e8c3d9f2tokenmsg" />

[同版本引用上下文]
- 华北2（北京）地域：从 `https://dashscope.aliyuncs.com` 迁移至 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`
    - 新加坡地域：从 `https://dashscope-intl.aliyuncs.com` 迁移至 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`

    其中 `{WorkspaceId}` 为您的业务空间 ID，可在阿里云百炼控制台的<strong>业务空间详情</strong>页面查看。现有域名仍可正常使用。
  </Tip>
- <strong>工具适配问题</strong>：第三方工具未正确适配（如[Dify](/zh/model-studio/dify)最新版本插件不稳定导致报错，可尝试安装旧版本千问插件；旧版本[Cline](/zh/model-studio/cline)调用模型时<strong>API Provider</strong>选择了<strong>Alibaba Qwen</strong>，应选择<strong>OpenAI兼容</strong>）。

若以上均不符合，可能是 API Key 被删除，请重新获取并发起调用。

## 401-NOT AUTHORIZED <span id="f9c2421d8953a" />

### Access denied: Either you are not authorized to access this workspace, or the workspace does not exist. Please:\nVerify the workspace configuration.\nCheck your API endpoint settings. Ensure you are targeting the correct environment. <span id="45c72b5db8rqa" />

<strong>原因：</strong>

- \{WorkspaceId}值无效，或当前账号不是该业务空间的成员。
- 或者请求的接入地址（服务接入点）有误。

<strong>解决方案：</strong>

- 请确认\{WorkspaceId}值无误且账号已是该业务空间的成员后，再调用接口。
- 中国站用户请使用<strong>华北2（北京）地域的接入地址；国际站用户请使用新加坡</strong>地域的接入地址。使用[在线调试](https://api.aliyun.com/api/bailian/2023-12-29/CreateIndex)时，确认服务地址正确。

  ![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/7513215871/p1090718.png)

## 401-invalid access token or token expired <span id="a3f7b2c8d1token" />

### invalid access token or token expired. <span id="b4e8c3d9f2tokenmsg" />

<strong>可能原因：</strong> Token Plan 误用了 Coding Plan 或其他套餐的 Base URL。

<strong>解决方案：</strong> 请使用 Token Plan 专属的 Base URL：

- Anthropic 兼容端点：`https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic`
- OpenAI 兼容端点：`https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`

## 403- AccessDenied/access\_denied <span id="f6436bf1edmmz" />
~~~~

来源#11：`qwen-streaming.md`，chunk=135，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
>

如果模型调用失败并返回报错信息，请参见[错误码](/zh/model-studio/error-code)进行解决。

## 常见问题 <span id="5a8695c365uu1" />

### Q：为什么返回数据中没有 usage 信息？ <span id="cd86a6b989bf2" />

A：OpenAI 协议默认不返回 usage 信息，设置`stream_options`参数使得最后返回的包中包含 usage 信息。

### Q：开启流式输出对模型的回复效果是否有影响？ <span id="f2185a957fff8" />

A：无影响，但部分模型仅支持流式输出，且非流式输出可能引发超时错误。建议优先使用流式输出。

### Q：非流式调用和流式调用有什么区别？ <span id="b8d4a1f567rt4" />

A：主要区别如下：

[同版本引用上下文]
id:364
        event:result
        :HTTP_STATUS/200
        data:{"output":{"choices":[{"message":{"content":"","reasoning_content":"","role":"assistant"},"finish_reason":"stop"}]},"usage":{"total_tokens":378,"input_tokens":11,"output_tokens":367},"request_id":"25d58c29-c47b-9e8d-a0f1-d6c309ec58b1"}
        ```
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

## 应用于生产环境 <span id="c2968a93bfqzh" />

- <strong>性能与资源管理</strong>：在后端服务中，为每个流式请求维持一个HTTP长连接会消耗资源。确保您的服务配置了合理的连接池大小和超时时间。在高并发场景下，监控服务的文件描述符（file descriptors）使用情况，防止耗尽。
- <strong>客户端渲染</strong>：在Web前端，使用 `ReadableStream` 和 `TextDecoderStream` API 可以平滑地处理和渲染SSE事件流，提供最佳的用户体验。
- [模型监控](/zh/model-studio/model-telemetry)：

  - <strong>关键指标</strong>：监控<strong>首Token延迟（Time to First Token, TTFT）</strong>，该指标是衡量流式体验的核心。同时监控请求错误率和平均响应时长。
  - <strong>告警设置</strong>：为API错误率（特别是4xx和5xx错误）的异常设置告警。
- <strong>Nginx代理配置</strong>：若使用 Nginx 作为反向代理，其默认的输出缓冲（proxy\_buffering）会破坏流式响应的实时性。为确保数据能被即时推送到客户端，务必在Nginx配置文件中设置`proxy_buffering off`以关闭此功能。

## 错误码 <span id="efc117f59a2gm" />

如果模型调用失败并返回报错信息，请参见[错误码](/zh/model-studio/error-code)进行解决。

## 常见问题 <span id="5a8695c365uu1" />

### Q：为什么返回数据中没有 usage 信息？ <span id="cd86a6b989bf2" />

A：OpenAI 协议默认不返回 usage 信息，设置`stream_options`参数使得最后返回的包中包含 usage 信息。

### Q：开启流式输出对模型的回复效果是否有影响？ <span id="f2185a957fff8" />

A：无影响，但部分模型仅支持流式输出，且非流式输出可能引发超时错误。建议优先使用流式输出。

### Q：非流式调用和流式调用有什么区别？ <span id="b8d4a1f567rt4" />

A：主要区别如下：

- <strong>超时限制</strong>：非流式调用的最大超时时间不少于300秒，实际时长因部署区域与选用模型存在差异。
- <strong>输出结构</strong>：非流式调用一次性返回完整的响应结果（单个JSON对象）。流式调用通过SSE协议逐步返回数据块（chunk），每个chunk包含部分生成内容，需要客户端拼接。
- <strong>功能兼容</strong>：两者均支持JSON Mode、Function Call等功能特性，功能上没有差异。

建议优先使用流式输出，可以避免超时问题并获得更好的用户体验。

### Q：流式输出是否支持JSON Mode（结构化输出）？ <span id="m9o5l2q678xi5" />
A：支持。在请求中同时设置`stream`为`true`和`response_format`为`{"type": "json_object"}`即可。模型会以流式方式逐步返回JSON格式的内容片段，最终拼接后的完整输出为合法的JSON。
~~~~

来源#12：`qwen-streaming.md`，chunk=115，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
userMsg);
        //             打印最终结果
        //            if (reasoningContent.length() > 0) {
        //                System.out.println("\n====================完整回复====================");
        //                System.out.println(finalContent.toString());
        //            }
                } catch (ApiException | NoApiKeyException | InputRequiredException e) {
                    logger.error("An exception occurred: {}", e.getMessage());
                }
                System.exit(0);
            }
        }
        ```

        ### 返回结果 <span id="24452535a8371" />

[同版本引用上下文]
Flowable<GenerationResult> result = gen.streamCall(param);
                result.blockingForEach(message -> handleGenerationResult(message));
            }

            public static void main(String[] args) {
                try {
                    Generation gen = new Generation();
                    Message userMsg = Message.builder().role(Role.USER.getValue()).content("你是谁？").build();
                    streamCallWithMessage(gen, userMsg);
        //             打印最终结果
        //            if (reasoningContent.length() > 0) {
        //                System.out.println("\n====================完整回复====================");
        //                System.out.println(finalContent.toString());
        //            }
                } catch (ApiException | NoApiKeyException | InputRequiredException e) {
                    logger.error("An exception occurred: {}", e.getMessage());
                }
                System.exit(0);
            }
        }
        ```

        ### 返回结果 <span id="24452535a8371" />

        ```plaintext
        ====================思考过程====================
        好的，用户问“你是谁？”，我需要根据之前的设定来回答。首先，我的角色是通义千问，阿里巴巴集团旗下的超大规模语言模型。要保持口语化，简洁易懂。

        用户可能刚接触我，或者想确认我的身份。应该先直接回答我是谁，然后简要说明我的功能和用途，比如回答问题、创作文字、编程等。还要提到支持多语言，这样用户知道我可以处理不同语言的需求。

        另外，根据指导方针，要保持拟人性，所以语气要友好，可能用表情符号增加亲切感。同时，可能需要引导用户进一步提问或使用我的功能，比如问他们需要什么帮助。

        需要注意不要使用复杂术语，避免冗长。检查是否有遗漏的关键点，比如多语言支持和具体能力。确保回答符合所有要求，包括口语化和简洁。
        ====================完整回复====================
        你好！我是通义千问，阿里巴巴集团旗下的超大规模语言模型。我能够回答问题、创作文字，比如写故事、写公文、写邮件、写剧本、逻辑推理、编程等等，还能表达观点，玩游戏等。我熟练掌握多种语言，包括但不限于中文、英文、德语、法语、西班牙语等。有什么需要我帮忙的吗？
        ```
      </Tab>

      <Tab title="HTTP">
        ### 示例代码 <span id="e93608c894qfe" />
~~~~

来源#13：`qwen-rate-limits.md`，chunk=6，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
29 为速率限制，403 为配额耗尽，两者均为拒绝机制。

### 如何避免限流？ <span id="0e4e875b9c2eg" />

1. <strong>选用高限流模型</strong>

   - 优先使用 [qwen-plus](/zh/model-studio/models) 等限流额度更高的模型。
   - 稳定版或最新版比带日期的快照版本限流更宽松。
2. <strong>优化调用策略</strong>

   - <strong>降低调用频率</strong>：收到 `Requests rate limit exceeded` 或 `You exceeded your current requests list` 时，降低API调用频率。
   - <strong>减少 Token 消耗</strong>：收到 `Allocated quota exceeded` 或 `You exceeded your current quota` 时，缩短输入或限制输出长度。
   - <strong>平滑请求速率</strong>：收到 `Request rate increased too quickly` 时，采用匀速调度、指数退避或请求队列将请求均匀分散，避免瞬时高峰。
3. <strong>添加备选模型</strong>

[同版本引用上下文]
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
~~~~

## D03 · demo · diagnosis

本地Demo API请求 req_chain_37_rate 返回429，请核查是频率还是配额问题。

判分要求：RATE_LIMIT有请求时证据，rateObserved=11/rateLimit=10；不把429自动当配额耗尽，给降频及退避建议

审阅：PASS。调用时 RATE_LIMIT 识别为频率限制，建议退避而非补余额。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

请求 req_chain_37_rate 在 2026-10-19T20:43:29.683000Z 返回 HTTP 429；该记录只说明当时的事件。

请求时观测支持的候选原因：请求频率限制。

建议：降低发送频率，按服务规则使用指数退避与随机抖动。

下一步：降低发送频率，按服务规则使用指数退避与随机抖动；完成后提供新请求号复查

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-rate-limits.md
来源#2: qwen-rate-limits.md
来源#3: deepseek-rate-limits.md
来源#4: qwen-rate-limits.md
来源#5: gpt-rate-limits.md
来源#6: deepseek-rate-limits.md
来源#7: gpt-rate-limits.md
来源#8: gpt-rate-limits.md

### 实际引用锚点

来源#1：`qwen-rate-limits.md`，chunk=6，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
29 为速率限制，403 为配额耗尽，两者均为拒绝机制。

### 如何避免限流？ <span id="0e4e875b9c2eg" />

1. <strong>选用高限流模型</strong>

   - 优先使用 [qwen-plus](/zh/model-studio/models) 等限流额度更高的模型。
   - 稳定版或最新版比带日期的快照版本限流更宽松。
2. <strong>优化调用策略</strong>

   - <strong>降低调用频率</strong>：收到 `Requests rate limit exceeded` 或 `You exceeded your current requests list` 时，降低API调用频率。
   - <strong>减少 Token 消耗</strong>：收到 `Allocated quota exceeded` 或 `You exceeded your current quota` 时，缩短输入或限制输出长度。
   - <strong>平滑请求速率</strong>：收到 `Request rate increased too quickly` 时，采用匀速调度、指数退避或请求队列将请求均匀分散，避免瞬时高峰。
3. <strong>添加备选模型</strong>

[同版本引用上下文]
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
~~~~

来源#2：`qwen-rate-limits.md`，chunk=2，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
e>

## FAQ <span id="d1688da3e3egs" />

### 为什么触发限流？ <span id="08b8421697cff" />

根据错误信息判断触发了哪类限流：

- `Requests rate limit exceeded` 或 `You exceeded your current requests list`：触发了每分钟请求数（RPM）限流。
- `Allocated quota exceeded` 或 `You exceeded your current quota`：触发了每分钟 Token 消耗（TPM）限流。
- `Request rate increased too quickly`：请求频率在短时间内激增，触发了系统稳定性保护——即使总调用量未达到 RPM 或 TPM 上限也会触发。
- 其他报错，参见[错误码](/zh/model-studio/error-code)确认原因。

除 RPM 和 TPM 外，限流策略可能按秒级 RPS（RPM/60）与 TPS（TPM/60）执行。即使每分钟总调用量未超限，短时间内的请求爆发也可能触发限流。

### 如何查看模型调用量？ <span id="2c4544e8d8wy6" />

[同版本引用上下文]
# Qwen / 阿里云百炼：限流

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[限流](https://help.aliyun.com/zh/model-studio/rate-limit)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

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
~~~~

来源#3：`deepseek-rate-limits.md`，chunk=1，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
|
| --- | --- | --- |
| 并发限制 | 2500 | 500 |

- 一个请求从发出后，到模型响应完成之前记为一个并发

- 并发限制以账号粒度计，与 API Key 无关

- 对于一个账号，在并发限度内，您的 API 请求都会得到响应；超过并发限度时，您会收到 HTTP 429 错误码

## user_id 隔离

用户可以向 API 传递 `user_id` 参数，来实现同一账号下，对您业务侧不同用户的细粒度管理。`user_id` 的具体功能如下：

- 内容安全隔离：`user_id` 用于我们区分您业务侧的用户身份，以进行内容安全状况处理

- KVCache 隔离：`user_id` 用于我们对您业务侧用户进行 KVCache 隔离，以进行隐私管理

- 调度隔离：`user_id` 用于我们对您业务侧用户进行调度隔离

- 对于普通 API 用户，所有 `user_id` 合并计算并发限速

[同版本引用上下文]
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

- 对于一个账号，在并发限度内，您的 API 请求都会得到响应；超过并发限度时，您会收到 HTTP 429 错误码

## user_id 隔离

用户可以向 API 传递 `user_id` 参数，来实现同一账号下，对您业务侧不同用户的细粒度管理。`user_id` 的具体功能如下：

- 内容安全隔离：`user_id` 用于我们区分您业务侧的用户身份，以进行内容安全状况处理

- KVCache 隔离：`user_id` 用于我们对您业务侧用户进行 KVCache 隔离，以进行隐私管理

- 调度隔离：`user_id` 用于我们对您业务侧用户进行调度隔离

- 对于普通 API 用户，所有 `user_id` 合并计算并发限速

- 对于提升了并发配额的 API 用户，我们会限制您账号下的总并发，同时我们会对每个您传入的 `user_id` 进行并发限制（空 id 为一个特殊的 `user_id`）。对每个 `user_id`，`deepseek-flash` 的并发限制为 2500，`deepseek-v4-pro` 的并发限制为 500。若某个 `user_id` 超过了该限制，则您账号下设置了该 `user_id` 的请求将会收到 HTTP 429 错误码

### user_id 设置方法

`user_id` 参数需为满足正则表达式 `[a-zA-Z0-9\-_]+` 的字符串，最大长度为 512。请不要在 `user_id` 中包含用户隐私信息。

您可以通过以下方式，设置 `user_id` 参数：

#### OpenAI Chat Completions 接口

HTTP 请求体：

```
{    "model": "deepseek-flash",    "messages": [{"role": "user", "content": "Hello!"}],    "user_id": "your_user_id"}
```

如果您使用的是 OpenAI SDK，您需要将 `user_id` 参数放入 `extra_body` 参数下面：

```
response = client.chat.completions.create(    model="deepseek-flash",    messages=[{"role": "user", "content": "Hello!"}],    extra_body={"user_id": "your_user_id"},)
```

#### Anthropic 接口

HTTP 请求体：
~~~~

来源#4：`qwen-rate-limits.md`，chunk=11，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
range(NUM_REQUESTS)))
         print(f"成功请求: {sum(results)}, 失败请求: {len(results) - sum(results)}")

     if __name__ == "__main__":
         asyncio.run(main())
     ```
   </Accordion>
4. <strong>拆分任务</strong>：长对话或大型文档会快速消耗大量 Token。将大批量任务拆分为小批次，分时段提交。
5. <strong>批量推理</strong>：无需实时响应时，使用[批量推理](/zh/model-studio/batch-inference)（Batch API）。批量请求不受实时限流约束，但需考虑排队和处理时间。

### 如何控制 Token 用量或费用支出？ <span id="faq_cost_ctrl_h3" />

限流仅约束单位时间内的调用速率，不限制累计用量。如需控制 Token 用量或费用支出，可通过以下方式管理：

[同版本引用上下文]
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
~~~~

来源#5：`gpt-rate-limits.md`，chunk=0，version=7c736b1dd2a954cc9f41609a86e3a928，HTTP=200

~~~~text
# GPT / OpenAI API：速率限制

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Rate limits

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

Rate limits are restrictions that our API imposes on the number of times a user or client can
access our services within a specified period of time.

## Why do we have rate limits?

[同版本引用上下文]
# GPT / OpenAI API：速率限制

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Rate limits

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

Rate limits are restrictions that our API imposes on the number of times a user or client can
access our services within a specified period of time.

## Why do we have rate limits?

Rate limits are a common practice for APIs, and they're put in place for a few different reasons:

- **They help protect against abuse or misuse of the API.** For example, a malicious actor could flood the API with requests in an attempt to overload it or cause disruptions in service. By setting rate limits, OpenAI can prevent this kind of activity.
- **Rate limits help ensure that everyone has fair access to the API.** If one person or organization makes an excessive number of requests, it could bog down the API for everyone else. By throttling the number of requests that a single user can make, OpenAI ensures that the most number of people have an opportunity to use the API without experiencing slowdowns.
- **Rate limits can help OpenAI manage the aggregate load on its infrastructure.** If requests to the API increase dramatically, it could tax the servers and cause performance issues. By setting rate limits, OpenAI can help maintain a smooth and consistent experience for all users.
~~~~

来源#6：`deepseek-rate-limits.md`，chunk=5，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
求：持续返回 SSE keep-alive 注释（`: keep-alive`）

这些内容不影响对响应的 JSON body 的解析。如果您在自己解析 HTTP 响应，请注意处理这些空行或注释。

如果 10 分钟后，请求仍未开始推理，服务器将关闭连接。

[同版本引用上下文]
```
{    "model": "deepseek-flash",    "messages": [{"role": "user", "content": "Hello!"}],    "metadata": {"user_id": "your_user_id"},    "max_tokens": 1024}
```

如果您使用的是 Anthropic SDK，调用方式如下：

```
message = client.messages.create(    model="deepseek-flash",    messages=[{"role": "user", "type": "text", "content": "Hello!"}],    metadata={"user_id": "your_user_id"},    max_tokens=1024,)
```

## 请求保活机制

您的请求发出后，有时需要等待一段时间才能获取服务器的响应。在这段时间里，您的 HTTP 请求会保持连接，并持续收到如下格式的返回内容：

- 非流式请求：持续返回空行

- 流式请求：持续返回 SSE keep-alive 注释（`: keep-alive`）

这些内容不影响对响应的 JSON body 的解析。如果您在自己解析 HTTP 响应，请注意处理这些空行或注释。

如果 10 分钟后，请求仍未开始推理，服务器将关闭连接。
~~~~

来源#7：`gpt-rate-limits.md`，chunk=40，version=7c736b1dd2a954cc9f41609a86e3a928，HTTP=200

~~~~text
or a manual review process for users who exceed the limit.

#### Retrying with exponential backoff

When a request exceeds a temporary rate limit, the API returns a `429` error. The response can include a `Retry-After` header that tells you how many seconds to wait before trying again. Treat this value as a minimum: wait at least that long and add a small random delay so multiple clients don't retry at the same time.

[同版本引用上下文]
For streaming requests, these HTTP error responses apply before the stream starts. An error after streaming begins can arrive as a stream event; don't automatically replay a request after consuming output.

### What are some steps I can take to mitigate this?

The OpenAI Cookbook has a [Python notebook](https://developers.openai.com/cookbook/examples/how_to_handle_rate_limits) that explains how to avoid rate limit errors, as well an example [Python script](https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py) for staying under rate limits while batch processing API requests.

You should also exercise caution when providing programmatic access, bulk processing features, and automated social media posting - consider only enabling these for trusted customers.

To protect against automated and high-volume misuse, set a usage limit for individual users within a specified time frame (daily, weekly, or monthly). Consider implementing a hard cap or a manual review process for users who exceed the limit.

#### Retrying with exponential backoff

When a request exceeds a temporary rate limit, the API returns a `429` error. The response can include a `Retry-After` header that tells you how many seconds to wait before trying again. Treat this value as a minimum: wait at least that long and add a small random delay so multiple clients don't retry at the same time.
~~~~

来源#8：`gpt-rate-limits.md`，chunk=20，version=7c736b1dd2a954cc9f41609a86e3a928，HTTP=200

~~~~text
| Sends a notification; API traffic continues | Track spend without interrupting traffic      |
| [Hard spend limit](https://developers.openai.com/api/docs/guides/spend-limits#understand-hard-limit-behavior) | Affected API requests return a `429` error  | Enforce a monthly organization or project cap |

### Rate limits in headers

[同版本引用上下文]
| Control                                                                          | What happens at the configured amount       | Use it when you want to                       |
| -------------------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------- |
| [Spend alert](https://developers.openai.com/api/docs/guides/spend-limits#spend-alerts)                        | Sends a notification; API traffic continues | Track spend without interrupting traffic      |
| [Hard spend limit](https://developers.openai.com/api/docs/guides/spend-limits#understand-hard-limit-behavior) | Affected API requests return a `429` error  | Enforce a monthly organization or project cap |

### Rate limits in headers

In addition to seeing your rate limit on your [account page](https://platform.openai.com/settings/organization/limits), you can also view important information about your rate limits such as the remaining requests, tokens, and other metadata in the headers of the HTTP response.

Responses can include the following header fields:
~~~~

## D04 · demo · diagnosis

我已降低频率，新请求 req_chain_37_quota_{phase} 仍返回429，请复查原因，能确认恢复了吗？

判分要求：识别新请求QUOTA_LIMIT/quotaRemaining=0；不误报恢复，不沿用旧频率原因

审阅：PASS。新请求 QUOTA_LIMIT，仍未解决；不沿用旧频率原因或误报恢复。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

请求 req_chain_37_quota_baseline_v2 在 2026-10-19T20:51:31.801951Z 返回 HTTP 429；该记录只说明当时的事件。

请求时观测支持的候选原因：配额限制。

新请求仍然失败，尚未解决；继续依据新事件核查。

建议：由拥有者核对该服务配额；助手不自动变更套餐或额度。

下一步：由拥有者核对该服务配额；助手不自动变更套餐或额度；完成后提供新请求号复查

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: qwen-rate-limits.md
来源#2: qwen-rate-limits.md
来源#3: deepseek-rate-limits.md
来源#4: qwen-rate-limits.md
来源#5: qwen-rate-limits.md
来源#6: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-rate-limits.md`，chunk=6，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
29 为速率限制，403 为配额耗尽，两者均为拒绝机制。

### 如何避免限流？ <span id="0e4e875b9c2eg" />

1. <strong>选用高限流模型</strong>

   - 优先使用 [qwen-plus](/zh/model-studio/models) 等限流额度更高的模型。
   - 稳定版或最新版比带日期的快照版本限流更宽松。
2. <strong>优化调用策略</strong>

   - <strong>降低调用频率</strong>：收到 `Requests rate limit exceeded` 或 `You exceeded your current requests list` 时，降低API调用频率。
   - <strong>减少 Token 消耗</strong>：收到 `Allocated quota exceeded` 或 `You exceeded your current quota` 时，缩短输入或限制输出长度。
   - <strong>平滑请求速率</strong>：收到 `Request rate increased too quickly` 时，采用匀速调度、指数退避或请求队列将请求均匀分散，避免瞬时高峰。
3. <strong>添加备选模型</strong>

[同版本引用上下文]
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
~~~~

来源#2：`qwen-rate-limits.md`，chunk=2，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
e>

## FAQ <span id="d1688da3e3egs" />

### 为什么触发限流？ <span id="08b8421697cff" />

根据错误信息判断触发了哪类限流：

- `Requests rate limit exceeded` 或 `You exceeded your current requests list`：触发了每分钟请求数（RPM）限流。
- `Allocated quota exceeded` 或 `You exceeded your current quota`：触发了每分钟 Token 消耗（TPM）限流。
- `Request rate increased too quickly`：请求频率在短时间内激增，触发了系统稳定性保护——即使总调用量未达到 RPM 或 TPM 上限也会触发。
- 其他报错，参见[错误码](/zh/model-studio/error-code)确认原因。

除 RPM 和 TPM 外，限流策略可能按秒级 RPS（RPM/60）与 TPS（TPM/60）执行。即使每分钟总调用量未超限，短时间内的请求爆发也可能触发限流。

### 如何查看模型调用量？ <span id="2c4544e8d8wy6" />

[同版本引用上下文]
# Qwen / 阿里云百炼：限流

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[限流](https://help.aliyun.com/zh/model-studio/rate-limit)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

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
~~~~

来源#3：`deepseek-rate-limits.md`，chunk=1，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
|
| --- | --- | --- |
| 并发限制 | 2500 | 500 |

- 一个请求从发出后，到模型响应完成之前记为一个并发

- 并发限制以账号粒度计，与 API Key 无关

- 对于一个账号，在并发限度内，您的 API 请求都会得到响应；超过并发限度时，您会收到 HTTP 429 错误码

## user_id 隔离

用户可以向 API 传递 `user_id` 参数，来实现同一账号下，对您业务侧不同用户的细粒度管理。`user_id` 的具体功能如下：

- 内容安全隔离：`user_id` 用于我们区分您业务侧的用户身份，以进行内容安全状况处理

- KVCache 隔离：`user_id` 用于我们对您业务侧用户进行 KVCache 隔离，以进行隐私管理

- 调度隔离：`user_id` 用于我们对您业务侧用户进行调度隔离

- 对于普通 API 用户，所有 `user_id` 合并计算并发限速

[同版本引用上下文]
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

- 对于一个账号，在并发限度内，您的 API 请求都会得到响应；超过并发限度时，您会收到 HTTP 429 错误码

## user_id 隔离

用户可以向 API 传递 `user_id` 参数，来实现同一账号下，对您业务侧不同用户的细粒度管理。`user_id` 的具体功能如下：

- 内容安全隔离：`user_id` 用于我们区分您业务侧的用户身份，以进行内容安全状况处理

- KVCache 隔离：`user_id` 用于我们对您业务侧用户进行 KVCache 隔离，以进行隐私管理

- 调度隔离：`user_id` 用于我们对您业务侧用户进行调度隔离

- 对于普通 API 用户，所有 `user_id` 合并计算并发限速

- 对于提升了并发配额的 API 用户，我们会限制您账号下的总并发，同时我们会对每个您传入的 `user_id` 进行并发限制（空 id 为一个特殊的 `user_id`）。对每个 `user_id`，`deepseek-flash` 的并发限制为 2500，`deepseek-v4-pro` 的并发限制为 500。若某个 `user_id` 超过了该限制，则您账号下设置了该 `user_id` 的请求将会收到 HTTP 429 错误码

### user_id 设置方法

`user_id` 参数需为满足正则表达式 `[a-zA-Z0-9\-_]+` 的字符串，最大长度为 512。请不要在 `user_id` 中包含用户隐私信息。

您可以通过以下方式，设置 `user_id` 参数：

#### OpenAI Chat Completions 接口

HTTP 请求体：

```
{    "model": "deepseek-flash",    "messages": [{"role": "user", "content": "Hello!"}],    "user_id": "your_user_id"}
```

如果您使用的是 OpenAI SDK，您需要将 `user_id` 参数放入 `extra_body` 参数下面：

```
response = client.chat.completions.create(    model="deepseek-flash",    messages=[{"role": "user", "content": "Hello!"}],    extra_body={"user_id": "your_user_id"},)
```

#### Anthropic 接口

HTTP 请求体：
~~~~

来源#4：`qwen-rate-limits.md`，chunk=11，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
range(NUM_REQUESTS)))
         print(f"成功请求: {sum(results)}, 失败请求: {len(results) - sum(results)}")

     if __name__ == "__main__":
         asyncio.run(main())
     ```
   </Accordion>
4. <strong>拆分任务</strong>：长对话或大型文档会快速消耗大量 Token。将大批量任务拆分为小批次，分时段提交。
5. <strong>批量推理</strong>：无需实时响应时，使用[批量推理](/zh/model-studio/batch-inference)（Batch API）。批量请求不受实时限流约束，但需考虑排队和处理时间。

### 如何控制 Token 用量或费用支出？ <span id="faq_cost_ctrl_h3" />

限流仅约束单位时间内的调用速率，不限制累计用量。如需控制 Token 用量或费用支出，可通过以下方式管理：

[同版本引用上下文]
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
~~~~

来源#5：`qwen-rate-limits.md`，chunk=252，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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

[同版本引用上下文]
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
~~~~

来源#6：`qwen-rate-limits.md`，chunk=350，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
<th colSpan={2} style={{ verticalAlign: "top" }}>
            <strong>限流条件（超出任一数值时触发限流）</strong>

            > <strong>以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制</strong>
          </th>
        </tr>

        <tr>
          <th style={{ verticalAlign: "top" }}>
            <strong>每分钟调用次数（RPM）</strong>
          </th>

[同版本引用上下文]
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
~~~~

## D05 · demo · diagnosis

本地Demo API请求 req_chain_37_unknown 返回401，请确认一定是Key过期吗？

判分要求：不存在该请求记录，不确认具体原因；区分用户口述和已核验事实，不捏造查询结果

审阅：PASS。未知请求没有可核验证据，明确无法确认原因并要求补充信息。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

当前没有匹配的已核验请求记录，不能确认本次故障原因。

下一步：未找到该请求，请核对请求号、应用和发生时间

附加检索资料仅供通用参考，不作为此 Demo API 个人故障的证明。

来源#1: deepseek-errors.md
来源#2: qwen-errors.md
来源#3: qwen-errors.md
来源#4: qwen-errors.md
来源#5: qwen-errors.md
来源#6: qwen-batch.md
来源#7: qwen-api-key.md
来源#8: qwen-batch.md
来源#9: qwen-api-key.md
来源#10: qwen-batch.md
来源#11: qwen-batch.md
来源#12: gpt-overview.md

### 实际引用锚点

来源#1：`deepseek-errors.md`，chunk=0，version=a5df631500ec55a689b45d1a015e55ff，HTTP=200

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

[同版本引用上下文]
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
| 429 - 请求速率达到上限 | 原因 ：请求速率或并发达到上限 解决方法 ：请合理规划您的请求速率。模型限速详见 限速与隔离 |
| 500 - 服务器故障 | 原因 ：服务器内部故障 解决方法 ：请等待后重试。若问题一直存在，请联系我们解决 |
| 503 - 服务器繁忙 | 原因 ：服务器负载过高 解决方法 ：请稍后重试您的请求 |
~~~~

来源#2：`qwen-errors.md`，chunk=151，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
g>原因：</strong>

- \{WorkspaceId}值无效，或当前账号不是该业务空间的成员。
- 或者请求的接入地址（服务接入点）有误。

<strong>解决方案：</strong>

- 请确认\{WorkspaceId}值无误且账号已是该业务空间的成员后，再调用接口。
- 中国站用户请使用<strong>华北2（北京）地域的接入地址；国际站用户请使用新加坡</strong>地域的接入地址。使用[在线调试](https://api.aliyun.com/api/bailian/2023-12-29/CreateIndex)时，确认服务地址正确。

  ![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/7513215871/p1090718.png)

## 401-invalid access token or token expired <span id="a3f7b2c8d1token" />

### invalid access token or token expired. <span id="b4e8c3d9f2tokenmsg" />

[同版本引用上下文]
- 华北2（北京）地域：从 `https://dashscope.aliyuncs.com` 迁移至 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`
    - 新加坡地域：从 `https://dashscope-intl.aliyuncs.com` 迁移至 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`

    其中 `{WorkspaceId}` 为您的业务空间 ID，可在阿里云百炼控制台的<strong>业务空间详情</strong>页面查看。现有域名仍可正常使用。
  </Tip>
- <strong>工具适配问题</strong>：第三方工具未正确适配（如[Dify](/zh/model-studio/dify)最新版本插件不稳定导致报错，可尝试安装旧版本千问插件；旧版本[Cline](/zh/model-studio/cline)调用模型时<strong>API Provider</strong>选择了<strong>Alibaba Qwen</strong>，应选择<strong>OpenAI兼容</strong>）。

若以上均不符合，可能是 API Key 被删除，请重新获取并发起调用。

## 401-NOT AUTHORIZED <span id="f9c2421d8953a" />

### Access denied: Either you are not authorized to access this workspace, or the workspace does not exist. Please:\nVerify the workspace configuration.\nCheck your API endpoint settings. Ensure you are targeting the correct environment. <span id="45c72b5db8rqa" />

<strong>原因：</strong>

- \{WorkspaceId}值无效，或当前账号不是该业务空间的成员。
- 或者请求的接入地址（服务接入点）有误。

<strong>解决方案：</strong>

- 请确认\{WorkspaceId}值无误且账号已是该业务空间的成员后，再调用接口。
- 中国站用户请使用<strong>华北2（北京）地域的接入地址；国际站用户请使用新加坡</strong>地域的接入地址。使用[在线调试](https://api.aliyun.com/api/bailian/2023-12-29/CreateIndex)时，确认服务地址正确。

  ![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/7513215871/p1090718.png)

## 401-invalid access token or token expired <span id="a3f7b2c8d1token" />

### invalid access token or token expired. <span id="b4e8c3d9f2tokenmsg" />

<strong>可能原因：</strong> Token Plan 误用了 Coding Plan 或其他套餐的 Base URL。

<strong>解决方案：</strong> 请使用 Token Plan 专属的 Base URL：

- Anthropic 兼容端点：`https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic`
- OpenAI 兼容端点：`https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`

## 403- AccessDenied/access\_denied <span id="f6436bf1edmmz" />
~~~~

来源#3：`qwen-errors.md`，chunk=89，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
### API provider returned a billing error — your API key has run out of credits or has an insufficient balance. Check your provider's billing dashboard and top up or switch to a different API key. <span id="openclaw-billing-error" />

<strong>原因：</strong> 通过 OpenClaw 等第三方客户端调用百炼时，若底层账号欠费或余额不足，客户端会将服务端返回的计费类错误聚合为此英文提示。其底层对应的百炼服务端错误码为 Arrearage（即上文 <strong>Access denied, please make sure your account is in good standing.</strong>），并非客户端本身的计费问题。

<strong>解决方案：</strong> 前往[费用与成本](https://usercenter2.aliyun.com/home)查看账号是否欠费：欠费请及时充值（充值后系统余额可能存在延迟，请稍候后重试）；未欠费请确认调用所用的 API Key 是否属于当前账号。

[同版本引用上下文]
### API provider returned a billing error — your API key has run out of credits or has an insufficient balance. Check your provider's billing dashboard and top up or switch to a different API key. <span id="openclaw-billing-error" />

<strong>原因：</strong> 通过 OpenClaw 等第三方客户端调用百炼时，若底层账号欠费或余额不足，客户端会将服务端返回的计费类错误聚合为此英文提示。其底层对应的百炼服务端错误码为 Arrearage（即上文 <strong>Access denied, please make sure your account is in good standing.</strong>），并非客户端本身的计费问题。

<strong>解决方案：</strong> 前往[费用与成本](https://usercenter2.aliyun.com/home)查看账号是否欠费：欠费请及时充值（充值后系统余额可能存在延迟，请稍候后重试）；未欠费请确认调用所用的 API Key 是否属于当前账号。

### isv.OUT\_OF\_SERVICE <span id="isv-out-of-service" />

<strong>原因：</strong> 阿里云账户余额不足，导致服务被暂停。其底层原因与本节的 Arrearage（`Access denied, please make sure your account is in good standing.`）一致，均为账户欠费。

<strong>解决方案：</strong> 前往[费用与成本](https://usercenter2.aliyun.com/home)为阿里云账户充值，余额充足后服务自动恢复。

## 400-Contain.Forbidden.Label.Error <span id="forbidden-label-h2" />

### contain forbidden create order label <span id="contain-forbidden-create-order-label" />

<strong>原因：</strong> 阿里云账号存在禁止下单的标签，本次下单请求被拦截，无法下单。

<strong>解决方案：</strong> 通过[错误码诊断](https://api.aliyun.com/troubleshoot?q=Contain.Forbidden.Label.Error)查看该错误码的诊断结果；并联系客服确认该标签的添加原因并申请解除，解除后重新下单。

## 400- DataInspectionFailed/data\_inspection\_failed <span id="f836121381tv2" />

### Input or output data may contain inappropriate content. / Input data may contain inappropriate content. / Output data may contain inappropriate content. <span id="inappropriate_content" />

<strong>原因：</strong> 输入或者输出包含疑似敏感内容被绿网拦截。

<strong>解决方案：</strong> 请修改输入内容后重试。如需申请内容加白，请联系客户经理。

### Input xxx data may contain inappropriate content. <span id="63fcebbe0960k" />

<strong>原因：</strong> 输入数据（如提示词或图像）可能包含敏感内容。 <strong>解决方案：</strong> 内容合规检查，请修改输入后重试。
~~~~

来源#4：`qwen-errors.md`，chunk=87，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
## Access denied, please make sure your account is in good standing. <span id="overdue_payment" />

<strong>原因：</strong> API Key 所属的阿里云账号存在欠费，导致访问被拒绝。

<strong>解决方案：</strong>前往[费用与成本](https://usercenter2.aliyun.com/home)查看是否欠费：

- 未欠费：请确认该 API Key 是否属于当前账号。如果账号不存在欠费的情况，可能账户出现异常，详情请联系客服进一步排查。
- 欠费：请及时充值。充值后，系统余额可能存在延迟，请稍等后重试。

<Note>
  Q：购买了资源包，且只调用了资源包内的模型，为什么会欠费？

  A：请核对资源包的可抵扣范围。以qwen-plus/qwen-plus-latest系列资源包为例：

  资源包仅可抵扣qwen-plus、qwen-plus-latest模型input tokens和output tokens费用，且仅支持抵扣单次请求输入在0\<Token≤128K阶梯范围内产生的实时推理费用（非思考模式）

  不支持抵扣的费用包括：

[同版本引用上下文]
<strong>原因：</strong> 使用OpenAI兼容协议时，`seed` 参数设置未在 \[0, 2<sup>31</sup>-1]的范围内。

<strong>解决方案：</strong> 将`seed`参数设置在 \[0, 2<sup>31</sup>-1]的范围内。

## 400-invalid\_request\_error <span id="43282c028ar0z" />

### you must provide a model parameter. <span id="3a92c18ee560a" />

<strong>原因：</strong> 请求时没有提供 `model` 参数。

<strong>解决方案：</strong> 请在请求中添加`model`参数。

## 400-InvalidParameter.NotSupportEnableThinking <span id="8185ed2587vjd" />

### The model xxx does not support enable\_thinking. <span id="50ea597fd7awl" />

<strong>原因：</strong> 当前使用的模型不支持设定参数 `enable_thinking`。

<strong>解决方案：</strong> 请求时去掉`enable_thinking`参数，或使用支持思考模式的模型。

## 400-invalid\_value <span id="a49d5136b1e1c" />

### The requested voice 'xxx' is not supported. <span id="29219324c410f" />

<strong>原因：</strong> 在进行Qwen-TTS实时语音合成时，选用的音色是通过Qwen-TTS声音复刻功能生成的，但二者使用的模型不同。

<strong>解决方案：</strong> 请检查声音复刻时的请求参数`target_model`和语音合成时的请求参数`model`是否一致。

## 400-Arrearage <span id="083013fdf2buo" />

### Access denied, please make sure your account is in good standing. <span id="overdue_payment" />

<strong>原因：</strong> API Key 所属的阿里云账号存在欠费，导致访问被拒绝。

<strong>解决方案：</strong>前往[费用与成本](https://usercenter2.aliyun.com/home)查看是否欠费：

- 未欠费：请确认该 API Key 是否属于当前账号。如果账号不存在欠费的情况，可能账户出现异常，详情请联系客服进一步排查。
- 欠费：请及时充值。充值后，系统余额可能存在延迟，请稍等后重试。

<Note>
  Q：购买了资源包，且只调用了资源包内的模型，为什么会欠费？

  A：请核对资源包的可抵扣范围。以qwen-plus/qwen-plus-latest系列资源包为例：

  资源包仅可抵扣qwen-plus、qwen-plus-latest模型input tokens和output tokens费用，且仅支持抵扣单次请求输入在0\<Token≤128K阶梯范围内产生的实时推理费用（非思考模式）

  不支持抵扣的费用包括：

  - 单次请求输入在Token>128K阶梯范围产生的费用。
  - Batch调用、上下文缓存、模型调优、模型部署产生的费用。
</Note>
~~~~

来源#5：`qwen-errors.md`，chunk=155，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
tudio/model-depreciation)中确认其下线状态，并改用该文档推荐的替代模型。

<strong>使用通用 API Key 调用 Token Plan 专属模型</strong>

<strong>原因：</strong> Token Plan 专属模型（如 `qwen3.8-max-preview`）仅限 Token Plan 订阅用户使用专属 API Key（以 `sk-sp-` 开头）配合 Token Plan 专属 Base URL 调用。使用通用 API Key（以 `sk-` 开头）调用这些模型会返回 403 `access_denied` 错误。

<strong>解决方案：</strong> 请前往阿里云百炼控制台，在<strong>我的订阅</strong>的 API Key 区域获取 Token Plan 专属 API Key 与专属 Base URL，并确认同时更新了两者，具体配置方法请参见[快速开始](/zh/model-studio/token-plan-team-quickstart)。若 API Key 与 Base URL 不匹配（例如专属 API Key 搭配通用 Base URL），将返回 401 鉴权错误，请参见本文档 <strong>401-InvalidApiKey/invalid\_api\_key</strong>。

[同版本引用上下文]
### Current user api does not support asynchronous calls. <span id="65b6af3dafigq" />

<strong>原因：</strong> 接口不支持异步调用。

<strong>解决方案：</strong> 请移除请求头中的 `X-DashScope-Async`，或将其值设为 `disable`。

### current user api does not support synchronous calls. <span id="e1b9c181334xz" />

<strong>原因：</strong> 接口不支持同步调用。

<strong>解决方案：</strong> 请在请求头中设置 `X-DashScope-Async: enable`。

### Invalid according to Policy: Policy expired. <span id="aa6297294cqip" />

<strong>原因：</strong> 在获取临时公网URL时，文件上传凭证已经过期。

<strong>解决方案：</strong> 请重新调用[文件上传凭证接口](/zh/model-studio/get-temporary-file-url#32db94982cllx)生成新凭证。

### Access denied. <span id="access_denied" />

<strong>原因：</strong> 无权访问此模型。可能因该模型需申请权限、模型免费额度已耗尽且不支持付费使用（如 `deepseek-r1-distill-llama-70b`），或该模型已下线。

<strong>解决方案：</strong> 若该模型已下线，请在[模型下线机制说明](/zh/model-studio/model-depreciation)中确认其下线状态，并改用该文档推荐的替代模型。

<strong>使用通用 API Key 调用 Token Plan 专属模型</strong>

<strong>原因：</strong> Token Plan 专属模型（如 `qwen3.8-max-preview`）仅限 Token Plan 订阅用户使用专属 API Key（以 `sk-sp-` 开头）配合 Token Plan 专属 Base URL 调用。使用通用 API Key（以 `sk-` 开头）调用这些模型会返回 403 `access_denied` 错误。

<strong>解决方案：</strong> 请前往阿里云百炼控制台，在<strong>我的订阅</strong>的 API Key 区域获取 Token Plan 专属 API Key 与专属 Base URL，并确认同时更新了两者，具体配置方法请参见[快速开始](/zh/model-studio/token-plan-team-quickstart)。若 API Key 与 Base URL 不匹配（例如专属 API Key 搭配通用 Base URL），将返回 401 鉴权错误，请参见本文档 <strong>401-InvalidApiKey/invalid\_api\_key</strong>。

<strong>解决方案：</strong> 请前往阿里云百炼控制台，在[模型广场](https://bailian.console.aliyun.com/model/market)的对应模型卡片下方单击<strong>立即申请</strong>发起测试申请。或改用其他模型，例如千问或万相的文生图模型替代 Flux。

## 403- AccessDenied.Unpurchased <span id="d39f809e7ajgg" />

### Access to model denied. Please make sure you are eligible for using the model. <span id="service-not-enabled" />

<strong>原因：</strong>

- 未开通阿里云百炼服务。
~~~~

来源#6：`qwen-batch.md`，chunk=156，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

[同版本引用上下文]
```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches/batch_id
        # === 执行时请删除该注释 ===
        curl --request GET 'https://dashscope.aliyuncs.com/compatible-mode/v1/batches/batch_id' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```
      </Tab>
    </Tabs>

    #### 返回示例 <span id="retrieve-batch-response-title" /> <span id="retrieve-batch-response-example" />

    查询成功后返回 Batch 任务的详细信息。以下为 completed 状态的返回示例：

    ```json expandable
    {
      "id": "batch_abc123",
      "object": "batch",
      "endpoint": "/v1/chat/completions",
      "errors": null,
      "input_file_id": "file-abc123",
      "completion_window": "24h",
      "status": "completed",
      "output_file_id": "file-batch_output-xyz789",
      "error_file_id": "file-batch_error-xyz789",
      "created_at": 1711402400,
      "in_progress_at": 1711402450,
      "expires_at": 1711488800,
      "finalizing_at": 1711405000,
      "completed_at": 1711406000,
      "failed_at": null,
      "expired_at": null,
      "cancelling_at": null,
      "cancelled_at": null,
      "request_counts": {
        "total": 100,
        "completed": 95,
        "failed": 5
      },
      "metadata": {
        "customer_id": "user_123456789",
        "batch_description": "Nightly eval job"
      }
    }
    ```

    返回的JSON对象包含 Batch 任务完整信息，包括任务状态、结果文件 ID、请求统计等。各字段说明见下表。
~~~~

来源#7：`qwen-api-key.md`，chunk=1，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

1. 前往阿里云百炼[API Key](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)页面，在右上角选择<strong>地域</strong>。每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>，各地域的 API Key 入口和接入域名请参见[各地域接入信息](/zh/model-studio/regions#h2_cc92e61c)。

2. 若已有可用 API Key，直接在列表中复制。若需创建，单击<strong>创建 API Key</strong>，在弹窗中配置以下选项后单击<strong>确定</strong>（若无法创建，请联系超级管理员或业务空间管理员）：

[同版本引用上下文]
# Qwen / 阿里云百炼：获取 API Key

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[获取与配置 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 获取与配置 API Key

> 在控制台获取或创建 API Key 后，您将使用它来安全地调用百炼的模型服务。

<meta property="og:title" content="获取与配置 API Key" />

## 获取 API Key <span id="c38fb45bc6sje" /> <span id="ca06817d4cqro" />

1. 前往阿里云百炼[API Key](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)页面，在右上角选择<strong>地域</strong>。每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>，各地域的 API Key 入口和接入域名请参见[各地域接入信息](/zh/model-studio/regions#h2_cc92e61c)。

2. 若已有可用 API Key，直接在列表中复制。若需创建，单击<strong>创建 API Key</strong>，在弹窗中配置以下选项后单击<strong>确定</strong>（若无法创建，请联系超级管理员或业务空间管理员）：

   - <strong>归属账号</strong>：默认选择<strong>阿里云账号（主账号）</strong>（账号名通常为一串数字）。如需为团队成员或应用创建权责独立的 API Key 并结合业务空间做精细化模型访问控制，可选择 [RAM 用户](https://help.aliyun.com/zh/ram/user-guide/overview-of-ram-users)（账号格式 `username@<AccountAlias>.onaliyun.com`）。
   - <strong>归属业务空间</strong>：默认选择<strong>默认业务空间</strong>（数量上限与主账号配额见[时效性与限制](#apikey-limits)）。如需权限隔离、精细化模型访问控制或独立成本核算，请选择非默认业务空间，参见[业务空间管理](/zh/model-studio/permission-management-overview)。
   - <strong>权限</strong>：建议选择<strong>全部</strong>。如需精细控制，可选择<strong>自定义</strong>，配置可访问 IP 和可访问模型范围（数量限制见[时效性与限制](#apikey-limits)）。

3. 点击新创建的 API Key 旁的<Image src="https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/8412544571/p994217.png" alt="image" className="inline" noZoom />图标复制 API Key。

## 配置 API Key 到环境变量 <span id="20b17d4430qvt" /> <span id="6a82f1a968bhf" />

- <strong>方式一：在</strong>[<strong>第三方工具</strong>](/zh/model-studio/use-chat-client-or-development-tool)<strong>中进行配置</strong>

  如果在 Chatbox 等工具或平台中调用模型，您可能需要输入三个信息：

  - 本文获取的 API Key
  - Base URL：
~~~~

来源#8：`qwen-batch.md`，chunk=98，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
地域时，API Key也需要对应更换
          base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
      )

      # test.jsonl 是一个本地示例文件，purpose必须是batch
      file_object = client.files.create(file=Path("test.jsonl"), purpose="batch")

      print(file_object.model_dump_json())
      ```
    </Tab>

    <Tab title="OpenAI Node.js SDK">
      #### 请求示例 <span id="nodejs-request-title" /> <span id="nodejs-request-example" />

[同版本引用上下文]
```python
    batch = client.batches.create(
        input_file_id="file-batch-xxx",  # 直接使用已有文件 ID，无需重新上传
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    ```

    可通过 `client.files.list(purpose="batch")` 接口查询已上传的 Batch 文件 ID。
  </Note>

  <Tabs>
    <Tab title="OpenAI Python SDK">
      #### 请求示例 <span id="eadaf3f1ca7z5" /> <span id="6042ecfd84t57" />

      ```python
      import os
      from pathlib import Path
      from openai import OpenAI

      client = OpenAI(
          # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
          # 新加坡和北京地域的API Key不同。
          api_key=os.getenv("DASHSCOPE_API_KEY"),
          # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
          # 注意：切换地域时，API Key也需要对应更换
          base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
      )

      # test.jsonl 是一个本地示例文件，purpose必须是batch
      file_object = client.files.create(file=Path("test.jsonl"), purpose="batch")

      print(file_object.model_dump_json())
      ```
    </Tab>

    <Tab title="OpenAI Node.js SDK">
      #### 请求示例 <span id="nodejs-request-title" /> <span id="nodejs-request-example" />

      ```javascript expandable
      /**
       * 阿里云百炼 Batch API - 上传文件
       *
       * 若没有配置环境变量，可在代码中硬编码API Key：apiKey: 'sk-xxx'
       * 但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
       * 新加坡和北京地域的API Key不同。
       *
       * 安装依赖：npm install openai
       */
      const OpenAI = require('openai');
      const fs = require('fs');
~~~~

来源#9：`qwen-api-key.md`，chunk=22，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

~~~~text
- <strong>API Key 数量</strong>：账号+地域维度最多 50 个，不按业务空间限制；单个主账号最多 20 个业务空间（含默认业务空间）。
- <strong>自定义权限可选模型</strong>：最多 30 个，限于该业务空间已授权的模型。
- <strong>IP 白名单</strong>：最多 20 个地址或网段；IPv6 仅华北2（北京）地域支持，美国（弗吉尼亚）地域仅支持 IPv4；批量输入用英文逗号隔开。
- <strong>临时 API Key</strong>：最长 1800 秒。

## API 调用 <span id="4dd13345796cg" /> <span id="68bf80d8faprx" />

请访问[文本生成](/zh/model-studio/qwen-api-reference)以及更多模型的 API 参考。

OpenAI SDK 支持的模型，请参考[OpenAI 兼容](/zh/model-studio/toolkits-and-frameworks)。

## 常见问题 <span id="e6a57c054bfzy" /> <span id="4ed8cb6687hz6" />

### 无法创建 API Key？ <span id="9603b994a7nx6" />

[同版本引用上下文]
- <strong>API Key 数量</strong>：账号+地域维度最多 50 个，不按业务空间限制；单个主账号最多 20 个业务空间（含默认业务空间）。
- <strong>自定义权限可选模型</strong>：最多 30 个，限于该业务空间已授权的模型。
- <strong>IP 白名单</strong>：最多 20 个地址或网段；IPv6 仅华北2（北京）地域支持，美国（弗吉尼亚）地域仅支持 IPv4；批量输入用英文逗号隔开。
- <strong>临时 API Key</strong>：最长 1800 秒。

## API 调用 <span id="4dd13345796cg" /> <span id="68bf80d8faprx" />

请访问[文本生成](/zh/model-studio/qwen-api-reference)以及更多模型的 API 参考。

OpenAI SDK 支持的模型，请参考[OpenAI 兼容](/zh/model-studio/toolkits-and-frameworks)。

## 常见问题 <span id="e6a57c054bfzy" /> <span id="4ed8cb6687hz6" />

### 无法创建 API Key？ <span id="9603b994a7nx6" />

API Key 的创建需使用[超级管理员](/zh/model-studio/permission-management-overview#982297bd47p3i)或[业务空间管理员](/zh/model-studio/permission-management-overview#c82f37c2033vw)操作。

### 如何管理 API Key 的权限？ <span id="44eed06516tbh" />

API Key 的调用权限完全由其<strong>归属业务空间</strong>决定。<strong>同一空间内的 API Key 权限相同</strong>，无需为不同模型（如文生文、文生图、语音合成）创建不同的 API Key。

- <strong>默认业务空间下的 API Key：</strong>可调用所有[标准模型](/zh/model-studio/models)，以及默认业务空间内的[应用](/zh/model-studio/application-introduction)。
- <strong>子业务空间下的 API Key：</strong>可调用该子业务空间已获得[模型调用授权](/zh/model-studio/permission-management-overview)的标准模型，以及该业务空间内的应用。

<strong>调用在阿里云百炼</strong>[<strong>调优后的模型</strong>](/zh/model-studio/model-training-overview)<strong>：</strong>此类模型部署成功后，仅能用其所在业务空间的API Key调用。

如需在业务空间之外做更细粒度的控制，可在创建或编辑 API Key 时将<strong>权限</strong>切换为<strong>自定义</strong>，配置：

- <strong>IP 白名单规则</strong>：默认放通全部 IPv4，完整规则参见[时效性与限制](#apikey-limits)。
- <strong>访问模型范围</strong>：开关开启后，该 API Key 仅能调用已勾选的模型（限于该业务空间已授权的模型，数量限制参见[时效性与限制](#apikey-limits)）。

### 环境变量已设置，为何代码仍提示找不到 API Key？ <span id="a486eb2dc2p5y" />

具体原因如下：

- 情况一：<strong>没有设置永久性环境变量</strong>。临时环境变量只在当前终端会话中有效，对于已经启动的 IDE 或其他应用程序并不会生效。请参考本文中设置永久性环境变量的方法。
- 情况二：<strong>没有重启IDE、命令行工具或应用</strong>。
~~~~

来源#10：`qwen-batch.md`，chunk=178，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
<Tab title="curl(HTTP)">
        #### 请求示例 <span id="127c17fef9duj" /> <span id="314b7724e83p2" />

        ```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches?xxx同下方内容xxx
        # === 执行时请删除该注释 ===
        curl --request GET  'https://dashscope.aliyuncs.com/compatible-mode/v1/batches?after=batch_xxx&limit=2&ds_name=Batch&input_file_ids=file-batch-xxx,file-batch-xxx&status=completed,failed&create_after=20250303000000&create_before=20250320000000' \

[同版本引用上下文]
private static String readResponse(HttpURLConnection conn) throws Exception {
                int responseCode = conn.getResponseCode();
                InputStream is = (responseCode < 400) ? conn.getInputStream() : conn.getErrorStream();
                try (Scanner scanner = new Scanner(is, "UTF-8").useDelimiter("\\A")) {
                    return scanner.hasNext() ? scanner.next() : "";
                }
            }

            private static String parseField(String json, String regex) {
                Pattern pattern = Pattern.compile(regex);
                Matcher matcher = pattern.matcher(json);
                return matcher.find() ? matcher.group(1) : null;
            }
        }
        ```
      </Tab>

      <Tab title="curl(HTTP)">
        #### 请求示例 <span id="127c17fef9duj" /> <span id="314b7724e83p2" />

        ```bash
        # ======= 重要提示 =======
        # 新加坡和北京地域的API Key不同。
        # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/batches?xxx同下方内容xxx
        # === 执行时请删除该注释 ===
        curl --request GET  'https://dashscope.aliyuncs.com/compatible-mode/v1/batches?after=batch_xxx&limit=2&ds_name=Batch&input_file_ids=file-batch-xxx,file-batch-xxx&status=completed,failed&create_after=20250303000000&create_before=20250320000000' \
         -H "Authorization: Bearer $DASHSCOPE_API_KEY"
        ```

        > 将 `after=batch_id` 中的 `batch_id` 替换为实际值， `limit` 参数设置为返回任务的数量， `ds_name` 填写为任务名称片段，input\_file\_ids的值可填写多个文件ID， `status` 填写Batch任务的多个状态， `create_after` 和 `create_before` 的值填写为时间点。
      </Tab>
    </Tabs>

    #### 输入参数 <span id="be637ea3e500d" /> <span id="837b874cbaint" />
~~~~

来源#11：`qwen-batch.md`，chunk=70，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
- <strong>唯一标识</strong>：每个请求必须包含文件内唯一的 custom\_id 字段，用于匹配请求与结果

<strong>场景1：文本对话</strong>

示例文件内容：

```json
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
```

[同版本引用上下文]
```json
{"id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","custom_id":"1","response":{"status_code":200,"request_id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-bca7295b-67c3-4b1f-8239-d78323bb669f","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
{"id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","custom_id":"2","response":{"status_code":200,"request_id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-1e32a8ba-2b69-4dc4-be42-e2897eac9e84","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
```

## 执行正式任务 <span id="bad4ef1522g5k" /> <span id="759dd0eccesua" />

### 输入文件要求 <span id="0214fa4f9dxb3" /> <span id="bbf6655574dbn" />

- <strong>格式</strong>：UTF-8 编码的 JSONL（每行一个独立JSON对象）
- <strong>规模限制</strong>：单文件最多 50,000 个请求，且不超过 500 MB
- <strong>单行限制</strong>：每个JSON对象不超过 6 MB，且不超过模型上下文长度
- <strong>一致性要求</strong>：同一文件内所有请求须使用相同的模型及思考模式（如适用）
- <strong>唯一标识</strong>：每个请求必须包含文件内唯一的 custom\_id 字段，用于匹配请求与结果

<strong>场景1：文本对话</strong>

示例文件内容：

```json
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
```
~~~~

来源#12：`gpt-overview.md`，chunk=0，version=9feabad921a156d9a4741c5a7765bf77，HTTP=200

~~~~text
# GPT / OpenAI API：接入认证与请求追踪

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# API Overview

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：接入认证与请求追踪

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[API Overview](https://developers.openai.com/api/reference/overview)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# API Overview

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

Use this reference to look up OpenAI API endpoints, request and response
schemas, streaming events, client library methods, and shared behavior such as
authentication, errors, rate limits, and request IDs.

## Start here

1. Choose the API surface for your application:
   - [Responses](https://developers.openai.com/api/reference/responses/overview) for direct model requests, tool use, audio, image, and text inputs, and stateful interactions.
   - [Realtime API](https://developers.openai.com/api/docs/guides/realtime) for low-latency voice or audio sessions over WebRTC, WebSocket, or SIP. Use the [client events](https://developers.openai.com/api/reference/resources/realtime/client-events) and [server events](https://developers.openai.com/api/reference/resources/realtime/server-events) references while building sessions.
   - [Administration](https://developers.openai.com/api/reference/administration/overview) for organization workflows such as users, invites, projects, API keys, and audit logs.
2. Create credentials. Use a standard [API key](https://platform.openai.com/settings/organization/api-keys) for application requests, an [Admin API key](https://platform.openai.com/settings/organization/admin-keys) for Administration endpoints, or [workload identity federation](https://developers.openai.com/api/docs/guides/workload-identity-federation) for short-lived access tokens.
~~~~

## D06 · demo · diagnosis

本地Demo API请求 req_chain_37_rate 返回429，请核查并转人工客服。

判分要求：收集实际证据，保留明确转人工请求；仅工具成功并有工单号才声明创建成功

审阅：PASS。实际创建转人工记录并返回工单号，保留 Demo 范围和调用时证据。

### 原始回答

以下核查来自本项目的 Demo API，不代表查询了厂商的真实账户。

请求 req_chain_37_rate 在 2026-10-19T20:43:29.683000Z 返回 HTTP 429；该记录只说明当时的事件。

请求时观测支持的候选原因：请求频率限制。

建议：降低发送频率，按服务规则使用指数退避与随机抖动。

下一步：已达到人工核查条件，等待真实工单创建结果

人工工单已创建：CS_0af34d6a53174d8c9cbc

### 实际引用锚点
