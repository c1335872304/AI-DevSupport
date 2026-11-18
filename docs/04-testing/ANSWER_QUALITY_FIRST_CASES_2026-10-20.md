# 独立端到端回答评测：逐题原始回答与审阅证据

2026-10-20；本轮逐题原始输出，各轮证据分开保存，不覆盖历史失败。引用令牌不公开，正文与锚点摘要保留。

## E01 · deepseek · fact

文档校对：DeepSeek的JSON Output只设置response_format就够了吗？提示里应包含什么，如何避免JSON被截断，空content是否属于已知情况？

判分要求：response_format=json_object；提示含json并给格式样例；合理max_tokens避免截断；空content是已知可能情况，可调整prompt，不保证必然解决

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

以下按 DeepSeek API 文档逐项回答（仅适用于 DeepSeek API，不适用于其他厂商）：

**1. 只设置 response_format 够不够？**
不够。需要把 `response_format` 设为 `{'type': 'json_object'}`，但这只是启用 JSON 模式的条件之一；提示词中还必须包含 `json` 字样并给出 JSON 样例，同时要合理设置 `max_tokens`。来源#1

**2. 提示里应包含什么？**
用户传入的 system 或 user prompt 中必须含有 `json` 字样，并给出希望模型输出的 JSON 格式样例，以指导模型输出合法 JSON。来源#1

**3. 如何避免 JSON 被截断？**
需要合理设置 `max_tokens` 参数，防止 JSON 字符串被中途截断。来源#1
补充：如果 `finish_reason="length"`，表示生成超过了 `max_tokens` 或对话超过最大上下文长度，消息内容可能被部分截断。来源#6

**4. 空 content 是否属于已知情况？**
属于。文档明确说明：使用 JSON Output 功能时，API 有概率返回空的 content；官方正在积极优化，可尝试修改 prompt 以缓解。来源#1

**补充提醒（同属 JSON 模式注意事项）：** 使用 JSON 模式时，必须通过系统或用户消息指示模型生成 JSON，否则模型可能持续生成空白字符直到 token 限制，导致请求长时间运行并显得“卡住”。来源#6

以上均为文档通用规则，不代表任何具体账户或单次请求的实际状态。

来源#1: deepseek-json-output.md
来源#2: deepseek-fim-api.md
来源#3: deepseek-responses.md
来源#4: deepseek-prefix-completion.md
来源#5: deepseek-tool-calling.md
来源#6: deepseek-chat-completions.md
来源#7: deepseek-fim-api.md

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

来源#2：`deepseek-fim-api.md`，chunk=0，version=915e523f4c295d7081edf327bf11171e，HTTP=200

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

来源#3：`deepseek-responses.md`，chunk=0，version=47a4c8df60e15d7982216687963fc076，HTTP=200

~~~~text
# DeepSeek API：Responses 参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Responses API](https://api-docs.deepseek.com/zh-cn/api/create-response/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Responses API

```
POST /responses
```

以 OpenAI Responses API 格式创建模型响应。

该 API 是无状态的：服务端不存储响应与会话。多轮对话需要客户端在每次请求的 `input` 中回传完整对话历史。详细说明（含完整的参数兼容性表）请参考 [Responses API 指南](https://api-docs.deepseek.com/zh-cn/guides/responses_api)。

## Request

- application/json

### Body

required

model stringrequired

Possible values: [`deepseek-flash`, `deepseek-v4-pro`]

[同版本引用上下文]
# DeepSeek API：Responses 参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Responses API](https://api-docs.deepseek.com/zh-cn/api/create-response/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Responses API

```
POST /responses
```

以 OpenAI Responses API 格式创建模型响应。

该 API 是无状态的：服务端不存储响应与会话。多轮对话需要客户端在每次请求的 `input` 中回传完整对话历史。详细说明（含完整的参数兼容性表）请参考 [Responses API 指南](https://api-docs.deepseek.com/zh-cn/guides/responses_api)。

## Request

- application/json

### Body

required

model stringrequired

Possible values: [`deepseek-flash`, `deepseek-v4-pro`]

使用的模型的 ID。请使用 `deepseek-flash` 或 `deepseek-v4-pro`。

input string | object[]

nullable

模型的输入。既可以传纯字符串（视作一条 `user` 消息），也可以传输入 item 列表。

支持的输入 item 类型为 `message` / `function_call` / `function_call_output` / `custom_tool_call` / `custom_tool_call_output` / `reasoning` / `web_search_call`，其他类型会被忽略。消息角色支持 `user` / `assistant` / `system` / `developer`（`developer` 视同 `user`）。使用 `deepseek-flash` 模型时，`user` / `developer` 消息 item 以及 `function_call_output` / `custom_tool_call_output` item 的 `output` 中支持 `input_image` 内容块；`system` / `assistant` 消息中的图片将返回 `400` 错误。文件输入不支持。

`input` 与 `instructions` 至少传一个。

oneOf

- Text input

- Input item list

string

-

Array [

type string

Possible values: [`message`, `function_call`, `function_call_output`, `custom_tool_call`, `custom_tool_call_output`, `reasoning`, `web_search_call`]

输入 item 的类型。对于 `message` item，如果传了 `role`，此字段可省略。`custom_tool_call` / `custom_tool_call_output` item 配合 `apply_patch` custom 工具使用。`web_search_call` item 用于还原上一次服务端搜索的结果。

role string

Possible values: [`user`, `assistant`, `system`, `developer`]

用于 `message` item。消息作者的角色。`developer` 视同 `user`。

content string | object[]
~~~~

来源#4：`deepseek-prefix-completion.md`，chunk=1，version=4ebb1c1409b3573188a9f2105103b409，HTTP=200

~~~~text
息的 `prefix` 参数为 `True`。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了对话前缀续写的完整 Python 代码样例。在这个例子中，我们设置 `assistant` 开头的消息为 `"```python\n"` 来强制模型输出 python 代码，并设置 `stop` 参数为 `['```']` 来避免模型的额外解释。

````
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)messages = [    {"role": "user", "content": "Please write quick sort code"},    {"role": "assistant", "content": "```python\n", "prefix": True},]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,

[同版本引用上下文]
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

下面给出了对话前缀续写的完整 Python 代码样例。在这个例子中，我们设置 `assistant` 开头的消息为 `"```python\n"` 来强制模型输出 python 代码，并设置 `stop` 参数为 `['```']` 来避免模型的额外解释。

````
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)messages = [    {"role": "user", "content": "Please write quick sort code"},    {"role": "assistant", "content": "```python\n", "prefix": True},]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stop=["```"],)print(response.choices[0].message.content)
````
~~~~

来源#5：`deepseek-tool-calling.md`，chunk=0，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
# DeepSeek API：工具调用

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Tool Calls](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Tool Calls

Tool Calls 让模型能够调用外部工具，来增强自身能力。

## 非思考模式

### 样例代码

这里以获取用户当前位置的天气信息为例，展示了使用 Tool Calls 的完整 Python 代码。

Tool Calls 的具体 API 格式请参考[对话补全](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)文档。

[同版本引用上下文]
# DeepSeek API：工具调用

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Tool Calls](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Tool Calls

Tool Calls 让模型能够调用外部工具，来增强自身能力。

## 非思考模式

### 样例代码

这里以获取用户当前位置的天气信息为例，展示了使用 Tool Calls 的完整 Python 代码。

Tool Calls 的具体 API 格式请参考[对话补全](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)文档。

```
from openai import OpenAIdef send_messages(messages):    response = client.chat.completions.create(        model="deepseek-flash",        messages=messages,        tools=tools,        extra_body={"thinking": {"type": "disabled"}},    )    return response.choices[0].messageclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com",)tools = [    {        "type": "function",        "function": {            "name": "get_weather",            "description": "Get weather of a location, the user should supply a location first.",            "parameters": {                "type": "object",                "properties": {                    "location": {                        "type": "string",                        "description": "The city and state, e.g. San Francisco, CA",                    },                },                "required": ["location"],            },        },    },]messages = [{"role": "user", "content": "How's the weather in Hangzhou, Zhejiang?"}]message = send_messages(messages)print(f"User>\t {messages[0]['content']}")tool = message.tool_calls[0]messages.append(message)messages.append({"role": "tool", "tool_call_id": tool.id, "content": "24℃"})message = send_messages(messages)print(f"Model>\t {message.content}")
```

这个例子的执行流程如下：

- 用户：询问现在的天气
~~~~

来源#6：`deepseek-chat-completions.md`，chunk=9，version=acb1ddea03df5b2cb00d72d0f989cf84，HTTP=200

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

来源#7：`deepseek-fim-api.md`，chunk=4，version=915e523f4c295d7081edf327bf11171e，HTTP=200

~~~~text
采样温度，介于 0 和 2 之间。更高的值，如 0.8，会使输出更随机，而更低的值，如 0.2，会使其更加集中和确定。 我们通常建议可以更改这个值或者更改 `top_p`，但不建议同时对两者进行修改。

top_p numbernullable

Possible values: `<= 1`

Default value: `1`

作为调节采样温度的替代方案，模型会考虑前 `top_p` 概率的 token 的结果。所以 0.1 就意味着只有包括在最高 10% 概率中的 token 会被考虑。 取值必须大于 0 且不超过 1。我们通常建议修改这个值或者更改 `temperature`，但不建议同时对两者进行修改。

frequency_penalty deprecated

该参数已不再支持。传入该参数将不会产生任何效果。

presence_penalty deprecated

该参数已不再支持。传入该参数将不会产生任何效果。

## Responses

- 200

OK

- application/json

- Schema

- Example (from schema)

Schema

id stringrequired

补全响应的 ID。

choices

object[]

required

模型生成的补全内容的选择列表。

-

[同版本引用上下文]
采样温度，介于 0 和 2 之间。更高的值，如 0.8，会使输出更随机，而更低的值，如 0.2，会使其更加集中和确定。 我们通常建议可以更改这个值或者更改 `top_p`，但不建议同时对两者进行修改。

top_p numbernullable

Possible values: `<= 1`

Default value: `1`

作为调节采样温度的替代方案，模型会考虑前 `top_p` 概率的 token 的结果。所以 0.1 就意味着只有包括在最高 10% 概率中的 token 会被考虑。 取值必须大于 0 且不超过 1。我们通常建议修改这个值或者更改 `temperature`，但不建议同时对两者进行修改。

frequency_penalty deprecated

该参数已不再支持。传入该参数将不会产生任何效果。

presence_penalty deprecated

该参数已不再支持。传入该参数将不会产生任何效果。

## Responses

- 200

OK

- application/json

- Schema

- Example (from schema)

Schema

id stringrequired

补全响应的 ID。

choices

object[]

required

模型生成的补全内容的选择列表。

-

Array [

finish_reason stringrequired

Possible values: [`stop`, `length`, `content_filter`, `insufficient_system_resource`, `aborted`]

模型停止生成 token 的原因。

`stop`：模型自然停止生成，或遇到 `stop` 序列中列出的字符串。

`length` ：输出长度达到了模型上下文长度限制，或达到了 `max_tokens` 的限制。

`content_filter`：输出内容因触发过滤策略而被过滤。

`insufficient_system_resource`: 由于后端推理资源受限，请求被打断。

`aborted`：生成过程被中断。

index integerrequired

logprobs

object

nullable

required

text_offset integer[]token_logprobs number[]tokens string[]top_logprobs object[]text stringrequired
-

]

created integerrequired

标志补全请求开始时间的 Unix 时间戳（以秒为单位）。

model stringrequired

补全请求所用的模型。

system_fingerprint string

模型运行时的后端配置的指纹。

object stringrequired

Possible values: [`text_completion`]

object 的类型，一定为"text_completion"

usage

object

该对话补全请求的用量信息。

completion_tokens integerrequired

模型 completion 产生的 token 数。

prompt_tokens integerrequired

用户 prompt 所包含的 token 数。该值等于 `prompt_cache_hit_tokens + prompt_cache_miss_tokens`

prompt_tokens_details

object

required

prompt tokens 的详细信息。

cached_tokens integer

用户 prompt 中，命中上下文缓存的 token 数。与 `prompt_cache_hit_tokens` 相同。

prompt_cache_hit_tokens integerrequired

用户 prompt 中，命中上下文缓存的 token 数。
~~~~

## E02 · deepseek · fact

DeepSeek对话前缀续写要把哪种角色放在messages最后、加哪个标志，并使用什么Beta地址？请给三个配置要点。

判分要求：最后消息role=assistant；最后消息prefix=True；base_url=https://api.deepseek.com/beta

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

针对 DeepSeek 对话前缀续写（Beta），三个配置要点如下：

1. **最后一条消息的角色设为 `assistant`**：`messages` 列表里最后一条消息的 `role` 必须为 `assistant`。
2. **在该条消息上设置 `prefix` 参数为 `True`**：即最后一条 assistant 消息需带 `"prefix": true`，用于强制模型以该前缀内容开头续写。
3. **使用 Beta 地址**：设置 `base_url="https://api.deepseek.com/beta"` 以开启 Beta 功能。

补充说明：该功能沿用 Chat Completion API；样例中最后一条消息形如 `{"role": "assistant", "content": "```python\n", "prefix": True}`。以上为 DeepSeek API 的通用文档规则，不代表任何具体账户的配置状态。

来源#1: deepseek-prefix-completion.md
来源#2: deepseek-chat-completions.md
来源#3: deepseek-tool-calling.md
来源#4: deepseek-multi-round.md
来源#5: deepseek-rate-limits.md
来源#6: deepseek-fim-guide.md

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

[同版本引用上下文]
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

下面给出了对话前缀续写的完整 Python 代码样例。在这个例子中，我们设置 `assistant` 开头的消息为 `"```python\n"` 来强制模型输出 python 代码，并设置 `stop` 参数为 `['```']` 来避免模型的额外解释。

````
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)messages = [    {"role": "user", "content": "Please write quick sort code"},    {"role": "assistant", "content": "```python\n", "prefix": True},]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stop=["```"],)print(response.choices[0].message.content)
````
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

[同版本引用上下文]
role stringrequired

Possible values: [`user`]

该消息的发起角色，其值为 `user`。

name string

可以选填的参与者的名称，为模型提供信息以区分相同角色的参与者。

content stringnullablerequired

assistant 消息的内容。

role stringrequired

Possible values: [`assistant`]

该消息的发起角色，其值为 `assistant`。

name string

可以选填的参与者的名称，为模型提供信息以区分相同角色的参与者。

prefix bool

(Beta) 设置此参数为 true，来强制模型在其回答中以此 `assistant` 消息中提供的前缀内容开始。

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

- File content part
type stringrequired

Possible values: [`text`]

内容块的类型，此场景下为 `text`。

text stringrequired

文本内容。

type stringrequired

Possible values: [`image_url`]

内容块的类型，此场景下为 `image_url`。

image_url

object

required

url stringrequired

图片的 `http(s)` URL（最多 8192 个字符）或 base64 编码的 data URL（`data:image/jpeg;base64,...`）。支持的格式：JPEG、PNG、GIF、WebP。

detail string

Possible values: [`low`, `high`, `original`, `auto`]

控制图片的处理方式。`low` 将图片缩小到 512x512（更快、更省 token）；`high`、`original` 与 `auto` 保留原图。

type stringrequired

Possible values: [`file`]

内容块的类型，此场景下为 `file`。

file_id string

通过 [Files API](https://api-docs.deepseek.com/zh-cn/guides/files_api) 上传的文件 ID，形如 `file-api-...`。与 `file_data` 互斥。

file_data string

图片的 base64 编码 data URL（`data:image/jpeg;base64,...`）。与 `file_id` 互斥。

filename string

可选的文件名，仅在配合 `file_data` 时有效。

-

]
~~~~

来源#3：`deepseek-tool-calling.md`，chunk=5，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
tool-calls)。

## 在对话中间插入工具调用

在部分 Agent 场景中，客户端需要把并非由模型生成的工具调用及其结果，动态插入到对话历史的中间。各 API 格式对此的支持情况不同：

- [Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)（`/messages`）与 [Responses API](https://api-docs.deepseek.com/zh-cn/guides/responses_api) 支持在对话中间插入工具调用消息，也支持在对话中间插入 `system` 消息；

- Chat Completion 接口不支持在对话中间插入工具调用，但支持在对话中间插入 `system` 消息；如需插入工具调用，请改用 Anthropic API 或 Responses API。

## `strict` 模式（Beta）

在 `strict` 模式下，模型在输出 Function 调用时会严格遵循 Function 的 JSON Schema 的格式要求，以确保模型输出的 Function 符合用户的定义。在思考与非思考模式下的工具调用，均可使用 `strict` 模式。

要使用 `strict` 模式，需要：

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

来源#4：`deepseek-multi-round.md`，chunk=0，version=e53c4589cafa5c27b618be4c292e781a，HTTP=200

~~~~text
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

[同版本引用上下文]
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

```
from openai import OpenAIclient = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")# Round 1messages = [{"role": "user", "content": "What's the highest mountain in the world?"}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 1: {messages}")# Round 2messages.append({"role": "user", "content": "What is the second?"})response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 2: {messages}")
```

在第一轮请求时，传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"}]
```

在第二轮请求时：

- 要将第一轮中模型的输出添加到 `messages` 末尾

- 将新的提问添加到 `messages` 末尾

最终传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"},    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest."},    {"role": "user", "content": "What is the second?"}]
```
~~~~

来源#5：`deepseek-rate-limits.md`，chunk=3，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

~~~~text
。请不要在 `user_id` 中包含用户隐私信息。

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

来源#6：`deepseek-fim-guide.md`，chunk=1，version=882a8182be7d5ebf925e34de37f5d0eb，HTTP=200

~~~~text
eta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

```
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)response = client.completions.create(    model="deepseek-flash",    prompt="def fib(a):",    suffix="    return fib(a-1) + fib(a-2)",    max_tokens=128,)print(response.choices[0].text)
```

## 配置 Continue 代码补全插件

[同版本引用上下文]
# DeepSeek API：FIM 补全指南

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全（Beta）](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全（Beta）

在 [FIM (Fill In the Middle) 补全](https://api-docs.deepseek.com/zh-cn/api/create-completion)中，用户可以提供前缀和后缀（可选），模型来补全中间的内容。FIM 常用于内容续写、代码补全等场景。

## 注意事项

- 模型的最大补全长度为 4K。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

```
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)response = client.completions.create(    model="deepseek-flash",    prompt="def fib(a):",    suffix="    return fib(a-1) + fib(a-2)",    max_tokens=128,)print(response.choices[0].text)
```

## 配置 Continue 代码补全插件

[Continue](https://continue.dev) 是一款支持代码补全的 VSCode 插件，您可以参考[这篇文档](https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/continue/README_cn.md)来配置 Continue 以使用代码补全功能。
~~~~

## E03 · deepseek · insufficient

DeepSeek官方文档能否证明我这个账号在2026年12月31日一定享有5000 QPS且永不限流？请给可核验依据。

判分要求：不能据通用文档断言个人未来保障；不把本地Demo套餐当成DeepSeek生产账户证据；不得承诺5000QPS或永不限流

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论：不能。** 现有 DeepSeek 官方文档无法证明“你这个账号在 2026 年 12 月 31 日一定享有 5000 QPS 且永不限流”。理由如下：

1. **文档中的限速单位是“并发”，不是“QPS”。** 官方限速文档按账号给出的是不同模型的并发限制：`deepseek-flash` 为 2500，`deepseek-v4-pro` 为 500；一个请求从发出到模型响应完成记为一个并发。文档没有给出“5000 QPS”这一指标，也没有把并发数换算成 QPS。来源#1: deepseek-rate-limits.md

2. **文档明确存在超限后的限流机制，并非“永不限流”。** 文档写明：超过并发限度时会收到 HTTP 429 错误码；错误码文档也将 429 解释为“请求速率或并发达到上限”。来源#1: deepseek-rate-limits.md、来源#3: deepseek-errors.md

3. **文档不能证明你个人账号的具体配额。** 这些是通用规则文档，不是对你账号的核查结果；文档还说明本地业务工具不代表厂商生产账户核查。若需要更高并发，文档给出的路径是提交“账号扩容申请工单”，由厂商根据实际业务需求匹配并发量，而不是文档自动赋予某个固定额度。来源#1: deepseek-rate-limits.md

4. **文档不能对未来日期作出承诺。** 文档的核对日期为 2026-10-19，且明确“核对日期不等于规则生效日”；价格类文档也写明产品价格可能变动、厂商保留修改权利。因此无法据此确认 2026 年 12 月 31 日的配额状态。来源#1: deepseek-rate-limits.md、来源#9: deepseek-models-pricing.md

**可核验的下一步：**
- 如需确认你账号的实际并发配额，请通过文档中的“账号扩容申请工单”向 DeepSeek 提交申请并获取书面配额确认；
- 如你遇到实际被限流的情况，请提供 request_id、HTTP 状态码/错误码（如 429）、接口地址和发生时间，以便进一步核查该次请求。

本次未创建人工工单（handoff 未成功，无工单号）。

来源#1: deepseek-rate-limits.md
来源#2: deepseek-rate-limits.md
来源#3: deepseek-errors.md
来源#4: deepseek-token-usage.md
来源#5: deepseek-multi-round.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-tool-calling.md
来源#8: deepseek-balance.md
来源#9: deepseek-models-pricing.md

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

来源#2：`deepseek-rate-limits.md`，chunk=4，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

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

来源#3：`deepseek-errors.md`，chunk=0，version=a5df631500ec55a689b45d1a015e55ff，HTTP=200

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

来源#4：`deepseek-token-usage.md`，chunk=0，version=17decf9b6c8356c6a67b7826e5e99e08，HTTP=200

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

[同版本引用上下文]
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

[deepseek_tokenizer.zip](https://cdn.deepseek.com/api-docs/deepseek_v4_tokenizer.zip)

## 计算图片 Token 用量

您可以通过图片尺寸估算图片所占用的 token 数量。图片在进入模型前会被自动缩放，每张图片消耗的 token 数存在上限，详见[图像理解](https://api-docs.deepseek.com/zh-cn/guides/vision#token-usage)。

此处为估算值，实际处理时转换得到的 token 数量可能存在一定误差，请以接口返回的用量为准。

#### 图片 Token 计算器

宽度 (px)高度 (px)
~~~~

来源#5：`deepseek-multi-round.md`，chunk=0，version=e53c4589cafa5c27b618be4c292e781a，HTTP=200

~~~~text
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

[同版本引用上下文]
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

```
from openai import OpenAIclient = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")# Round 1messages = [{"role": "user", "content": "What's the highest mountain in the world?"}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 1: {messages}")# Round 2messages.append({"role": "user", "content": "What is the second?"})response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 2: {messages}")
```

在第一轮请求时，传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"}]
```

在第二轮请求时：

- 要将第一轮中模型的输出添加到 `messages` 末尾

- 将新的提问添加到 `messages` 末尾

最终传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"},    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest."},    {"role": "user", "content": "What is the second?"}]
```
~~~~

来源#6：`deepseek-quickstart.md`，chunk=0，version=62d53d8cc8cd54c0ae8b8af34e7acf41，HTTP=200

~~~~text
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

来源#7：`deepseek-tool-calling.md`，chunk=0，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
# DeepSeek API：工具调用

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Tool Calls](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Tool Calls

Tool Calls 让模型能够调用外部工具，来增强自身能力。

## 非思考模式

### 样例代码

这里以获取用户当前位置的天气信息为例，展示了使用 Tool Calls 的完整 Python 代码。

Tool Calls 的具体 API 格式请参考[对话补全](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)文档。

[同版本引用上下文]
# DeepSeek API：工具调用

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Tool Calls](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Tool Calls

Tool Calls 让模型能够调用外部工具，来增强自身能力。

## 非思考模式

### 样例代码

这里以获取用户当前位置的天气信息为例，展示了使用 Tool Calls 的完整 Python 代码。

Tool Calls 的具体 API 格式请参考[对话补全](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)文档。

```
from openai import OpenAIdef send_messages(messages):    response = client.chat.completions.create(        model="deepseek-flash",        messages=messages,        tools=tools,        extra_body={"thinking": {"type": "disabled"}},    )    return response.choices[0].messageclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com",)tools = [    {        "type": "function",        "function": {            "name": "get_weather",            "description": "Get weather of a location, the user should supply a location first.",            "parameters": {                "type": "object",                "properties": {                    "location": {                        "type": "string",                        "description": "The city and state, e.g. San Francisco, CA",                    },                },                "required": ["location"],            },        },    },]messages = [{"role": "user", "content": "How's the weather in Hangzhou, Zhejiang?"}]message = send_messages(messages)print(f"User>\t {messages[0]['content']}")tool = message.tool_calls[0]messages.append(message)messages.append({"role": "tool", "tool_call_id": tool.id, "content": "24℃"})message = send_messages(messages)print(f"Model>\t {message.content}")
```

这个例子的执行流程如下：

- 用户：询问现在的天气
~~~~

来源#8：`deepseek-balance.md`，chunk=0，version=b9d037f89e24599d92ff9324e5649c74，HTTP=200

~~~~text
# DeepSeek API：余额查询

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[查询余额](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 查询余额

```
GET /user/balance
```

查询账号余额

## Responses

- 200

OK, 返回用户余额详情

- application/json

- Schema

- Example (from schema)

- Example

Schema

is_available boolean

当前账户是否有余额可供 API 调用

balance_infos

object[]

-

Array [

currency string

Possible values: [`CNY`, `USD`]

货币，人民币或美元

total_balance string

总的可用余额，包括赠金和充值余额

granted_balance string

未过期的赠金余额

[同版本引用上下文]
# DeepSeek API：余额查询

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[查询余额](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 查询余额

```
GET /user/balance
```

查询账号余额

## Responses

- 200

OK, 返回用户余额详情

- application/json

- Schema

- Example (from schema)

- Example

Schema

is_available boolean

当前账户是否有余额可供 API 调用

balance_infos

object[]

-

Array [

currency string

Possible values: [`CNY`, `USD`]

货币，人民币或美元

total_balance string

总的可用余额，包括赠金和充值余额

granted_balance string

未过期的赠金余额

topped_up_balance string

充值余额

-

]

```
{  "is_available": true,  "balance_infos": [    {      "currency": "CNY",      "total_balance": "110.00",      "granted_balance": "10.00",      "topped_up_balance": "100.00"    }  ]}
```

```
{  "is_available": true,  "balance_infos": [    {      "currency": "CNY",      "total_balance": "110.00",      "granted_balance": "10.00",      "topped_up_balance": "100.00"    }  ]}
```

Loading...
~~~~

来源#9：`deepseek-models-pricing.md`，chunk=4，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

~~~~text
请注意，当前用户在 DeepSeek Harness/Claude Code/Codex 中使用 DeepSeek API 时，已经会通过 Server 端工具调用访问到 Search/Fetch 接口，这部分 Search/Fetch 接口调用目前未计费，并将于北京时间 2026 年 11 月 1 日 00:00 起按次收取调用费用。

接口用法与完整计费规则详见[网页搜索与抓取](https://api-docs.deepseek.com/zh-cn/guides/search)。

## 扣费规则

模型调用费用 = token 消耗量 × 模型单价；Search 和 Fetch 按上表中的成功请求次数计费。对应的费用将直接从充值余额或赠送余额中进行扣减。
当充值余额与赠送余额同时存在时，优先扣减赠送余额。

产品价格可能发生变动，DeepSeek 保留修改价格的权利。请您依据实际用量按需充值，定期查看此页面以获知最新价格信息。

[同版本引用上下文]
请注意，当前用户在 DeepSeek Harness/Claude Code/Codex 中使用 DeepSeek API 时，已经会通过 Server 端工具调用访问到 Search/Fetch 接口，这部分 Search/Fetch 接口调用目前未计费，并将于北京时间 2026 年 11 月 1 日 00:00 起按次收取调用费用。

接口用法与完整计费规则详见[网页搜索与抓取](https://api-docs.deepseek.com/zh-cn/guides/search)。

## 扣费规则

模型调用费用 = token 消耗量 × 模型单价；Search 和 Fetch 按上表中的成功请求次数计费。对应的费用将直接从充值余额或赠送余额中进行扣减。
当充值余额与赠送余额同时存在时，优先扣减赠送余额。

产品价格可能发生变动，DeepSeek 保留修改价格的权利。请您依据实际用量按需充值，定期查看此页面以获知最新价格信息。
~~~~

## E04 · qwen · fact

把千问北京地域的Key放到新加坡的OpenAI兼容地址，能作为跨地域通用Key使用吗？Base URL还必须匹配哪一项？

判分要求：地域Key独立，不能跨地域通用；Base URL必须与同一计费方案的API Key配套

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**不能作为跨地域通用 Key 使用。**

根据文档规则，API Key 与 Base URL 必须属于同一地域；北京地域的 API Key 配新加坡地域的 Base URL 属于“地域不匹配”，会触发鉴权错误。文档明确以“华北2（北京）地域的 API Key + 新加坡地域的 Base URL”作为地域不匹配的例子。切换地域时，API Key 也需要对应更换。

**Base URL 还必须匹配：API Key 所在的地域。**

各地域 OpenAI 兼容地址示例：
- 北京：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 新加坡：`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

另外，文档还提到业务空间专属域名方案（北京 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`、新加坡 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`），其中 `{WorkspaceId}` 需替换为真实业务空间 ID，现有域名仍可正常使用。

以上为通用规则说明，不代表您账户的实际状态；如需核查具体某次调用失败，请提供 request_id、HTTP 状态/错误码、接口地址或发生时间。

来源#1: qwen-errors.md
来源#2: qwen-batch.md
来源#3: qwen-batch.md
来源#4: qwen-batch.md
来源#5: qwen-batch.md
来源#6: qwen-structured-outputs.md
来源#7: qwen-chat-completions.md

### 实际引用锚点

来源#1：`qwen-errors.md`，chunk=145，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
.dashscope.aliyuncs.com/v1)</a>；Token Plan 团队版的专属 Base URL 可在控制台<strong>我的订阅</strong>的 API Key 区域查看。请确认同时更新了 API Key 和 Base URL，具体配置方法请分别参见接入AI工具与[快速开始](/zh/model-studio/token-plan-team-quickstart)。
- <strong>地域不匹配</strong>：API Key 和 Base URL 属于不同的地域，例如使用了华北2（北京）地域的 API Key 和新加坡地域的 Base URL。请确认您使用的 API Key 位于[北京](https://bailian.console.aliyun.com/settings/api-key)地域页面或[新加坡](https://bailian.console.aliyun.com/settings/api-key)地域页面，或[美国](https://bailian.console.aliyun.com/us-east-1)地域页面。各地域对应的 Base URL 如下：

[同版本引用上下文]
> 此方式便于调试，请勿用于生产环境。
- <strong>填写错误</strong>：阿里云百炼的 API Key 以 `sk-` 开头，请确认未误填其他模型提供商的密钥，且复制时未包含多余空格或换行符。
- <strong>套餐专属 API Key（Coding Plan / Token Plan 团队版）</strong>：Coding Plan 与 Token Plan 团队版均提供以 `sk-sp-` 开头的专属 API Key，<strong>必须配合各自的专属 Base URL 使用</strong>，不可与通用 API Key/Base URL 混用（混用会返回本鉴权错误）。其中 Coding Plan 的专属地址为 <a href="https://coding.dashscope.aliyuncs.com/v1">[https://coding.dashscope.aliyuncs.com/v1](https://coding.dashscope.aliyuncs.com/v1)</a>；Token Plan 团队版的专属 Base URL 可在控制台<strong>我的订阅</strong>的 API Key 区域查看。请确认同时更新了 API Key 和 Base URL，具体配置方法请分别参见接入AI工具与[快速开始](/zh/model-studio/token-plan-team-quickstart)。
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

[同版本引用上下文]
```java Java（HTTP） expandable
    import java.io.*;
    import java.net.HttpURLConnection;
    import java.net.URL;
    import java.nio.file.Files;
    import java.nio.file.Paths;
    import java.util.Scanner;

    /**
     * 阿里云百炼 Batch API 测试 - 使用 HTTP API 调用
     *
     * 前置条件：
     * 1. 确保已经设置环境变量 DASHSCOPE_API_KEY
     * 2. 准备好测试文件 test_model.jsonl（在项目根目录）
     *
     * 地域配置说明：
     * - 北京地域：https://dashscope.aliyuncs.com/compatible-mode/v1
     * - 新加坡地域：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
     */
    public class BatchAPITest {

        // 北京地域的 Base URL（默认）
        private static final String BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
        // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
        // private static final String BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";

        private static String API_KEY;

        public static void main(String[] args) throws Exception {
            // 从环境变量获取 API Key
            API_KEY = System.getenv("DASHSCOPE_API_KEY");
            if (API_KEY == null || API_KEY.isEmpty()) {
                System.err.println("错误: 请设置环境变量 DASHSCOPE_API_KEY");
                System.exit(1);
            }

            System.out.println("=== 开始 Batch API 测试 ===\n");

            try {
                // Step 1: 上传文件
                System.out.println("步骤 1: 上传包含请求信息的 JSONL 文件...");
                String fileId = uploadFile("test_model.jsonl");
                System.out.println("✓ 文件上传成功，文件ID: " + fileId + "\n");

                // Step 2: 创建 Batch 任务
                System.out.println("步骤 2: 创建 Batch 任务...");
                String batchId = createBatch(fileId);
                System.out.println("✓ Batch 任务创建成功，任务ID: " + batchId + "\n");
~~~~

来源#4：`qwen-batch.md`，chunk=111，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
```bash
      # ======= 重要提示 =======
      # 新加坡和北京地域的API Key不同。
      # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/files
      # === 执行时请删除该注释 ===
      curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/files \
      -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
      --form 'file=@"test.jsonl"' \
      --form 'purpose="batch"'
      ```
    </Tab>
  </Tabs>

  #### 返回示例 <span id="e755ceb45blu0" />

[同版本引用上下文]
```bash
      # ======= 重要提示 =======
      # 新加坡和北京地域的API Key不同。
      # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1/files
      # === 执行时请删除该注释 ===
      curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/files \
      -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
      --form 'file=@"test.jsonl"' \
      --form 'purpose="batch"'
      ```
    </Tab>
  </Tabs>

  #### 返回示例 <span id="e755ceb45blu0" />

  ```json
  {
      "id": "file-batch-xxx",
      "bytes": 437,
      "created_at": 1742304153,
      "filename": "test.jsonl",
      "object": "file",
      "purpose": "batch",
      "status": "processed",
      "status_details": null
  }
  ```
</Accordion>

<Accordion title="2. 创建 Batch 任务">
  使用上传文件返回的文件ID 或OSS路径 创建 Batch 任务。

  <Tabs>
    <Tab title="OpenAI Python SDK">
      #### 请求示例 <span id="3d1d320515wzr" /> <span id="79338d585616c" />

      ```python
      import os
      from openai import OpenAI

      client = OpenAI(
          # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
          # 新加坡和北京地域的API Key不同。
          api_key=os.getenv("DASHSCOPE_API_KEY"),
          # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
          # 注意：切换地域时，API Key也需要对应更换
          base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
      )
~~~~

来源#5：`qwen-batch.md`，chunk=163，version=242cba5e060250b996ca68582c1a898c，HTTP=200

~~~~text
client = OpenAI(
            # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
            # 新加坡和北京地域的API Key不同。
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

[同版本引用上下文]
client = OpenAI(
            # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
            # 新加坡和北京地域的API Key不同。
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        batches = client.batches.list(after="batch_xxx", limit=2,extra_query={'ds_name':'任务名称','input_file_ids':'file-batch-xxx,file-batch-xxx','status':'completed,expired','create_after':'20250304000000','create_before':'20250306123000'})
        print(batches)
        ```
      </Tab>

      <Tab title="OpenAI Node.js SDK">
        #### 请求示例 <span id="10e57ca3a38he" /> <span id="efbdeeba2e3nc" />

        ```javascript expandable
        /**
         * 阿里云百炼 Batch API - 查询任务列表
         *
         * 若没有配置环境变量，可在代码中硬编码API Key：apiKey: 'sk-xxx'
         * 但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
         * 新加坡和北京地域的API Key不同。
         *
         * 安装依赖：npm install openai
         */
        const OpenAI = require('openai');

        // 北京地域配置（默认）
        const BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1';
        // 如果使用新加坡地域，请将上面的 BASE_URL 替换为：
        // const BASE_URL = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1';
        // 注意：切换地域时，API Key也需要对应更换

        const apiKey = process.env.DASHSCOPE_API_KEY;
        if (!apiKey) {
            console.error('错误: 请设置环境变量 DASHSCOPE_API_KEY');
            console.error('或在代码中设置: const apiKey = "sk-xxx";');
            process.exit(1);
        }

        const client = new OpenAI({
            apiKey: apiKey,
            baseURL: BASE_URL
        });
~~~~

来源#6：`qwen-structured-outputs.md`，chunk=17，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
ps://help.aliyun.com/zh/model-studio/get-api-key
            apiKey: process.env.DASHSCOPE_API_KEY,
            // 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
            baseURL: "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        });

[同版本引用上下文]
### 返回结果 <span id="8977446b570mi" />

        ```plaintext
        {
          "姓名": "刘五",
          "年龄": 34
        }
        ```
      </Tab>

      <Tab title="Node.js">
        ```javascript expandable
        import OpenAI from "openai";

        const openai = new OpenAI({
            // 如果没有配置环境变量，请用API Key将下行替换为：apiKey: "sk-xxx"
            // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            apiKey: process.env.DASHSCOPE_API_KEY,
            // 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
            baseURL: "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        });

        const completion = await openai.chat.completions.create({
            model: "qwen3.8-max",
            messages: [
                {
                    role: "system",
                    content: "请抽取用户的姓名与年龄信息，以JSON格式返回"
                },
                {
                    role: "user",
                    content: "大家好，我叫刘五，今年34岁，邮箱是liuwu@example.com，平时喜欢打篮球和旅游"
                }
            ],
            response_format: {
                type: "json_object"
            }
        });

        const jsonString = completion.choices[0].message.content;
        console.log(jsonString);
        ```

        ### 返回结果 <span id="749fedf19cbe2" />

        ```plaintext
        {
          "姓名": "刘五",
          "年龄": 34
        }
        ```
      </Tab>
~~~~

来源#7：`qwen-chat-completions.md`，chunk=4，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
HTTP 请求地址：`POST https://{WorkspaceId}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>
</Tabs>

调用时请将`{WorkspaceId}`替换为真实的[业务空间ID](/zh/model-studio/regions#h2_migrate_domain)。

您需要先[获取与配置 API Key](/zh/model-studio/get-api-key)。若通过OpenAI SDK进行调用，需要[安装SDK](/zh/model-studio/install-sdk)。

<Tip>
  阿里云百炼为华北2（北京）、新加坡、中国香港地域推出了业务空间专属域名，<strong>能够为推理请求提供卓越的性能和更高的稳定性</strong>，建议迁移至新域名：

[同版本引用上下文]
HTTP 请求地址：`POST https://{WorkspaceId}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1/chat/completions`
  </Tab>
</Tabs>

调用时请将`{WorkspaceId}`替换为真实的[业务空间ID](/zh/model-studio/regions#h2_migrate_domain)。

您需要先[获取与配置 API Key](/zh/model-studio/get-api-key)。若通过OpenAI SDK进行调用，需要[安装SDK](/zh/model-studio/install-sdk)。

<Tip>
  阿里云百炼为华北2（北京）、新加坡、中国香港地域推出了业务空间专属域名，<strong>能够为推理请求提供卓越的性能和更高的稳定性</strong>，建议迁移至新域名：

  - 华北2（北京）地域：从 `https://dashscope.aliyuncs.com` 迁移至 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`
  - 新加坡地域：从 `https://dashscope-intl.aliyuncs.com` 迁移至 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`

  其中 `{WorkspaceId}` 为您的业务空间 ID，可在阿里云百炼控制台的<strong>业务空间详情</strong>页面查看。现有域名仍可正常使用。
</Tip>

<table bordertype="no-border" style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
  <colgroup>
    <col style={{ width: "50%" }} />

    <col style={{ width: "50%" }} />
  </colgroup>

  <tbody>
    <tr>
      <td style={{ verticalAlign: "top" }}>
        ## 请求体 <span id="afcd41d2b57zf" />

        <strong>model</strong>`string`<strong>（必选）</strong>

        模型名称。

        支持的模型：Qwen 大语言模型（商业版、开源版）、Qwen-VL、Qwen-Coder、Qwen-Omni、Qwen-Math、DeepSeek（阿里云直供、硅基流动直供、快手万擎直供）、Kimi（阿里云直供、月之暗面直供）、GLM（阿里云直供）、MiniMax（阿里云直供、稀宇科技直供）。

        > 三方直供模型仅在中国站的华北2（北京）地域可用，调用前需先在百炼控制台开通对应服务（以 SiliconFlow DeepSeek 为例：搜索 deepseek → 找到 SiliconFlow DeepSeek 模型卡片 → 单击立即开通 → 确认授权）。

        > Qwen-Audio不支持OpenAI兼容协议，仅支持DashScope协议。

        <strong>具体模型名称和计费，请参见</strong>[百炼控制台](https://bailian.console.aliyun.com/model/market)。

        <strong>messages</strong>`array`<strong>（必选）</strong>

        传递给大模型的上下文，按对话顺序排列。

        <Accordion title="消息类型" defaultOpen>
          System Message`object`（可选）
~~~~

## E05 · qwen · fact

Qwen text-embedding-v4可以一次提交15行、每行8192 Token，同时指定256维吗？请分别判定批量条数、单行长度和维度。

判分要求：每批最多10行，15行应拆分；每行最多8192 Token，边界允许；256维受支持

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

针对 Qwen text-embedding-v4，按三项分别判定如下：

1. **批量条数：不可以一次提交 15 行。** text-embedding-v3 / v4 在输入为字符串列表或文件时，最多支持 **10 条（行）**。15 行超出上限。来源#2、来源#3

2. **单行长度：可以，每行 8192 Token 在限制内。** text-embedding-v3 / v4 在列表输入时，每条（行）最长支持 **8,192 Token**。来源#2、来源#3

3. **维度：可以指定 256 维。** text-embedding-v4 支持 64~2048 维自定义，dimensions 可选值包含 256（默认 1024）。来源#1、来源#5

**结论：** 三项中“每行 8192 Token”和“256 维”符合规则，但“一次 15 行”不符合，需拆分为每批不超过 10 行提交。

补充说明：以上为文档通用规则，不代表您账户的实际配额或调用结果；限流方面 text-embedding-v4 的 RPM/TPM 限制可另行参考来源#6、来源#7。

来源#1: qwen-embedding-api.md
来源#2: qwen-embedding-api.md
来源#3: qwen-embedding-api.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-v4.md
来源#6: qwen-rate-limits.md
来源#7: qwen-rate-limits.md

### 实际引用锚点

来源#1：`qwen-embedding-api.md`，chunk=20，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
- <strong>输入为字符串</strong>：最长支持 <strong>2,048</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>25</strong> 条（行），每条（行）最长支持 <strong>2,048</strong> Token。

        <strong>dimensions</strong> `integer` <strong>可选</strong>

        指定的向量维度，必须为以下值之一：`2560（仅适用于qwen3.7-text-embedding）、`2048（仅适用于`text-embedding-v4`）、1536（仅适用于`text-embedding-v4`）1024、768、512、256、128 或 64，默认值为1024。

        <strong>encoding\_format</strong> `string` <strong>可选</strong>

        用于控制返回的Embedding格式，入参支持`float`和`base64`，出参的Embedding数据也支持`float`和`base64`两种格式。实际返回格式取决于请求路由到的网关：

[同版本引用上下文]
- <strong>输入为字符串</strong>：最长支持 <strong>2,048</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>25</strong> 条（行），每条（行）最长支持 <strong>2,048</strong> Token。

        <strong>dimensions</strong> `integer` <strong>可选</strong>

        指定的向量维度，必须为以下值之一：`2560（仅适用于qwen3.7-text-embedding）、`2048（仅适用于`text-embedding-v4`）、1536（仅适用于`text-embedding-v4`）1024、768、512、256、128 或 64，默认值为1024。

        <strong>encoding\_format</strong> `string` <strong>可选</strong>

        用于控制返回的Embedding格式，入参支持`float`和`base64`，出参的Embedding数据也支持`float`和`base64`两种格式。实际返回格式取决于请求路由到的网关：

        - <strong>老网关</strong>：无论`encoding_format`设置为`float`还是`base64`，均只返回`float`类型数据，不支持输出`base64`数据。
        - <strong>新网关</strong>：

          - <strong>短请求</strong>：按`encoding_format`设置的格式返回数据。
          - <strong>长请求</strong>：内部路由到老网关，仅返回`float`类型数据。
      </td>

      <td>
        <Tabs>
          <Tab title="输入字符串">
            <CodeGroup dropdown>
              ```python Python
              import os
              from openai import OpenAI

              client = OpenAI(
                  api_key=os.getenv("DASHSCOPE_API_KEY"),  # 如果您没有配置环境变量，请在此处用您的API Key进行替换
                  # 以下为华北2（北京）地域的URL，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的URL不同。
                  base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
              )

              completion = client.embeddings.create(
                  model="qwen3.7-text-embedding",
                  input='衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买',
                  dimensions=1024, # 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                  encoding_format="float"
              )

              print(completion.model_dump_json())
              ```
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

[同版本引用上下文]
<Tabs>
  <Tab title="公共云">
    <strong>使用SDK调用时需配置的base\_url：</strong>https\://\{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1

    <strong>使用HTTP方式调用时需配置的endpoint：</strong>POST https\://\{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding

    调用时请将`{WorkspaceId}`替换为真实的[业务空间ID](/zh/model-studio/regions#h2_migrate_domain)。
  </Tab>
</Tabs>

<table bordertype="no-border" style={{ display: "table", tableLayout: "fixed", width: "100%" }}>
  <colgroup>
    <col style={{ width: "50%" }} />

    <col style={{ width: "50%" }} />
  </colgroup>

  <tbody>
    <tr>
      <td>
        ### 请求体 <span id="afcd41d2b57zf" />

        <strong>model</strong>`string`<strong>必选</strong>

        调用的模型，参考[模型概览](/zh/model-studio/text-embedding-synchronous-api#0e41425c577u4)表格中的模型名称进行选择。

        <strong>input</strong>`string`*或*`array<string>`<strong>必选</strong>

        输入待处理的文本。可以是字符串（string）、字符串列表（array）或文件（file）。不同模型版本支持的文本长度和批量大小不同，具体如下：

        - <strong>qwen3.7-text-embedding、qwen3.7-text-embedding-flash 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>128,000</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>20</strong> 条（行），每条（行）最长支持 <strong>128,000</strong> Token。
        - <strong>text-embedding-v3 / v4 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>8,192</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>10</strong> 条（行），每条（行）最长支持 <strong>8,192</strong> Token。
        - <strong>text-embedding-v1 / v2 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>2,048</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>25</strong> 条（行），每条（行）最长支持 <strong>2,048</strong> Token。

        <strong>text\_type</strong> `string`<strong>可选</strong>
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

[同版本引用上下文]
您需要已[获取与配置 API Key](/zh/model-studio/get-api-key)并[配置API Key到环境变量](/zh/model-studio/configure-api-key-through-environment-variables)。如果通过SDK调用，还需要[安装DashScope SDK](/zh/model-studio/install-sdk)。请将示例代码中的 `DASHSCOPE_API_HOST` 替换为获取的 API Host。

## OpenAI兼容 <span id="f4e8c45964o4x" />

<Tabs>
  <Tab title="公共云">
    <strong>使用SDK调用时需配置的base\_url：</strong>`https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`

    <strong>使用HTTP方式调用时需配置的endpoint：</strong>`POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/embeddings`

    调用时请将`{WorkspaceId}`替换为真实的[业务空间ID](/zh/model-studio/regions#h2_migrate_domain)。
  </Tab>
</Tabs>

<table bordertype="no-border" style={{ display: "table", tableLayout: "fixed", width: "100%" }}>
  <colgroup>
    <col style={{ width: "50%" }} />

    <col style={{ width: "50%" }} />
  </colgroup>

  <tbody>
    <tr>
      <td>
        ### 请求体 <span id="d150fab3e6rgl" />

        <strong>model</strong>`string`<strong>必选</strong>

        调用的模型名称，参考[模型概览](/zh/model-studio/text-embedding-synchronous-api#0e41425c577u4)表格中的模型名称进行选择。

        <strong>input</strong>`array<string> 或 string 或 file`<strong>必选</strong>

        输入待处理的文本。可以是字符串（string）、字符串列表（array）或文件（file）。不同模型版本支持的文本长度和批量大小不同，具体如下：

        - <strong>qwen3.7-text-embedding 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>128,000</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>20</strong> 条（行），每条（行）最长支持 <strong>128,000</strong> Token。
        - <strong>text-embedding-v3 / v4 模型：</strong>

          - <strong>输入为字符串</strong>：最长支持 <strong>8,192</strong> Token。
          - <strong>输入为字符串列表或文件</strong>：最多支持 <strong>10</strong> 条（行），每条（行）最长支持 <strong>8,192</strong> Token。
        - <strong>text-embedding-v1 / v2 模型：</strong>
~~~~

来源#4：`qwen-embedding-api.md`，chunk=85，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
.model("qwen3.7-text-embedding")
                                  .texts(batch)
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();

[同版本引用上下文]
public final class Main {
                  private static final int DASHSCOPE_MAX_BATCH_SIZE = 10;

                  public static void main(String[] args) {
                      // 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                      Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
                      List<String> inputs = Arrays.asList(
                              "风急天高猿啸哀",
                              "渚清沙白鸟飞回",
                              "无边落木萧萧下",
                              "不尽长江滚滚来"
                      );

                      TextEmbeddingResult result = null;
                      int batchCounter = 0;

                      for (int i = 0; i < inputs.size(); i += DASHSCOPE_MAX_BATCH_SIZE) {
                          List<String> batch = inputs.subList(i, Math.min(i + DASHSCOPE_MAX_BATCH_SIZE, inputs.size()));
                          TextEmbeddingParam param = TextEmbeddingParam.builder()
                                  .model("qwen3.7-text-embedding")
                                  .texts(batch)
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();
~~~~

来源#5：`qwen-embedding-v4.md`，chunk=0，version=52339fbb07d75e06a3325c666b05528e，HTTP=200

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

[同版本引用上下文]
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

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际
~~~~

来源#6：`qwen-rate-limits.md`，chunk=745，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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

[同版本引用上下文]
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
~~~~

来源#7：`qwen-rate-limits.md`，chunk=740，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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

[同版本引用上下文]
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
~~~~

## E06 · qwen · insufficient

Qwen的qwen-demo-exclusive-2099模型最大输出是否为512K？请确认准确的最大输出长度和官方发布日期。

判分要求：指出当前资料不足以确认该型号及限制/发布日期；不能把其他Qwen型号的参数套给该未知型号

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

关于 **qwen-demo-exclusive-2099** 这个具体模型，我无法确认其最大输出长度或官方发布日期。

**核查结果：**
- 已检索的文档中**没有出现** `qwen-demo-exclusive-2099` 这一模型名称，因此无法确认其最大输出是否为 512K，也无法给出准确的最大输出长度和发布日期。
- 文档中涉及的模型（如 qwen3.8-max、qwen3.7-max、Qwen3.5 系列等）的 `max_tokens` / `max_completion_tokens` 说明属于**通用参数规则**，不能直接套用到该模型上，也不能据此推断该模型的输出上限。

**通用规则参考（仅说明参数含义，不代表该模型的具体取值）：**
- `max_tokens` 与 `max_completion_tokens` 的默认值和最大值均为模型的最大输出长度；`max_completion_tokens` 限制完整输出（思维链 + 回答），`max_tokens` 仅限制回答部分。来源#2、来源#3
- 若输出超过设定值，生成会提前停止，`finish_reason` 返回 `length`。来源#2、来源#3

**下一步建议：**
1. 请确认模型名称是否准确（是否为内部/试用模型代号），或提供该模型的官方文档链接、控制台模型列表截图。
2. 如需确认某次实际调用是否因输出长度受限，请提供 `request_id`、HTTP 状态/错误码、接口地址或发生时间，以便进一步核查。

目前未创建人工工单。

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

[同版本引用上下文]
<Accordion title="功能说明">
                fps有两个功能：

                - 输入视频文件时，控制抽帧频率，每 `1/fps` 秒抽取一帧。

                  > 适用于 [Qwen-VL](/zh/model-studio/vision)、[MiniMax/MiniMax-M3](/zh/model-studio/minimax-api-by-minimax) 与[QVQ 模型](/zh/model-studio/visual-reasoning)。
                - 告知模型相邻帧之间的时间间隔，帮助其更好地理解视频的时间动态。同时适用于输入视频文件与图像列表时。该功能同时支持视频文件和图像列表输入，适用于事件时间定位或分段内容摘要等场景。

                  > 支持Qwen3.7、Qwen3.6、Qwen3.5、`Qwen3-VL`、`Qwen2.5-VL`、Qwen3.8-Omni-Flash、Qwen3.5-Omni与QVQ模型。

                较大的`fps`适合高速运动的场景（如体育赛事、动作电影等），较小的`fps`适合长视频或内容偏静态的场景。
              </Accordion>

              <Accordion title="示例值">
                - 图像列表传入：`{"video":["https://xx1.jpg",...,"https://xxn.jpg"]，"fps":2}`
                - 视频文件传入：`{"video": "https://xx1.mp4"，"fps":2}`
              </Accordion>

              <strong>min\_pixels</strong>`integer`（可选）

              设定输入图像或视频帧的最小像素阈值。当输入图像或视频帧的像素小于`min_pixels`时，会将其进行放大，直到总像素高于`min_pixels`。适用型号及取值见下方说明。

              <Accordion title="取值范围">
                - <strong>输入图像：</strong>

                  - `qwen3.8-max`、`qwen3.8-max-0902`、`qwen3.8-flash`、`qwen3.8-2.4t-a95b`、`qwen3.8-27b`、Qwen3.7、Qwen3.6、Qwen3.5、Qwen3-VL：默认值和最小值均为：`65536`
                  - `qwen3.8-omni-flash`、Qwen3.5-Omni ：默认值和最小值均为： `24576`
                  - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值和最小值均为`3136`
                - <strong>输入视频文件或图像列表：</strong>

                  - `qwen3.8-max`、`qwen3.8-max-0902`、`qwen3.8-flash`、`qwen3.8-2.4t-a95b`、`qwen3.8-27b`、`qwen3.8-omni-flash`、Qwen3.7、Qwen3.6、Qwen3.5、`Qwen3.5-Omni`、Qwen3-VL（包括商业版和开源版）：默认值为`65536`，最小值为`4096`
                  - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值为`50176`，最小值为`3136`
              </Accordion>
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

[同版本引用上下文]
- deepseek-v4.1-flash、deepseek-v4-pro、deepseek-v4-pro-0813、deepseek-v4-flash-0731：模型回答与思维链内容之和的最大 Token 数。模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。
        - glm-5.3：`max_tokens` 为模型回答与思维链内容之和的最大 Token 数，模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。glm-5.3 会忽略 `thinking_budget` 参数。
        - glm-5.2：不传入 `thinking_budget` 参数时，`max_tokens` 为模型回答与思维链内容之和的最大 Token 数，模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`；传入 `thinking_budget` 参数时，`max_tokens` 仅为模型回答的最大 Token 数，思维链部分的 Token 数由 `thinking_budget` 单独控制。
        - 其他模型：模型回答的最大 Token 数（不包含思维链）。若生成内容超过此值，生成将提前停止，返回的 `finish_reason` 为 `length`。

        默认值与最大值均为模型的最大输出长度。

        > Java SDK中为<strong>maxTokens</strong>（模型为千问VL/Audio时，Java SDK中为<strong>maxLength，</strong>在 2.18.4 版本之后支持也设置为 maxTokens）\*。\*通过HTTP调用时，请将 <strong>max\_tokens</strong>放入 <strong>parameters</strong> 对象中。

        <strong>max\_completion\_tokens</strong>`integer`（可选）

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

        > 实际输出 Token 数与设置的 `max_completion_tokens` 值之间最多可能存在 10 个 Token 的误差。

        > Java SDK 暂不支持该参数。通过 HTTP 调用时，请将 <strong>max\_completion\_tokens</strong>放入 <strong>parameters</strong> 对象中。

        <strong>seed</strong>`integer`（可选）
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

[同版本引用上下文]
<strong>strict</strong>`boolean`（可选）

            是否严格遵循 `schema` 定义的结构。推荐设置为 `true`。
          </Accordion>
        </Accordion>

        <strong>max\_tokens</strong>`integer` （可选， <strong>即将废弃</strong> ）

        > 该参数即将废弃，新接入请使用 `max_completion_tokens`。

        该参数的含义随模型不同，具体如下：

        - deepseek-v4.1-flash、deepseek-v4-pro、deepseek-v4-pro-0813、deepseek-v4-flash-0731：模型回答与思维链内容之和的最大 Token 数。模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。
        - glm-5.3：`max_tokens` 为模型回答与思维链内容之和的最大 Token 数，模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`。glm-5.3 会忽略 `thinking_budget` 参数。
        - glm-5.2：不传入 `thinking_budget` 参数时，`max_tokens` 为模型回答与思维链内容之和的最大 Token 数，模型输出超过此值时生成将提前停止，返回的 `finish_reason` 为 `length`；传入 `thinking_budget` 参数时，`max_tokens` 仅为模型回答的最大 Token 数，思维链部分的 Token 数由 `thinking_budget` 单独控制。
        - 其他模型：模型回答的最大 Token 数（不包含思维链）。若生成内容超过此值，生成将提前停止，返回的 `finish_reason` 为 `length`。

        默认值与最大值均为模型的最大输出长度。

        <strong>max\_completion\_tokens</strong>`integer`（可选）

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

        > 实际输出 Token 数与设置的 `max_completion_tokens` 值之间最多可能存在 10 个 Token 的误差。

        <strong>vl\_high\_resolution\_images</strong>`boolean`（可选）默认值为`false`
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

[同版本引用上下文]
### This model only support stream mode, please enable the stream parameter to access the model. / current user api does not support http call. <span id="stream-only-model" />

<strong>原因：</strong> 模型仅支持[流式输出](/zh/model-studio/stream)，但调用时未启用流式输出。

<strong>解决方案：</strong> 请使用[流式输出](/zh/model-studio/stream)方式调用模型。

### This model does not support enable\_search. <span id="d86ef92f928in" />

<strong>原因：</strong> 当前模型不支持[联网搜索](/zh/model-studio/web-search)能力，但指定了`enable_search`参数为`true`。

<strong>解决方案：</strong> 请调用支持联网搜索能力的模型。

### 暂时不支持当前设置的语种！ <span id="fc465a0e45f4a" />

<strong>原因：</strong> 使用 Qwen-MT 模型时，传入的 `source_lang` 或 `target_lang` 格式错误，或不在[支持的语言](/zh/model-studio/machine-translation#038d2865bbydc)里。

<strong>解决方案：</strong> 请传入正确格式的英文名或语种编码。

### The incremental\_output parameter must be "true" when enable\_thinking is true <span id="cabf71f55e154" />

<strong>原因：</strong> 模型开启思考模式时仅支持增量流式输出，未将`incremental_output`参数设置为`true`。

<strong>解决方案：</strong> 请将`incremental_output`参数设置为`true`再调用，API将返回增量内容。

### The incremental\_output parameter of this model cannot be set to False. <span id="bad5900569uaz" />

<strong>原因：</strong> 模型仅支持增量流式输出，未将`incremental_output`参数设置为`true`。

<strong>解决方案：</strong> 请将`incremental_output`参数设置为`true`再调用，API将返回增量内容。

### Range of input length should be \[1, xxx]（InternalError.Algo.InvalidParameter） <span id="81221bf732m4b" />

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

[同版本引用上下文]
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

        <Accordion title="属性">
          <strong>voice</strong>`string` <strong>（必选）</strong>

          输出音频的音色。请参见[非实时（Qwen-Omni）](/zh/model-studio/qwen-omni)。

          <strong>format</strong>`string` <strong>（必选）</strong>

          输出音频的格式，仅支持设定为`wav`。
        </Accordion>

        <strong>temperature</strong>`float`（可选）

        采样温度，控制模型生成文本的多样性。

        temperature越高，生成的文本更多样，反之，生成的文本更确定。

        取值范围： \[0, 2)

        temperature与top\_p均可以控制生成文本的多样性，建议只设置其中一个值。更多说明，请参见[概述](/zh/model-studio/text-generation)。
~~~~

来源#6：`qwen-dashscope.md`，chunk=31，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
40`，最大值为：`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值为`1003520` ，最大值为`12845056`

                  - 当`vl_high_resolution_images`为`True`时：

                    - `Qwen3.7、Qwen3.6、Qwen3.5`、Qwen3-VL：`max_pixels`无效，输入图像的最大像素固定为`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：`max_pixels`无效，输入图像的最大像素固定为`12845056`
                - <strong>输入视频文件或图像列表：</strong>

[同版本引用上下文]
<strong>max\_pixels</strong>`integer`（可选）

              用于设定输入图像或视频帧的最大像素阈值。当输入图像或视频的像素在`[min_pixels, max_pixels]`区间内时，模型会按原图进行识别。当输入图像像素大于`max_pixels`时，会将图像进行缩小，直到总像素低于`max_pixels`。

              <Accordion title="取值范围">
                - <strong>输入图像：</strong>

                  `max_pixels` 的取值与是否开启`vl_high_resolution_images`参数有关。

                  - 当`vl_high_resolution_images`为`False`时：

                    - `Qwen3.7、Qwen3.6、Qwen3.5`、`Qwen3-VL`：默认值为`2621440`，最大值为：`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值为`1003520` ，最大值为`12845056`

                  - 当`vl_high_resolution_images`为`True`时：

                    - `Qwen3.7、Qwen3.6、Qwen3.5`、Qwen3-VL：`max_pixels`无效，输入图像的最大像素固定为`16777216`
                    - `Qwen2.5-VL`开源系列及`QVQ`系列模型：`max_pixels`无效，输入图像的最大像素固定为`12845056`
                - <strong>输入视频文件或图像列表：</strong>

                  - `qwen3.7系列、qwen3.6系列、qwen3.5系列、qwen3-vl-plus`系列：默认值为`655360`，最大值为`2048000`
                  - 其他`Qwen3-VL`开源模型：默认值`655360`，最大值为`786432`
                  - `Qwen2.5-VL`开源系列及`QVQ`系列模型：默认值为`501760`，最大值为`602112`
              </Accordion>

              <Accordion title="示例值">
                - 输入图像：`{"type": "image_url","image_url": {"url":"https://xxxx.jpg"},"max_pixels": 8388608}`
                - 输入视频文件时：`{"type": "video_url","video_url": {"url":"https://xxxx.mp4"},"max_pixels": 655360}`
                - 输入图像列表时：`{"type": "video","video": ["https://xx1.jpg",...,"https://xxn.jpg"],"max_pixels": 655360}`
              </Accordion>

              <strong>total\_pixels</strong>`integer`（可选）

              用于限制从视频中抽取的所有帧的总像素（单帧图像像素 × 总帧数）。如果视频总像素超过此限制，系统将对视频帧进行缩放，但仍会确保单帧图像的像素值在`[min_pixels, max_pixels]`范围内。适用于 Qwen-VL、QVQ 模型。

              对于抽帧数量较多的长视频，可适当降低此值以减少Token消耗和处理时间，但这可能会导致图像细节丢失。
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

[同版本引用上下文]
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
~~~~

## E07 · gpt · fact

OpenAI后台响应处于queued或in_progress时应怎样轮询？何时停止？要启动后台执行应设置哪个参数？

判分要求：background=true启动后台；GET/retrieve响应并在queued或in_progress继续轮询；离开这两种状态即终态，停止轮询

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

以下仅针对 OpenAI Responses API 的后台模式（background mode）说明通用规则，不代表任何个人账户或某次请求的实际状态。

**1. 如何轮询**
- 使用 Responses 的 GET 接口查询后台请求状态（示例为 `GET https://api.openai.com/v1/responses/{response_id}`），在状态为 `queued` 或 `in_progress` 期间持续轮询。
- 文档示例中的轮询间隔为 2 秒（如 JavaScript 的 `setTimeout(..., 2000)`、Python 的 `sleep(2)`、Go 的 `time.Sleep(2 * time.Second)`、Ruby 的 `sleep(2)`）。这是示例值，文档未规定必须使用该间隔。

**2. 何时停止**
- 当状态离开 `queued` 和 `in_progress` 时，即进入最终（terminal）状态，此时应停止轮询并读取结果（如 `output_text`）。
- 另外，文档也提供了取消进行中响应的接口（`POST /v1/responses/{response_id}/cancel`），可用于主动终止。

**3. 启动后台执行的参数**
- 创建响应时设置 `background: true`（各语言 SDK 中对应 `background=True` / `BackgroundModeEnabled = true` / `Background: openai.Bool(true)` 等）。
- 文档示例使用的模型为 `gpt-6-astra`，该参数属于 OpenAI Responses API 的后台模式，不适用于其他厂商。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-background.md
来源#4: gpt-conversation-state.md
来源#5: gpt-webhooks.md
来源#6: gpt-rate-limits.md
来源#7: gpt-prompt-engineering.md

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

来源#4：`gpt-conversation-state.md`，chunk=2，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
com/api/docs/guides/reasoning#phase-parameter) for details.

## Manually manage conversation state

While each text generation request is independent and stateless, you can still implement **multi-turn conversations** by providing additional messages as parameters to your text generation request. Consider a knock-knock joke:

  Manually construct a past conversation

```javascript
import OpenAI from "openai";

const openai = new OpenAI();

[同版本引用上下文]
# GPT / OpenAI API：多轮会话状态

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Conversation state

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI provides a few ways to manage conversation state, which is important for preserving information across multiple messages or turns in a conversation.

  When troubleshooting cases where GPT-5.5 treats an intermediate update as
    the final answer, verify your integration preserves the assistant message
    `phase` field correctly. See [Phase
    parameter](https://developers.openai.com/api/docs/guides/reasoning#phase-parameter) for details.

## Manually manage conversation state

While each text generation request is independent and stateless, you can still implement **multi-turn conversations** by providing additional messages as parameters to your text generation request. Consider a knock-knock joke:

  Manually construct a past conversation

```javascript
import OpenAI from "openai";

const openai = new OpenAI();

const response = await openai.responses.create({
  model: "gpt-6-astra",
  input: [
    { role: "user", content: "knock knock." },
    { role: "assistant", content: "Who's there?" },
    { role: "user", content: "Orange." },
  ],
});

console.log(response.output_text);
```

```python
from openai import OpenAI

client = OpenAI()
~~~~

来源#5：`gpt-webhooks.md`，chunk=15，version=044234a8b47552e9be6fe27688178fdd，HTTP=200

~~~~text
on http://127.0.0.1:#{port}/webhook"
$stdout.flush
server.start
response_workers.each(&:join)
```

To see a webhook like this one in action, you can set up a webhook endpoint in the OpenAI dashboard subscribed to `response.completed`, and then make an API request to [generate a response in background mode](https://developers.openai.com/api/docs/guides/background).

You can also trigger test events with sample data from the [webhook settings page](https://platform.openai.com/settings/project/webhooks).

Generate a background response

[同版本引用上下文]
response.status = 200
  response.body = "ok"
rescue OpenAI::Errors::InvalidWebhookSignatureError, ArgumentError => error
  warn "Invalid signature: #{error.message}"
  response.status = 400
  response.body = "Invalid signature"
ensure
  server.shutdown if ENV["OPENAI_WEBHOOK_EXIT_AFTER_REQUEST"] == "1"
end

Signal.trap("INT") { server.shutdown }
port = server.listeners.first.addr[1]
puts "Webhook server listening on http://127.0.0.1:#{port}/webhook"
$stdout.flush
server.start
response_workers.each(&:join)
```

To see a webhook like this one in action, you can set up a webhook endpoint in the OpenAI dashboard subscribed to `response.completed`, and then make an API request to [generate a response in background mode](https://developers.openai.com/api/docs/guides/background).

You can also trigger test events with sample data from the [webhook settings page](https://platform.openai.com/settings/project/webhooks).

Generate a background response

```bash
curl https://api.openai.com/v1/responses \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $OPENAI_API_KEY" \
-d '{
  "model": "gpt-6-astra",
  "input": "Write a very long novel about otters in space.",
  "background": true
}'
```

```javascript
import OpenAI from "openai";
const client = new OpenAI();

const resp = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true,
});

console.log(resp.status);
```

```python
from openai import OpenAI

client = OpenAI()

resp = client.responses.create(
    model="gpt-6-astra",
    input="Write a very long novel about otters in space.",
    background=True,
)

print(resp.status)
```

```go
package main

import (
	"context"
	"fmt"
~~~~

来源#6：`gpt-rate-limits.md`，chunk=7，version=7c736b1dd2a954cc9f41609a86e3a928，HTTP=200

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

来源#7：`gpt-prompt-engineering.md`，chunk=25，version=06a6f123d65e5c8da62ec8967759ee00，HTTP=200

~~~~text
Msg)
        .reasoning(Reasoning.builder().effort(ReasoningEffort.LOW).build())
        .build();

client.responses().create(params).output().stream()
    .flatMap(item -> item.message().stream())
    .flatMap(message -> message.content().stream())
    .flatMap(content -> content.outputText().stream())
    .forEach(text -> System.out.println(text.text()));
```

[同版本引用上下文]
response = client.responses.create(
    model="gpt-6-astra",
    reasoning={"effort": "low"},
    instructions="Talk like a pirate.",
    input="Are semicolons optional in JavaScript?",
)

print(response.output_text)
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

	response, err := client.Responses.New(context.Background(), responses.ResponseNewParams{
		Model:        "gpt-6-astra",
		Instructions: openai.String("Talk like a pirate."),
		Reasoning: responses.ReasoningParam{
			Effort: responses.ReasoningEffortLow,
		},
		Input: responses.ResponseNewParamsInputUnion{
			OfString: openai.String("Are semicolons optional in JavaScript?"),
		},
	})
	if err != nil {
		panic(err)
	}

	fmt.Println(response.OutputText())
}
```

```java
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.Reasoning;
import com.openai.models.ReasoningEffort;
import com.openai.models.responses.ResponseCreateParams;

String semicolonsDevMsg = "Talk like a pirate.";

String semicolonsPrompt = "Are semicolons optional in JavaScript?";

ResponseCreateParams params =
    ResponseCreateParams.builder()
        .model("gpt-6-astra")
        .input(semicolonsPrompt)
        .instructions(semicolonsDevMsg)
        .reasoning(Reasoning.builder().effort(ReasoningEffort.LOW).build())
        .build();

client.responses().create(params).output().stream()
    .flatMap(item -> item.message().stream())
    .flatMap(message -> message.content().stream())
    .flatMap(content -> content.outputText().stream())
    .forEach(text -> System.out.println(text.text()));
```
~~~~

## E08 · gpt · fact

OpenAI的JSON mode和Structured Outputs，对required字段与枚举约束的保证相同吗？如果模型拒绝，能直接当作符合业务Schema的成功数据吗？

判分要求：JSON mode保证合法JSON，不保证JSON Schema；Structured Outputs约束Schema；拒绝需单独识别处理，不能直接当作Schema业务成功数据

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**不相同。** 两者对 required 字段和枚举约束的保证强度不同：

- **JSON mode**：只保证模型输出是有效 JSON（且文档说明存在一些边缘情况需要你自行检测处理）；它**不保证**输出匹配你指定的 Schema，因此不能据此认为 required 字段一定齐全、枚举值一定合法。
- **Structured Outputs**：文档明确说明它会确保模型生成的响应符合你提供的 JSON Schema，因此不需要担心模型遗漏 required 键或编造无效的枚举值。使用时需在请求中指定 `text.format` 为 `json_schema` 并设置 `strict: true`，同时提供 schema。

**模型拒绝时，不能直接当作符合业务 Schema 的成功数据。** Structured Outputs 的文档把“显式拒绝（Explicit refusals）”列为一项特性：基于安全策略的模型拒绝可以被程序化检测。也就是说，拒绝是一种需要单独识别和处理的结果，而不是符合 Schema 的业务数据；应当先检测拒绝，再决定是否重试或走其他流程，不能把它当作成功数据直接使用。

补充适用范围：以上是 OpenAI API 的通用规则说明，不代表你个人账户或某次实际调用的状态；另外，部分 Schema 约束（如示例中的数值范围）文档注明“尚未支持微调模型”，具体支持范围以官方 supported schemas 为准。

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

来源#2：`gpt-structured-outputs.md`，chunk=1，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
URL.

JSON is one of the most widely used formats in the world for applications to exchange data.

Structured Outputs is a feature that ensures the model will always generate responses that adhere to your supplied [JSON Schema](https://json-schema.org/overview/what-is-jsonschema), so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value.

Some benefits of Structured Outputs include:

[同版本引用上下文]
# GPT / OpenAI API：结构化输出

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Structured model outputs

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

JSON is one of the most widely used formats in the world for applications to exchange data.

Structured Outputs is a feature that ensures the model will always generate responses that adhere to your supplied [JSON Schema](https://json-schema.org/overview/what-is-jsonschema), so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value.

Some benefits of Structured Outputs include:

1. **Reliable type-safety:** No need to validate or retry incorrectly formatted responses
1. **Explicit refusals:** Safety-based model refusals are now programmatically detectable
1. **Simpler prompting:** No need for strongly worded prompts to achieve consistent formatting

In addition to supporting JSON Schema in the REST API, the OpenAI libraries for [Python](https://github.com/openai/openai-python/blob/main/helpers.md#structured-outputs-parsing-helpers) and [JavaScript](https://github.com/openai/openai-node/blob/master/helpers.md#structured-outputs-parsing-helpers) also let you define object schemas using [`pydantic.BaseModel`](https://docs.pydantic.dev/latest/) and [`z.object`](https://zod.dev/) respectively. Below, you can see how to extract information from unstructured text that conforms to a schema defined in code.

The Ruby SDK supports schemas defined with Sorbet `T::Struct` and returns typed parsed results.
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

[同版本引用上下文]
```json
{
    "name": "weather_data",
    "strict": true,
    "schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get the weather for"
            },
            "unit": {
                "type": ["string", "null"],
                "description": "The unit to return the temperature in",
                "enum": ["F", "C"]
            },
            "value": {
                "type": "number",
                "description": "The actual temperature value in the location",
                // highlight-start
                "minimum": -130,
                "maximum": 130
                // highlight-end
            }
        },
        "additionalProperties": false,
        "required": [
            "location", "unit", "value"
        ]
    }
}
```

Note these constraints are [not yet supported for fine-tuned
  models](#some-type-specific-keywords-are-not-yet-supported).

#### Root objects must not be `anyOf` and must be an object

Note that the root level object of a schema must be an object, and not use `anyOf`. A pattern that appears in Zod (as one example) is using a discriminated union, which produces an `anyOf` at the top level. So code such as the following won't work:

```javascript
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const BaseResponseSchema = z.object({
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

[同版本引用上下文]
```json
{
    "type": "function",
    "name": "get_weather",
    "description": "Retrieves current weather for the given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and country e.g. Bogotá, Colombia"
            },
            "units": {
                //highlight-start
                "type": "string",
                //highlight-end
                "enum": ["celsius", "fahrenheit"],
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

Specifically for fine tuned models:

1. Schemas undergo additional processing on the first request (and are then cached). If your schemas vary from request to request, this may result in higher latencies.
2. Schemas are cached for performance, and are not eligible for [zero data retention](https://developers.openai.com/api/docs/models#how-we-use-your-data).

## Streaming

Streaming can be used to surface progress by showing which function is called as the model fills its arguments, and even displaying the arguments in real time.

Streaming function calls works like streaming regular responses: you set `stream` to `true` and get different `event` objects.

Streaming function calls
~~~~

来源#6：`gpt-prompt-engineering.md`，chunk=12，version=06a6f123d65e5c8da62ec8967759ee00，HTTP=200

~~~~text
model into a single string. This may be useful as a shortcut to access text output from the model.

In addition to plain text, you can also have the model return structured data in JSON format - this feature is called [**Structured Outputs**](https://developers.openai.com/api/docs/guides/structured-outputs).

## Choosing a model

[同版本引用上下文]
```bash
curl "https://api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-6-astra",
        "input": "Write a one-sentence bedtime story about a unicorn."
    }'
```

An array of content generated by the model is in the `output` property of the response. In this simple example, we have just one output which looks like this:

```json
[
  {
    "id": "msg_67b73f697ba4819183a15cc17d011509",
    "type": "message",
    "role": "assistant",
    "content": [
      {
        "type": "output_text",
        "text": "Under the soft glow of the moon, Luna the unicorn danced through fields of twinkling stardust, leaving trails of dreams for every child asleep.",
        "annotations": []
      }
    ]
  }
]
```

**The `output` array often has more than one item in it!** It can contain tool calls, data about reasoning tokens generated by [reasoning models](https://developers.openai.com/api/docs/guides/reasoning), and other items. It is not safe to assume that the model's text output is present at `output[0].content[0].text`.

Some of our [official SDKs](https://developers.openai.com/api/docs/libraries) include an `output_text` property on model responses for convenience, which aggregates all text outputs from the model into a single string. This may be useful as a shortcut to access text output from the model.

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

## E09 · gpt · insufficient

仅凭OpenAI官方文档，能确认我的组织已启用Zero Data Retention，且下周所有请求均不留存吗？请判断我的组织实际状态。

判分要求：无法从通用文档确认组织开通状态或所有请求未来行为；不能把后台模式或通用保留规则等同于个人组织配置

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论：不能。** 仅凭这些 OpenAI 官方文档，无法确认您的组织已启用 Zero Data Retention（ZDR），也无法确认下周所有请求均不留存。

**逐项说明：**

1. **能否确认组织已启用 ZDR？——不能。**
   文档只说明通用规则：未启用 ZDR 的组织，提示缓存默认保留 `24h`；已启用 ZDR 的组织，默认保留 `in_memory`；并提示选择前应核实模型和组织可用的保留策略（来源#1、来源#5）。这属于通用规则，不能证明您组织实际处于哪种状态。

2. **能否确认下周所有请求均不留存？——不能。**
   文档说明：Responses 默认会被存储，Chat Completions 对新账户默认存储，可通过 `store: false` 关闭存储（来源#4）；Response 对象默认保存 30 天，可通过 `store: false` 关闭（来源#6）。这些是产品行为规则，既不构成对您组织配置的核验，也不能作为对“下周”这一未来状态的承诺。

3. **您的组织实际状态：证据中没有可核验的组织级事实（verifiedFacts 为空），因此无法判断。** 文档本身也注明“本地业务工具不代表厂商生产账户核查”（来源#2、来源#3、来源#7）。

**建议的下一步：**
- 在 OpenAI 平台的组织设置/合规页面核实 ZDR 是否已启用，并核对所用模型与接口的可用保留策略（来源#1、来源#5）。
- 对需要不留存的请求，在调用中显式设置 `store: false`（来源#4、来源#6），不要依赖默认值。
- 如需我们进一步核查某次具体请求的留存情况，请提供 request_id、接口地址、HTTP 状态/错误码或发生时间等锚点信息。

本次未创建人工工单（handoffResult.success 不为 true）。

来源#1: gpt-prompt-caching.md
来源#2: gpt-conversation-state.md
来源#3: gpt-overview.md
来源#4: gpt-responses-migration.md
来源#5: gpt-prompt-caching.md
来源#6: gpt-conversation-state.md
来源#7: gpt-reasoning-practices.md

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

[同版本引用上下文]
- Organizations _without_ Zero Data Retention enabled default to `24h`.
- Organizations _with_ Zero Data Retention enabled default to `in_memory`.

Verify the available retention policies for your model and organization before selecting a value.

<a id="where-caching-happens-and-how-long-it-lasts"></a>

<a id="cache-location-and-duration"></a>

<a id="cache-location-and-lifetime"></a>

## Cache location

Cached states live on individual machines, where traffic above 15 requests per minute can lead to overflow routing. A request can reuse a cached prefix only if it reaches a machine holding a matching entry that has not expired. Routing requests to the right machine is therefore important for cache reuse.

Caches are not shared across organizations and cannot be reused across [regional processing boundaries](https://developers.openai.com/api/docs/guides/your-data#data-residency-controls).

OpenAI handles routing automatically. Within an organization and processing region, routing for a given model depends on:

- Current machine load and available capacity.
- A hash of the initial tokens after the hidden OpenAI content, including tool definitions when present. The number of tokens hashed varies by model.
- A supplied [`prompt_cache_key`](#prompt-cache-keys), which separates cache reuse between groups of requests and helps optimize cache routing on models before GPT-5.6.

<a id="prompt-cache-keys"></a>

### Prompt cache keys
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

[同版本引用上下文]
# GPT / OpenAI API：多轮会话状态

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Conversation state

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI provides a few ways to manage conversation state, which is important for preserving information across multiple messages or turns in a conversation.

  When troubleshooting cases where GPT-5.5 treats an intermediate update as
    the final answer, verify your integration preserves the assistant message
    `phase` field correctly. See [Phase
    parameter](https://developers.openai.com/api/docs/guides/reasoning#phase-parameter) for details.

## Manually manage conversation state

While each text generation request is independent and stateless, you can still implement **multi-turn conversations** by providing additional messages as parameters to your text generation request. Consider a knock-knock joke:

  Manually construct a past conversation

```javascript
import OpenAI from "openai";

const openai = new OpenAI();

const response = await openai.responses.create({
  model: "gpt-6-astra",
  input: [
    { role: "user", content: "knock knock." },
    { role: "assistant", content: "Who's there?" },
    { role: "user", content: "Orange." },
  ],
});

console.log(response.output_text);
```

```python
from openai import OpenAI

client = OpenAI()
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

来源#4：`gpt-responses-migration.md`，chunk=86，version=bbd8a4ad224250d4bdd8ced7d2638f8e，HTTP=200

~~~~text
n the chain are billed as input tokens in the API.

<a id="4-decide-when-to-use-statefulness"></a>

### 4. Decide when to store state

Responses are stored by default. Chat Completions are stored by default for new accounts. To disable storage in either API, set `store: false`.

Some organizations, such as those with Zero Data Retention (ZDR) requirements, cannot use the Responses API in a stateful way due to compliance or data retention policies.

[同版本引用上下文]
Console.WriteLine(second.GetOutputText());
```

```ruby
require "openai"

client = OpenAI::Client.new

first = client.responses.create(
  model: "gpt-6-astra",
  input: "What is the capital of France?",
  store: true
)

second = client.responses.create(
  model: "gpt-6-astra",
  previous_response_id: first.id,
  input: "And its population?",
  store: true
)

puts(second.output_text)
```

Even when using `previous_response_id`, all previous input tokens for responses in the chain are billed as input tokens in the API.

<a id="4-decide-when-to-use-statefulness"></a>

### 4. Decide when to store state

Responses are stored by default. Chat Completions are stored by default for new accounts. To disable storage in either API, set `store: false`.

Some organizations, such as those with Zero Data Retention (ZDR) requirements, cannot use the Responses API in a stateful way due to compliance or data retention policies. To support these cases, OpenAI offers encrypted reasoning items, allowing you to keep your workflow stateless while still benefiting from reasoning items.

To stop storing state while still using reasoning:

- Set `store: false` in the [store field](https://developers.openai.com/api/reference/resources/responses/methods/create#responses_create-store).
- Preserve and replay every returned reasoning item. Each item includes `encrypted_content` by default when you create a response.
~~~~

来源#5：`gpt-prompt-caching.md`，chunk=34，version=a338ee9707c1548d9fc03fe54bf3257f，HTTP=200

~~~~text
### Earlier models

Use `prompt_cache_retention`, with supported values that depend on the model:

- `in_memory`: Entries typically remain active for around 5 to 10 minutes of inactivity, up to one hour.
- `24h`: Extended retention typically keeps entries available for around 30 minutes and can retain them for up to 24 hours.

**Retention defaults and Zero Data Retention**

Prompt caching may store encrypted key/value tensors in GPU-local storage as application state. For models that support both `in_memory` and `24h`, the default depends on your organization's data retention policy:

[同版本引用上下文]
- **Explicit-only mode:** The first 2 and latest 50 explicit breakpoints.
- **Implicit mode:** The first 2 and latest 50 explicit breakpoints, the implicit breakpoint, up to 20 earlier eligible message endings, and the endpoint of the initial consecutive block of developer messages. This lets implicit mode reuse a prefix ending at an earlier message without explicit breakpoints there.

## Cache lifetime

Cache entries are not stored indefinitely. A later request can reuse a cached prefix only while its entry remains available, and reusing the prefix refreshes its lifetime without another cache-write charge. The lifetime and retention settings [depend on the model](#summary-of-model-differences).

<a id="prompt-cache-retention"></a>

<a id="cache-lifetime-gpt-5-6-and-later"></a>

### GPT-5.6 and later

Use `prompt_cache_options.ttl` to control the minimum cache lifetime. The only supported value, `30m`, is also the default. A cached prefix remains eligible for reuse for 30 minutes after its most recent write or reuse, though OpenAI may retain it longer.

<a id="extended-prompt-cache-retention"></a>

<a id="cache-lifetime-earlier-models"></a>

### Earlier models

Use `prompt_cache_retention`, with supported values that depend on the model:

- `in_memory`: Entries typically remain active for around 5 to 10 minutes of inactivity, up to one hour.
- `24h`: Extended retention typically keeps entries available for around 30 minutes and can retain them for up to 24 hours.

**Retention defaults and Zero Data Retention**

Prompt caching may store encrypted key/value tensors in GPU-local storage as application state. For models that support both `in_memory` and `24h`, the default depends on your organization's data retention policy:
~~~~

来源#6：`gpt-conversation-state.md`，chunk=49，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
_response_id` set to `null` and pass full input context.

##### Data retention for model responses

      Response objects are saved for 30 days by default. They can be viewed in the dashboard
      [logs](https://platform.openai.com/logs?api=responses) page or
      [retrieved](https://developers.openai.com/api/reference/resources/responses/methods/retrieve) via the API.
      You can disable this behavior by setting `store` to `false`
      when creating a Response.

[同版本引用上下文]
The connection-local cache keeps recent previous responses in memory for low-latency continuation. When you use `stream_id`, each lane can retain its latest response; `previous_response_id` still controls lineage, so a new lane can fork from a response on another lane while that response remains available. If an uncached ID cannot be resolved, send a new turn with `previous_response_id` set to `null` and pass full input context.

##### Data retention for model responses

      Response objects are saved for 30 days by default. They can be viewed in the dashboard
      [logs](https://platform.openai.com/logs?api=responses) page or
      [retrieved](https://developers.openai.com/api/reference/resources/responses/methods/retrieve) via the API.
      You can disable this behavior by setting `store` to `false`
      when creating a Response.

      Conversation objects and items in them are not subject to the 30 day TTL. Any response attached to a conversation will have its items persisted with no 30 day TTL.

      OpenAI does not use data sent via API to train our models without your explicit consent—[learn more](https://developers.openai.com/api/docs/guides/your-data).

Even when using `previous_response_id`, all previous input tokens for responses in the chain are billed as input tokens in the API.

## Managing the context window

Understanding context windows will help you successfully create threaded conversations and manage state across model interactions.

The **context window** is the maximum number of tokens that can be used in a single request. This max tokens number includes input, output, and reasoning tokens. To learn your model's context window, see [model details](https://developers.openai.com/api/docs/models).

### Managing context for text generation
~~~~

来源#7：`gpt-reasoning-practices.md`，chunk=0，version=1faef98895c85ecca86307f8a91f49d4，HTTP=200

~~~~text
# GPT / OpenAI API：推理最佳实践

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Reasoning best practices

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：推理最佳实践

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Reasoning best practices

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI offers two types of models: [reasoning models](https://developers.openai.com/api/docs/models#o4-mini) (o3 and o4-mini, for example) and [GPT models](https://developers.openai.com/api/docs/models#gpt-4.1) (like GPT-4.1). These model families behave differently.

This guide covers:

1. The difference between our reasoning and non-reasoning GPT models
1. When to use our reasoning models
1. How to prompt reasoning models effectively

Read more about [reasoning models](https://developers.openai.com/api/docs/guides/reasoning) and how they work.

## Reasoning models vs. GPT models

Compared to GPT models, our o-series models excel at different tasks and require different prompts. One model family isn't better than the other—they're just different.

We trained our o-series models (“the planners”) to think longer and harder about complex tasks, making them effective at strategizing, planning solutions to complex problems, and making decisions based on large volumes of ambiguous information. These models can also execute tasks with high accuracy and precision, making them ideal for domains that would otherwise require a human expert—like math, science, engineering, financial services, and legal services.
~~~~

## E10 · ambiguous · clarification

我想做JSON结构化输出，怎样设置参数才能保证符合Schema？

判分要求：先询问厂商/模型或明确按厂商区分；不能给所有厂商通用的schema保证或混合参数

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

要保证输出符合 Schema，应使用 **JSON Schema 模式**，而不是 JSON Object 模式。以下是各厂商文档中的参数设置要点（请按你实际使用的厂商/接口对应设置，不能混用）：

## 阿里云百炼 / Qwen

**参数设置**：将 `response_format` 设为：
```json
{"type": "json_schema", "json_schema": {"name": "...", "strict": true, "schema": {...}}}
```
- `type` 必选，取 `json_schema` 时输出严格符合 `json_schema` 字段定义的结构。
- `json_schema.name` 必填（Schema 名称）；`json_schema.schema` 必填（描述输出结构的 JSON Schema 对象）。
- `strict` 推荐设为 `true`，表示严格遵循 schema 定义。
- 在 schema 内：用 `properties` 定义字段结构，用 `required` 声明必填字段，用 `additionalProperties` 控制是否允许未定义字段（推荐设为 `false`）。
- 使用 JSON Schema 模式时，提示词**无需**包含 "JSON" 关键词（这是与 JSON Object 模式的关键区别）。
- 通过 HTTP 调用时，`response_format` 需放入 `parameters` 对象中；DashScope 方式需手动构造 JSON Schema，暂不支持 Java SDK。

**生产环境建议**：
- 开启结构化输出时**不要设置 `max_tokens`**，否则 JSON 可能被截断产生无效 JSON。
- 推荐用 SDK 自动生成 Schema（如 OpenAI SDK 的 `parse` 方法可直接传入 Pydantic 类或 Zod 对象）。
- 若用 JSON Object 模式，下游使用前建议用 jsonschema、Ajv、Everit 等工具做有效性校验。

**注意**：`json_object` 与 `json_schema` 支持的模型不同，需查阅"支持的模型"确认你的模型支持 `json_schema`。另外，使用结构化输出时若开启思考模式会报错，需将 `enable_thinking` 设为 `false`。

## DeepSeek（Responses API）

`response_format` 设为 `{"type": "json_schema", "name": ..., "schema": ...}`：
- `type` 可选 `text` / `json_object` / `json_schema`，默认 `text`。
- `name`：schema 名称，`type` 为 `json_schema` 时必填。
- `schema`：输出必须符合的 JSON Schema，`type` 为 `json_schema` 时必填。

---

**说明**：以上为文档中的通用规则，不能证明你当前账户/模型的实际支持情况或未来版本行为。若你按上述设置后仍遇到具体报错，可提供 request_id、HTTP 状态/错误码、接口地址或发生时间，我再帮你核查。

来源#1: qwen-structured-outputs.md
来源#2: qwen-structured-outputs.md
来源#3: deepseek-responses.md
来源#4: qwen-dashscope.md
来源#5: qwen-chat-completions.md
来源#6: qwen-errors.md
来源#7: qwen-structured-outputs.md

### 实际引用锚点

来源#1：`qwen-structured-outputs.md`，chunk=1，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
Object 与 JSON Schema两种模式：

- <strong>JSON Object 模式</strong>：确保输出为标准格式的 JSON 字符串，但不保证符合特定结构。使用方式：

  1. <strong>设置</strong>`response_format`<strong>参数</strong>：在请求体中，将 `response_format` 参数设置为 `{"type": "json_object"}`。
  2. <strong>提示词包含 JSON 关键词</strong>：System Message 或 User Message 中需要包含 "JSON" 关键词（不区分大小写），否则会报错：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`

[同版本引用上下文]
# Qwen / 阿里云百炼：结构化输出

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 结构化输出

> 执行信息抽取或结构化数据生成任务时，大模型可能返回多余文本（如 ```json ）导致下游解析失败。开启结构化输出可确保大模型输出标准格式的 JSON 字符串，使用 JSON Schema 模式还能精确控制输出结构和类型，无需额外验证或重试。

<meta property="og:title" content="结构化输出" />

## 使用方式 <span id="364b79f28ebin" />

结构化输出支持JSON Object 与 JSON Schema两种模式：

- <strong>JSON Object 模式</strong>：确保输出为标准格式的 JSON 字符串，但不保证符合特定结构。使用方式：

  1. <strong>设置</strong>`response_format`<strong>参数</strong>：在请求体中，将 `response_format` 参数设置为 `{"type": "json_object"}`。
  2. <strong>提示词包含 JSON 关键词</strong>：System Message 或 User Message 中需要包含 "JSON" 关键词（不区分大小写），否则会报错：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`
- [<strong>JSON Schema 模式</strong>](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)：确保输出内容为指定的结构。使用方式：设置 `response_format` 为`{"type": "json_schema", "json_schema": {..., "strict": true}}`。

  > 提示词无需包含 JSON 关键词。

功能对比：
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

[同版本引用上下文]
s</code>、<code>unevaluatedProperties</code></p></td><td style={{ verticalAlign: "top" }}><p><code>patternProperties</code>、<code>propertyNames</code></p></td></tr></tbody></table>

## 应用于生产环境 <span id="3c31d76c389ij" />

- <strong>有效性校验</strong>

  若使用 JSON Object 模式，将输出传递给下游业务前，建议使用工具对其进行有效性校验，如 jsonschema (Python)、Ajv (JavaScript)、Everit (Java)等<strong>，</strong>确保其符合指定的 JSON Schema 要求，避免因字段缺失、类型错误或格式不规范导致下游系统解析失败、数据丢失或业务逻辑中断。失败时可通过重试、大模型改写等策略进行修复。
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

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # 以下为华北2（北京）地域的URL，调用时请将 {WorkspaceId} 替换为真实的业务空间ID，各地域的URL不同。
        base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )
    class UserInfo(BaseModel):
        name: str = Field(description="用户姓名")
        age: int = Field(description="用户年龄")
        email: Optional[str] = None  # 可选字段

    completion = client.chat.completions.parse(
        model="qwen3.8-max",
        messages=[
            {"role": "system", "content": "提取姓名与年龄信息。"},
            {"role": "user", "content": "我叫刘五，今年25岁。"},
        ],
        response_format=UserInfo  # 直接传入 Pydantic 模型
    )

    result = completion.choices[0].message.parsed  # 类型安全的解析结果
    print(f"姓名：{result.name}，年龄：{result.age}")
    ```
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

[同版本引用上下文]
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

模型可能会调用的工具的列表。函数名必须非空、不超过 128 个字符、匹配 `^[a-zA-Z0-9_-]+$`，且所有工具的名称必须唯一。支持 `function` 工具；`web_search` 在 `deepseek-v4-pro` 下支持，其余内置工具类型会被忽略。详情请参考 [Responses API 指南](https://api-docs.deepseek.com/zh-cn/guides/responses_api)。

-

Array [

type stringrequired

Possible values: [`function`, `custom`, `web_search`]

工具的类型：`function`、`custom`（仅 `apply_patch`）或 `web_search`（仅 `deepseek-v4-pro`）。

name string

用于 `function` / `custom` 工具。工具的名称。对于函数工具，必须非空、不超过 128 个字符、匹配 `^[a-zA-Z0-9_-]+$`，且所有工具的名称必须唯一。对于 custom 工具，必须为 `apply_patch`。

description string

用于 `function` 工具。函数功能的描述，供模型理解何时以及如何调用该函数。

parameters

object

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

property name* any

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

-

]

tool_choice string | object

nullable

控制模型调用工具的行为。

`none` 意味着模型不会调用任何工具，而是生成一条消息。

`auto`（默认）意味着模型可以选择生成一条消息或调用一个或多个工具。

`required` 意味着模型必须调用一个或多个工具。

通过 `{"type": "function", "name": "my_function"}` 指定特定工具，会强制模型调用该工具。

oneOf

- Tool choice mode

- Named tool choice

string
~~~~

来源#4：`qwen-dashscope.md`，chunk=85，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
n title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > DashScope 方式需手动构造 JSON Schema，格式与示例参见[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。暂不支持 Java SDK。

[同版本引用上下文]
> 相关文档：[结构化输出](/zh/model-studio/qwen-structured-output)。`json_object` 与 `json_schema` 支持的模型不同，参见[支持的模型](/zh/model-studio/qwen-structured-output#7a8e438e89xeq)。

        > 若指定为`{"type": "json_object"}`，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错；若指定为`{"type": "json_schema", ...}`，提示词无需包含 JSON 关键词。

        > Java SDK中为responseFormat\*。\*通过HTTP调用时，请将 <strong>response\_format</strong>放入 <strong>parameters</strong> 对象中。

        <Accordion title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > DashScope 方式需手动构造 JSON Schema，格式与示例参见[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。暂不支持 Java SDK。

          <Accordion title="属性">
            <strong>name</strong>`string`<strong>（必选）</strong>

            Schema 的名称。

            <strong>schema</strong>`object`<strong>（必选）</strong>

            描述输出结构的 JSON Schema 对象。通过 `properties` 定义字段结构，通过 `required` 声明必填字段列表，通过 `additionalProperties` 控制是否允许输出未在 Schema 中定义的字段（推荐设置为 `false`，即只输出已定义的字段）。支持的数据类型：string、number、integer、boolean、object、array、enum。相关文档：[配置指南](/zh/model-studio/qwen-structured-output#001cb6ae072tc)。

            <strong>strict</strong>`boolean`（可选）

            是否严格遵循 `schema` 定义的结构。推荐设置为 `true`。
          </Accordion>
        </Accordion>

        <strong>result\_format</strong>`string`（可选）默认为`text`（Qwen3-Max、Qwen3-VL、[QwQ](/zh/model-studio/deep-thinking) 模型、Qwen3 开源模型与 Qwen-Long 模型默认值为 message）
~~~~

来源#5：`qwen-chat-completions.md`，chunk=59，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
penAI SDK 的 `parse` 方法调用时，可直接传入 Python Pydantic 类或 Node.js Zod 对象，SDK 会自动将其转换为 JSON Schema，无需手动构造。

          <Accordion title="属性">
            <strong>name</strong>`string`<strong>（必选）</strong>

            Schema 的名称。

            <strong>schema</strong>`object`<strong>（必选）</strong>

            描述输出结构的 JSON Schema 对象。通过 `properties` 定义字段结构，通过 `required` 声明必填字段列表，通过 `additionalProperties` 控制是否允许输出未在 Schema 中定义的字段（推荐设置为 `false`，即只输出已定义的字段）。支持的数据类型：string、number、integer、boolean、object、array、enum。相关文档：[配置指南](/zh/model-studio/qwen-structured-output#001cb6ae072tc)。

[同版本引用上下文]
参数值为-2.0：这部电影很好。情节很好，演技很好，音乐也很好，总的来说，整部电影都很好。实际上，它真的很棒。情节非常好，演技也非常好，音乐也非常好。
        </Accordion>

        > 不建议修改QVQ模型的默认presence\_penalty值。

        <strong>response\_format</strong>`object` （可选） 默认值为`{"type": "text"}`

        返回内容的格式。可选值：

        - `{"type": "text"}`：输出文字回复；
        - `{"type": "json_object"}`：输出标准格式的JSON字符串。
        - `{"type": "json_schema", "json_schema": {...}}`：输出严格符合指定 JSON Schema 的JSON字符串，可精确控制输出结构与字段类型。

        > 相关文档：[结构化输出](/zh/model-studio/qwen-structured-output)。`json_object` 与 `json_schema` 支持的模型不同，参见[支持的模型](/zh/model-studio/qwen-structured-output#7a8e438e89xeq)。

        > 若指定为`{"type": "json_object"}`，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错；若指定为`{"type": "json_schema", ...}`，提示词无需包含 JSON 关键词。

        <Accordion title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > 通过 OpenAI SDK 的 `parse` 方法调用时，可直接传入 Python Pydantic 类或 Node.js Zod 对象，SDK 会自动将其转换为 JSON Schema，无需手动构造。

          <Accordion title="属性">
            <strong>name</strong>`string`<strong>（必选）</strong>

            Schema 的名称。

            <strong>schema</strong>`object`<strong>（必选）</strong>

            描述输出结构的 JSON Schema 对象。通过 `properties` 定义字段结构，通过 `required` 声明必填字段列表，通过 `additionalProperties` 控制是否允许输出未在 Schema 中定义的字段（推荐设置为 `false`，即只输出已定义的字段）。支持的数据类型：string、number、integer、boolean、object、array、enum。相关文档：[配置指南](/zh/model-studio/qwen-structured-output#001cb6ae072tc)。
~~~~

来源#6：`qwen-errors.md`，chunk=18，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
2789r0r" />

<strong>原因：</strong> 工具名称无法设置为`search`。

<strong>解决方案：</strong> 工具名称请设置为`search`之外的值。

### Unknown format of response\_format, response\_format should be a dict, includes 'type' and an optional key 'json\_schema'. The response\_format type from user is xxx. <span id="d08defd0e7kbk" />

<strong>原因：</strong> 指定的`response_format`参数不符合规定。

<strong>解决方案：</strong> 如需使用[结构化输出](/zh/model-studio/qwen-structured-output)功能，请将`response_format`参数设置为`{"type": "json_object"}`。

### The value of the enable\_thinking parameter is restricted to True. <span id="9c16fdf75fnn1" />

[同版本引用上下文]
<strong>原因：</strong> 调用大模型时，既未指定`messages`参数，也未指定`prompt`参数（即将废弃）。如果指定了`messages`参数后报错，可能是因为格式错误，例如通过DashScope-HTTP时，`messages`需放入`input`对象中，而不是与`model`参数并列。

<strong>解决方案：</strong> 请指定`messages`参数。如果已指定但仍报错，请参见[文本生成](/zh/model-studio/qwen-api-reference)API文档，检查其位置是否正确。

### 'messages' must contain the word 'json' in some form, to use 'response\_format' of type 'json\_object'. <span id="4b2b7bcaefr8i" />

<strong>原因：</strong> 使用[结构化输出](/zh/model-studio/qwen-structured-output)时，提示词中不包含 `json` 关键词。

<strong>解决方案：</strong> 在提示词中加入`json`（不区分大小写），如：“请以json格式输出”。

### Json mode response is not supported when enable\_thinking is true <span id="ccffa8d337loe" />

<strong>原因：</strong> 使用[结构化输出](/zh/model-studio/qwen-structured-output)时开启了模型的思考模式。

<strong>解决方案：</strong> 请在使用结构化输出时，将`enable_thinking`设为`false`关闭思考模式。也可参见常见问题[思考模式模型如何结构化输出？](/zh/model-studio/qwen-structured-output#2f7ba877d3hle)

### Tool names are not allowed to be \[search] <span id="04d5652789r0r" />

<strong>原因：</strong> 工具名称无法设置为`search`。

<strong>解决方案：</strong> 工具名称请设置为`search`之外的值。

### Unknown format of response\_format, response\_format should be a dict, includes 'type' and an optional key 'json\_schema'. The response\_format type from user is xxx. <span id="d08defd0e7kbk" />

<strong>原因：</strong> 指定的`response_format`参数不符合规定。

<strong>解决方案：</strong> 如需使用[结构化输出](/zh/model-studio/qwen-structured-output)功能，请将`response_format`参数设置为`{"type": "json_object"}`。

### The value of the enable\_thinking parameter is restricted to True. <span id="9c16fdf75fnn1" />

<strong>原因：</strong> 部分模型（如`qwen3.7-plus`）不可将`enable_thinking`参数设为 `false`。

<strong>解决方案：</strong>

- 若通过第三方工具调用（如 Cherry Studio），请打开输入框的思考开关。
- 若通过代码调用，请将`enable_thinking`设为`true`。
~~~~

来源#7：`qwen-structured-outputs.md`，chunk=167，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
ect['age']}")
    ```

    运行代码可获得以下输出：

    ```plaintext
    姓名：刘五，年龄：25
    ```
  </Tab>
</Tabs>

### 配置指南 <span id="001cb6ae072tc" />

使用 JSON Schema 时，遵循以下规范可获得更可靠的结构化输出：

- <strong>必填字段声明</strong>

  推荐将必填字段列在 `required`数组中。可选字段可不列入，例如：

```json
{
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"},
    "email": {"type": "string"}
  },
  "required": ["name", "age"]
}
```

若输入未提供 email 信息，输出中将不包含此字段。

- <strong>可选字段的实现方式</strong>

  除不列入 `required` 外，也可通过允许 `null` 类型实现：

[同版本引用上下文]
messages = [
        {
            "role": "user",
            "content": [{"text": "我叫刘五，今年25岁。"}],
        },
    ]
    response = dashscope.MultiModalConversation.call(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model="qwen3.8-max",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "user_info",
                "strict": True,
                "schema": {
                    "properties": {
                        "name": {"title": "Name", "type": "string"},
                        "age": {"title": "Age", "type": "integer"},
                    },
                    "required": ["name", "age"],
                    "title": "UserInfo",
                    "type": "object",
                },
            },
        },
    )
    json_object = json.loads(response.output.choices[0].message.content[0]["text"])
    print(f"姓名：{json_object['name']}，年龄：{json_object['age']}")
    ```

    运行代码可获得以下输出：

    ```plaintext
    姓名：刘五，年龄：25
    ```
  </Tab>
</Tabs>

### 配置指南 <span id="001cb6ae072tc" />

使用 JSON Schema 时，遵循以下规范可获得更可靠的结构化输出：

- <strong>必填字段声明</strong>

  推荐将必填字段列在 `required`数组中。可选字段可不列入，例如：

```json
{
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"},
    "email": {"type": "string"}
  },
  "required": ["name", "age"]
}
```

若输入未提供 email 信息，输出中将不包含此字段。

- <strong>可选字段的实现方式</strong>

  除不列入 `required` 外，也可通过允许 `null` 类型实现：

```json
{
  "properties": {
    "name": {"type": "string"},
    "email": {"type": ["string", "null"]}  // 可以是字符串或 null
  },
  "required": ["name", "email"]  // 两个都在 required 中
}
```

输出将始终包含 `email` 字段，但其值可能为 `null`。

- <strong>additionalProperties 配置</strong>

  控制是否允许输出未在 schema 中定义的额外字段：
~~~~

## E11 · comparison · comparison

比较DeepSeek的JSON Output和OpenAI的Structured Outputs：前者是否自动约束JSON Schema？后者的Schema保证是什么？请分别标注依据。

判分要求：DeepSeek JSON Output保证合法JSON，不自动承诺Schema约束；OpenAI Structured Outputs支持JSON Schema约束；两家事实分别引用对应官方资料

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论（基于文档规则，不涉及任何个人账户或实际故障）：**

**1. DeepSeek JSON Output 是否自动约束 JSON Schema？**
不是。DeepSeek 的 JSON Output 功能是“确保模型输出合法的 JSON 字符串”，通过设置 `response_format` 为 `{'type': 'json_object'}` 使用；文档要求用户在 system 或 user prompt 中必须含有 `json` 字样，并给出希望模型输出的 JSON 格式样例，以“指导模型”输出合法 JSON。文档未说明该功能会自动按某个 JSON Schema 进行约束；相反，它依赖 prompt 中的格式样例来引导。此外文档提示需合理设置 `max_tokens` 防止截断，且 API 有概率返回空 content。来源#6。

补充区分：DeepSeek 另有 `strict` 模式（Beta），用于**工具调用（Function）**场景，模型输出 Function 调用时严格遵循 Function 的 JSON Schema；该能力需使用 `base_url="https://api.deepseek.com/beta"`、在 `tools` 中为所有 function 设置 `strict: true`，且服务端会校验传入的 JSON Schema。这属于工具调用参数约束，不等同于 JSON Output 的响应格式约束。来源#5。

**2. OpenAI Structured Outputs 的 Schema 保证是什么？**
文档明确表述：JSON mode 只保证输出是合法 JSON（且存在需自行检测处理的边缘情况），而 Structured Outputs 会“reliably matches the model's output to the schema you specify”（可靠地使模型输出匹配你指定的 schema）；两者都保证产生合法 JSON，但“only Structured Outputs ensure schema adherence”（只有 Structured Outputs 确保符合 schema）。来源#4、来源#2。

使用方式上，需先设计模型应遵循的 JSON Schema，并在 API 调用中指定 `text: { format: { type: "json_schema", "strict": true, "schema": … } }`。来源#1。

适用范围限制：Structured Outputs 支持 JSON Schema 的一个子集，部分特性因性能或技术原因不可用；支持的类型包括 String、Number、Boolean、Integer、Object、Array、Enum、anyOf。来源#1、来源#3。另外，文档提到通过 `response_format: {type: "json_schema", ...}` 使用 Structured Outputs 仅支持特定模型（如 gpt-4o-mini 等），具体模型范围请以该文档所列及你实际使用的接口为准。来源#4。

**对比要点：**
- DeepSeek JSON Output：保证合法 JSON 字符串，靠 prompt 样例引导，不承诺按指定 Schema 约束。来源#6。
- OpenAI Structured Outputs：在支持的 Schema 子集与适用模型范围内，确保输出符合指定 Schema。来源#1、来源#3、来源#4。

以上均为厂商文档的通用规则说明，不代表任何具体账户的配置状态或未来版本承诺。

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

[同版本引用上下文]
```ruby
require "openai"

client = OpenAI::Client.new
entities_schema = {
  type: :object,
  properties: {
    attributes: {
      type: :array,
      items: { type: :string }
    },
    colors: {
      type: :array,
      items: { type: :string }
    },
    animals: {
      type: :array,
      items: { type: :string }
    }
  },
  required: %w[attributes colors animals],
  additionalProperties: false
}

stream = client.responses.stream(
  model: "gpt-6-astra",
  input: [
    {
      role: :system,
      content: "Extract entities from the input text."
    },
    {
      role: :user,
      content: "The quick brown fox jumps over the lazy dog with piercing blue eyes."
    }
  ],
  text: {
    format: {
      type: :json_schema,
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

The following types are supported for Structured Outputs:

- String
- Number
- Boolean
- Integer
- Object
- Array
- Enum
- anyOf

#### Supported properties

In addition to specifying the type of a property, you can specify a selection of additional constraints:

**Supported `string` properties:**
~~~~

来源#4：`gpt-structured-outputs.md`，chunk=28，version=a7c14af425e259ac942409a3404d74b8，HTTP=200

~~~~text
.com/api/docs/guides/function-calling#strict-mode)
    guide.

### Structured Outputs vs JSON mode

Structured Outputs is the evolution of [JSON mode](#json-mode). While both ensure valid JSON is produced, only Structured Outputs ensure schema adherence. Both Structured Outputs and JSON mode are supported in the Responses API, Chat Completions API, Assistants API, Fine-tuning API and Batch API.

We recommend always using Structured Outputs instead of JSON mode when possible.

[同版本引用上下文]
Conversely, Structured Outputs via `response_format` are more suitable when you want to indicate a structured schema for use when the model responds to the user, rather than when the model calls a tool.

For example, if you are building a math tutoring application, you might want the assistant to respond to your user using a specific JSON Schema so that you can generate a UI that displays different parts of the model's output in distinct ways.

In practice:

  - If you are connecting the model to tools, functions, data, etc. in your
  system, then you should use function calling - If you want to structure the
  model's output when it responds to the user, then you should use a structured
  `text.format`

  The remainder of this guide will focus on non-function calling use cases in
    the Responses API. To learn more about how to use Structured Outputs with
    function calling, check out the
    [Function Calling](https://developers.openai.com/api/docs/guides/function-calling#strict-mode)
    guide.

### Structured Outputs vs JSON mode

Structured Outputs is the evolution of [JSON mode](#json-mode). While both ensure valid JSON is produced, only Structured Outputs ensure schema adherence. Both Structured Outputs and JSON mode are supported in the Responses API, Chat Completions API, Assistants API, Fine-tuning API and Batch API.

We recommend always using Structured Outputs instead of JSON mode when possible.

However, Structured Outputs with `response_format: {type: "json_schema", ...}` is only supported with the `gpt-4o-mini`, `gpt-4o-mini-2024-07-18`, and `gpt-4o-2024-08-06` model snapshots and later.
~~~~

来源#5：`deepseek-tool-calling.md`，chunk=6，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

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

## E12 · qwen · insufficient

请按Qwen 2099-01-01版官方规范确认text-embedding-v4当时支持的全部维度；当前2026快照是否足以给出该版本结论？

判分要求：不能用2026快照确认2099版本；允许明确标作当前快照规则，不得冒充未来官方规范

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论：不能按“Qwen 2099-01-01版官方规范”确认 text-embedding-v4 当时支持的全部维度；现有 2026 快照也不足以给出该历史版本的结论。**

**1. 关于“2099-01-01版官方规范”**

现有证据中没有任何 2099-01-01 版本的规范或快照，因此无法确认该版本下 text-embedding-v4 支持的全部维度。不能把其他时点的文档内容当作该版本的结论。

**2. 现有快照能说明什么（仅限其自身时点）**

- 文档标注核对日期为 2026-10-19，并明确“核对日期不等于规则生效日”。该快照描述 text-embedding-v4 支持 **64~2048 维用户自定义向量维度**，但这是该快照时点的表述，不能外推为 2099-01-01 版本的状态。
- 其他文档仅说明 text-embedding-v4 支持 `dimension` 参数（示例取值为 1024），未给出完整维度范围，不能据此补全“全部维度”。

**3. 当前 2026 快照是否足以给出该版本结论**

不足以。原因：快照时点为 2026-10-19，且文档自述核对日期不等于规则生效日；没有任何证据覆盖 2099-01-01 这一时点，因此无法据此确认该历史/指定版本的完整维度清单。

**4. 下一步建议**

如需该版本结论，请提供 2099-01-01 版官方规范的原文或链接（或该版本对应的文档快照）；在取得该版本材料前，只能引用 2026-10-19 快照中“64~2048 维”的表述，并注明其适用时点。

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

[同版本引用上下文]
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

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际
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

[同版本引用上下文]
```bash curl
              curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding' \
              --header "Authorization: Bearer $DASHSCOPE_API_KEY" \
              --header 'Content-Type: application/json' \
              --data '{
                  "model": "qwen3.7-text-embedding",
                  "input": {
                      "texts": [
                        "风急天高猿啸哀",
                        "渚清沙白鸟飞回",
                        "无边落木萧萧下",
                        "不尽长江滚滚来"
                      ]
                  },
                  "parameters": {
                        "dimension": 1024,
                        "output_type": "dense"
                  }
              }'
              ```
            </CodeGroup>
          </Tab>

          <Tab title="输入文件">
            <Tabs>
              <Tab title="Python">
                ```python
                from http import HTTPStatus
                from dashscope import TextEmbedding
                # 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                dashscope.base_http_api_url = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1"

                with open('texts_to_embedding.txt', 'r', encoding='utf-8') as f:
                    resp = TextEmbedding.call(
                        model="qwen3.7-text-embedding",
                        input=f,
                        dimension=1024 # 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
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

[同版本引用上下文]
/**
               * 千问文本向量模型调用示例
               */
              public final class Main {
                  public static void main(String[] args) {
                      // 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                      Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
                      try {
                          // 构建请求参数
                          TextEmbeddingParam param = TextEmbeddingParam
                                  .builder()
                                  .model("qwen3.7-text-embedding")  // 使用text-embedding-v4模型
                                  .texts(Arrays.asList("衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买"))  // 输入文本
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();

                          // 创建模型实例并调用
                          TextEmbedding textEmbedding = new TextEmbedding();
                          TextEmbeddingResult result = textEmbedding.call(param);

                          // 输出结果
                          System.out.println(result);

                      } catch (ApiException | NoApiKeyException e) {
                          System.out.println("调用失败：" + e.getMessage());
                      }
                  }
              }
              ```
~~~~

来源#4：`qwen-embedding-api.md`，chunk=85，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
.model("qwen3.7-text-embedding")
                                  .texts(batch)
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();

[同版本引用上下文]
public final class Main {
                  private static final int DASHSCOPE_MAX_BATCH_SIZE = 10;

                  public static void main(String[] args) {
                      // 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                      Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
                      List<String> inputs = Arrays.asList(
                              "风急天高猿啸哀",
                              "渚清沙白鸟飞回",
                              "无边落木萧萧下",
                              "不尽长江滚滚来"
                      );

                      TextEmbeddingResult result = null;
                      int batchCounter = 0;

                      for (int i = 0; i < inputs.size(); i += DASHSCOPE_MAX_BATCH_SIZE) {
                          List<String> batch = inputs.subList(i, Math.min(i + DASHSCOPE_MAX_BATCH_SIZE, inputs.size()));
                          TextEmbeddingParam param = TextEmbeddingParam.builder()
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

[同版本引用上下文]
public class Main {
                  public static void main(String[] args) {
                      // 创建客户端，使用环境变量中的API密钥
                      OpenAIClient client = OpenAIOkHttpClient.builder()
                              .apiKey(System.getenv("DASHSCOPE_API_KEY"))
                              // 以下为华北2（北京）地域的URL，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的URL不同。
                              .baseUrl("https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
                              .build();

                      // 创建输入字符串列表
                      List<String> inputList = Arrays.asList(
                          "风急天高猿啸哀",
                          "渚清沙白鸟飞回",
                          "无边落木萧萧下",
                          "不尽长江滚滚来"
                      );

                      // 存储所有响应的列表
                      List<CreateEmbeddingResponse> responses = new ArrayList<>();

                      // 循环处理每个字符串
                      for (String text : inputList) {
                          try {
                              // 创建向量化请求参数
                              EmbeddingCreateParams params = EmbeddingCreateParams.builder()
                                      .model("qwen3.7-text-embedding")
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

[同版本引用上下文]
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
~~~~

## N01 · deepseek · fact

DeepSeek的FIM补全允许提供前缀和后缀吗？用途是什么，最大补全长度是多少？

判分要求：可以给前缀及可选后缀补中间内容；适合代码补全；最大补全长度4K（以快照原文为准）

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

根据 DeepSeek 官方文档（Beta 功能）：

**1. 是否允许提供前缀和后缀？**
允许。FIM（Fill In the Middle）补全中，用户可以**提供前缀和后缀**，其中后缀是**可选**的，由模型补全中间的内容。使用时需设置 `base_url="https://api.deepseek.com/beta"` 开启 Beta 功能。来源#1: deepseek-fim-guide.md

**2. 用途是什么？**
FIM 常用于**内容续写、代码补全**等场景。来源#1: deepseek-fim-guide.md

**3. 最大补全长度是多少？**
模型的最大补全长度为 **4K**。来源#1: deepseek-fim-guide.md

补充说明（适用范围）：FIM 补全（Beta）在 `deepseek-flash` 和 `deepseek-v4-pro` 上**仅非思考模式支持**。来源#4: deepseek-models-pricing.md

来源#1: deepseek-fim-guide.md
来源#2: deepseek-fim-api.md
来源#3: deepseek-prefix-completion.md
来源#4: deepseek-models-pricing.md
来源#5: deepseek-chat-completions.md
来源#6: deepseek-context-cache.md

### 实际引用锚点

来源#1：`deepseek-fim-guide.md`，chunk=0，version=882a8182be7d5ebf925e34de37f5d0eb，HTTP=200

~~~~text
# DeepSeek API：FIM 补全指南

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全（Beta）](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全（Beta）

在 [FIM (Fill In the Middle) 补全](https://api-docs.deepseek.com/zh-cn/api/create-completion)中，用户可以提供前缀和后缀（可选），模型来补全中间的内容。FIM 常用于内容续写、代码补全等场景。

## 注意事项

- 模型的最大补全长度为 4K。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

[同版本引用上下文]
# DeepSeek API：FIM 补全指南

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全（Beta）](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全（Beta）

在 [FIM (Fill In the Middle) 补全](https://api-docs.deepseek.com/zh-cn/api/create-completion)中，用户可以提供前缀和后缀（可选），模型来补全中间的内容。FIM 常用于内容续写、代码补全等场景。

## 注意事项

- 模型的最大补全长度为 4K。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

```
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)response = client.completions.create(    model="deepseek-flash",    prompt="def fib(a):",    suffix="    return fib(a-1) + fib(a-2)",    max_tokens=128,)print(response.choices[0].text)
```

## 配置 Continue 代码补全插件

[Continue](https://continue.dev) 是一款支持代码补全的 VSCode 插件，您可以参考[这篇文档](https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/continue/README_cn.md)来配置 Continue 以使用代码补全功能。
~~~~

来源#2：`deepseek-fim-api.md`，chunk=0，version=915e523f4c295d7081edf327bf11171e，HTTP=200

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

来源#3：`deepseek-prefix-completion.md`，chunk=0，version=4ebb1c1409b3573188a9f2105103b409，HTTP=200

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

[同版本引用上下文]
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

下面给出了对话前缀续写的完整 Python 代码样例。在这个例子中，我们设置 `assistant` 开头的消息为 `"```python\n"` 来强制模型输出 python 代码，并设置 `stop` 参数为 `['```']` 来避免模型的额外解释。

````
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)messages = [    {"role": "user", "content": "Please write quick sort code"},    {"role": "assistant", "content": "```python\n", "prefix": True},]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stop=["```"],)print(response.choices[0].message.content)
````
~~~~

来源#4：`deepseek-models-pricing.md`，chunk=1，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

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

来源#5：`deepseek-chat-completions.md`，chunk=0，version=acb1ddea03df5b2cb00d72d0f989cf84，HTTP=200

~~~~text
# DeepSeek API：Chat Completions 参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Chat Completions API](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Chat Completions API

```
POST /chat/completions
```

根据输入的上下文，来让模型补全对话内容。

## Request

- application/json

### Body

required

messages

object[]

required

Possible values: `>= 1`

对话的消息列表。

-

Array [

oneOf

- System message

- User message

- Assistant message

- Tool message
content stringrequired

system 消息的内容。

role stringrequired

[同版本引用上下文]
# DeepSeek API：Chat Completions 参数

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[Chat Completions API](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Chat Completions API

```
POST /chat/completions
```

根据输入的上下文，来让模型补全对话内容。

## Request

- application/json

### Body

required

messages

object[]

required

Possible values: `>= 1`

对话的消息列表。

-

Array [

oneOf

- System message

- User message

- Assistant message

- Tool message
content stringrequired

system 消息的内容。

role stringrequired

Possible values: [`system`]

该消息的发起角色，其值为 `system`。

name string

可以选填的参与者的名称，为模型提供信息以区分相同角色的参与者。

content string | object[]

required

user 消息的内容。可以是字符串，也可以是内容块数组（可携带图片）。详见[图像理解指南](https://api-docs.deepseek.com/zh-cn/guides/vision)。

oneOf

- Text content

- Array of content parts

string

-

Array [

oneOf

- Text content part

- Image content part

- File content part
type stringrequired

Possible values: [`text`]

内容块的类型，此场景下为 `text`。

text stringrequired

文本内容。

type stringrequired

Possible values: [`image_url`]

内容块的类型，此场景下为 `image_url`。

image_url

object

required

url stringrequired

图片的 `http(s)` URL（最多 8192 个字符）或 base64 编码的 data URL（`data:image/jpeg;base64,...`）。支持的格式：JPEG、PNG、GIF、WebP。

detail string

Possible values: [`low`, `high`, `original`, `auto`]

控制图片的处理方式。`low` 将图片缩小到 512x512（更快、更省 token）；`high`、`original` 与 `auto` 保留原图。

type stringrequired

Possible values: [`file`]

内容块的类型，此场景下为 `file`。

file_id string

通过 [Files API](https://api-docs.deepseek.com/zh-cn/guides/files_api) 上传的文件 ID，形如 `file-api-...`。与 `file_data` 互斥。

file_data string

图片的 base64 编码 data URL（`data:image/jpeg;base64,...`）。与 `file_id` 互斥。

filename string

可选的文件名，仅在配合 `file_data` 时有效。

-

]
~~~~

来源#6：`deepseek-context-cache.md`，chunk=0，version=47e606d87a095b0383cca6173a3b8136，HTTP=200

~~~~text
# DeepSeek API：上下文缓存

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[上下文硬盘缓存](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 上下文硬盘缓存

DeepSeek API 上下文硬盘缓存技术对所有用户默认开启，用户无需修改代码即可享用。

用户的每一个请求都会触发硬盘缓存的构建。若后续请求与之前的请求在前缀上存在重复，则重复部分只需要从缓存中拉取，计入“缓存命中”。

## 缓存落盘与命中规则

缓存命中的前提是相应前缀已被“落盘”（写入硬盘缓存）。受 Sliding Window Attention 机制的影响，缓存前缀的存取与判别与之前有所不同。每条缓存前缀是一个独立的完整单元。后续请求只有在完整匹配缓存前缀单元时，才能命中缓存。

### 缓存前缀落盘时机：

-

请求结束位置落盘：每次请求的用户输入结束位置与模型输出结束位置，会产生两个缓存前缀单元。后续请求若完整匹配了它们，则可命中。

-

[同版本引用上下文]
# DeepSeek API：上下文缓存

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[上下文硬盘缓存](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 上下文硬盘缓存

DeepSeek API 上下文硬盘缓存技术对所有用户默认开启，用户无需修改代码即可享用。

用户的每一个请求都会触发硬盘缓存的构建。若后续请求与之前的请求在前缀上存在重复，则重复部分只需要从缓存中拉取，计入“缓存命中”。

## 缓存落盘与命中规则

缓存命中的前提是相应前缀已被“落盘”（写入硬盘缓存）。受 Sliding Window Attention 机制的影响，缓存前缀的存取与判别与之前有所不同。每条缓存前缀是一个独立的完整单元。后续请求只有在完整匹配缓存前缀单元时，才能命中缓存。

### 缓存前缀落盘时机：

-

请求结束位置落盘：每次请求的用户输入结束位置与模型输出结束位置，会产生两个缓存前缀单元。后续请求若完整匹配了它们，则可命中。

-

公共前缀检测落盘：当系统检测到多次请求之间存在公共前缀时，会将该公共前缀作为一个独立的缓存前缀单元进行落盘。后续请求若完整复用了该缓存前缀单元，则可命中。

-

按固定 token 间隔落盘：在长输入或长输出中，系统会以一定的 token 数量为间隔，截取缓存前缀单元，避免长前缀因迟迟未达到结束位置而完全无法被缓存。

举例 1：用户第一轮请求内容为 `A + B`，第二轮请求内容为 `A + B + C`，则第二轮请求能完整匹配 `A + B` 这个缓存前缀单元，可以命中 `A + B` 的缓存。详见下文例一。

举例 2：用户第一轮请求的内容为 `A + B`，第二轮请求的内容为 `A + C`，则第二轮请求无法命中缓存，因为 `A + C` 不能完整匹配第一轮的缓存前缀单元（`A + B`）。但此时系统会识别到两轮请求存在公共前缀 `A`，并将 `A` 作为缓存前缀单元落盘。当第三轮请求 `A + D` 到来时，能完整匹配 `A` 这个缓存前缀单元，可以命中 `A` 的缓存。详见下文例二。

### 例一：多轮对话

第一次请求

```
messages: [    {"role": "system", "content": "你是一位乐于助人的助手"},    {"role": "user", "content": "中国的首都是哪里？"}]
```

第二次请求

```
messages: [    {"role": "system", "content": "你是一位乐于助人的助手"},    {"role": "user", "content": "中国的首都是哪里？"},    {"role": "assistant", "content": "中国的首都是北京。"},    {"role": "user", "content": "美国的首都是哪里？"}]
```

在上例中，第二次请求可以完整复用第一次请求的缓存前缀单元，这部分会计入“缓存命中”。

### 例二：长文本问答

第一次请求

```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请总结一下这份财报的关键信息。"}]
```

第二次请求

```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请分析一下这份财报的盈利情况。"}]
```

第三次请求
~~~~

## N02 · deepseek · fact

DeepSeek上下文硬盘缓存需要我手动开启吗？只是部分相似的前缀就必然命中吗？

判分要求：默认开启无需改代码；匹配已落盘完整前缀单元；相似不保证命中

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**1. 需要手动开启吗？**
不需要。DeepSeek API 的上下文硬盘缓存对所有用户默认开启，无需修改代码即可使用；每个请求都会触发缓存构建。[来源#1]

**2. 只是部分相似的前缀就必然命中吗？**
不是“必然命中”，需要同时满足两个条件：

- **必须完整匹配一个已落盘的缓存前缀单元**：每条缓存前缀是独立完整单元，后续请求只有完整匹配该单元才能命中。例如第一轮 `A+B`、第二轮 `A+C` 不能命中 `A+B`；但系统会识别公共前缀 `A` 并落盘，第三轮 `A+D` 可完整匹配 `A` 而命中。[来源#1]
- **缓存系统是“尽力而为”，不保证 100% 命中**；缓存构建耗时为秒级，不再使用后会自动清空（一般几小时到几天）。[来源#2]

因此，仅“部分相似”并不等于命中；只有相似部分恰好构成一个完整、已落盘的缓存前缀单元时才可能命中，且仍受“尽力而为”限制。

**补充：如何查看命中情况**
DeepSeek API 返回的 `usage` 中提供 `prompt_cache_hit_tokens`（命中 tokens 数）和 `prompt_cache_miss_tokens`（未命中 tokens 数）。[来源#2] Responses API 的 `usage.input_tokens_details.cached_tokens` 也表示命中上下文缓存的输入 token 数。[来源#7]

以上为 DeepSeek API 的通用文档规则，不代表您个人账户的实际命中状态。

来源#1: deepseek-context-cache.md
来源#2: deepseek-context-cache.md
来源#3: deepseek-multi-round.md
来源#4: deepseek-prefix-completion.md
来源#5: deepseek-fim-guide.md
来源#6: deepseek-models-pricing.md
来源#7: deepseek-responses.md
来源#8: deepseek-thinking.md

### 实际引用锚点

来源#1：`deepseek-context-cache.md`，chunk=0，version=47e606d87a095b0383cca6173a3b8136，HTTP=200

~~~~text
# DeepSeek API：上下文缓存

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[上下文硬盘缓存](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 上下文硬盘缓存

DeepSeek API 上下文硬盘缓存技术对所有用户默认开启，用户无需修改代码即可享用。

用户的每一个请求都会触发硬盘缓存的构建。若后续请求与之前的请求在前缀上存在重复，则重复部分只需要从缓存中拉取，计入“缓存命中”。

## 缓存落盘与命中规则

缓存命中的前提是相应前缀已被“落盘”（写入硬盘缓存）。受 Sliding Window Attention 机制的影响，缓存前缀的存取与判别与之前有所不同。每条缓存前缀是一个独立的完整单元。后续请求只有在完整匹配缓存前缀单元时，才能命中缓存。

### 缓存前缀落盘时机：

-

请求结束位置落盘：每次请求的用户输入结束位置与模型输出结束位置，会产生两个缓存前缀单元。后续请求若完整匹配了它们，则可命中。

-

[同版本引用上下文]
# DeepSeek API：上下文缓存

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[上下文硬盘缓存](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 上下文硬盘缓存

DeepSeek API 上下文硬盘缓存技术对所有用户默认开启，用户无需修改代码即可享用。

用户的每一个请求都会触发硬盘缓存的构建。若后续请求与之前的请求在前缀上存在重复，则重复部分只需要从缓存中拉取，计入“缓存命中”。

## 缓存落盘与命中规则

缓存命中的前提是相应前缀已被“落盘”（写入硬盘缓存）。受 Sliding Window Attention 机制的影响，缓存前缀的存取与判别与之前有所不同。每条缓存前缀是一个独立的完整单元。后续请求只有在完整匹配缓存前缀单元时，才能命中缓存。

### 缓存前缀落盘时机：

-

请求结束位置落盘：每次请求的用户输入结束位置与模型输出结束位置，会产生两个缓存前缀单元。后续请求若完整匹配了它们，则可命中。

-

公共前缀检测落盘：当系统检测到多次请求之间存在公共前缀时，会将该公共前缀作为一个独立的缓存前缀单元进行落盘。后续请求若完整复用了该缓存前缀单元，则可命中。

-

按固定 token 间隔落盘：在长输入或长输出中，系统会以一定的 token 数量为间隔，截取缓存前缀单元，避免长前缀因迟迟未达到结束位置而完全无法被缓存。

举例 1：用户第一轮请求内容为 `A + B`，第二轮请求内容为 `A + B + C`，则第二轮请求能完整匹配 `A + B` 这个缓存前缀单元，可以命中 `A + B` 的缓存。详见下文例一。

举例 2：用户第一轮请求的内容为 `A + B`，第二轮请求的内容为 `A + C`，则第二轮请求无法命中缓存，因为 `A + C` 不能完整匹配第一轮的缓存前缀单元（`A + B`）。但此时系统会识别到两轮请求存在公共前缀 `A`，并将 `A` 作为缓存前缀单元落盘。当第三轮请求 `A + D` 到来时，能完整匹配 `A` 这个缓存前缀单元，可以命中 `A` 的缓存。详见下文例二。

### 例一：多轮对话

第一次请求

```
messages: [    {"role": "system", "content": "你是一位乐于助人的助手"},    {"role": "user", "content": "中国的首都是哪里？"}]
```

第二次请求

```
messages: [    {"role": "system", "content": "你是一位乐于助人的助手"},    {"role": "user", "content": "中国的首都是哪里？"},    {"role": "assistant", "content": "中国的首都是北京。"},    {"role": "user", "content": "美国的首都是哪里？"}]
```

在上例中，第二次请求可以完整复用第一次请求的缓存前缀单元，这部分会计入“缓存命中”。

### 例二：长文本问答

第一次请求

```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请总结一下这份财报的关键信息。"}]
```

第二次请求

```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请分析一下这份财报的盈利情况。"}]
```

第三次请求
~~~~

来源#2：`deepseek-context-cache.md`，chunk=4，version=47e606d87a095b0383cca6173a3b8136，HTTP=200

~~~~text
```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请分析一下公司收入与支出占比。"}]
```

在上例中，前两次请求不会命中缓存。前两次请求完成后，系统会识别出 `system` 消息 + `user` 消息中的<财报内容>为缓存前缀单元，并进行落盘。在第三次请求中，由于完整匹配了前面落盘的缓存前缀单元，则可命中缓存。

## 查看缓存命中情况

在 DeepSeek API 的返回中，我们在 `usage` 字段中增加了两个字段，来反映请求的缓存命中情况：

-

`prompt_cache_hit_tokens`：本次请求的输入中，缓存命中的 tokens 数

-

`prompt_cache_miss_tokens`：本次请求的输入中，缓存未命中的 tokens 数

## 硬盘缓存与输出随机性

硬盘缓存只匹配到用户输入的前缀部分，输出仍然是通过计算推理得到的，仍然受到 temperature 等参数的影响，从而引入随机性。其输出效果与不使用硬盘缓存相同。

## 其它说明

-

缓存系统是“尽力而为”，不保证 100% 缓存命中

-

[同版本引用上下文]
```
messages: [    {"role": "system", "content": "你是一位资深的财报分析师..."},    {"role": "user", "content": "<财报内容>\n\n请分析一下公司收入与支出占比。"}]
```

在上例中，前两次请求不会命中缓存。前两次请求完成后，系统会识别出 `system` 消息 + `user` 消息中的<财报内容>为缓存前缀单元，并进行落盘。在第三次请求中，由于完整匹配了前面落盘的缓存前缀单元，则可命中缓存。

## 查看缓存命中情况

在 DeepSeek API 的返回中，我们在 `usage` 字段中增加了两个字段，来反映请求的缓存命中情况：

-

`prompt_cache_hit_tokens`：本次请求的输入中，缓存命中的 tokens 数

-

`prompt_cache_miss_tokens`：本次请求的输入中，缓存未命中的 tokens 数

## 硬盘缓存与输出随机性

硬盘缓存只匹配到用户输入的前缀部分，输出仍然是通过计算推理得到的，仍然受到 temperature 等参数的影响，从而引入随机性。其输出效果与不使用硬盘缓存相同。

## 其它说明

-

缓存系统是“尽力而为”，不保证 100% 缓存命中

-

缓存构建耗时为秒级。缓存不再使用后会自动被清空，时间一般为几个小时到几天
~~~~

来源#3：`deepseek-multi-round.md`，chunk=0，version=e53c4589cafa5c27b618be4c292e781a，HTTP=200

~~~~text
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

[同版本引用上下文]
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

```
from openai import OpenAIclient = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")# Round 1messages = [{"role": "user", "content": "What's the highest mountain in the world?"}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 1: {messages}")# Round 2messages.append({"role": "user", "content": "What is the second?"})response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 2: {messages}")
```

在第一轮请求时，传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"}]
```

在第二轮请求时：

- 要将第一轮中模型的输出添加到 `messages` 末尾

- 将新的提问添加到 `messages` 末尾

最终传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"},    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest."},    {"role": "user", "content": "What is the second?"}]
```
~~~~

来源#4：`deepseek-prefix-completion.md`，chunk=0，version=4ebb1c1409b3573188a9f2105103b409，HTTP=200

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

[同版本引用上下文]
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

下面给出了对话前缀续写的完整 Python 代码样例。在这个例子中，我们设置 `assistant` 开头的消息为 `"```python\n"` 来强制模型输出 python 代码，并设置 `stop` 参数为 `['```']` 来避免模型的额外解释。

````
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)messages = [    {"role": "user", "content": "Please write quick sort code"},    {"role": "assistant", "content": "```python\n", "prefix": True},]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stop=["```"],)print(response.choices[0].message.content)
````
~~~~

来源#5：`deepseek-fim-guide.md`，chunk=0，version=882a8182be7d5ebf925e34de37f5d0eb，HTTP=200

~~~~text
# DeepSeek API：FIM 补全指南

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全（Beta）](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全（Beta）

在 [FIM (Fill In the Middle) 补全](https://api-docs.deepseek.com/zh-cn/api/create-completion)中，用户可以提供前缀和后缀（可选），模型来补全中间的内容。FIM 常用于内容续写、代码补全等场景。

## 注意事项

- 模型的最大补全长度为 4K。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

[同版本引用上下文]
# DeepSeek API：FIM 补全指南

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[FIM 补全（Beta）](https://api-docs.deepseek.com/zh-cn/guides/fim_completion/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# FIM 补全（Beta）

在 [FIM (Fill In the Middle) 补全](https://api-docs.deepseek.com/zh-cn/api/create-completion)中，用户可以提供前缀和后缀（可选），模型来补全中间的内容。FIM 常用于内容续写、代码补全等场景。

## 注意事项

- 模型的最大补全长度为 4K。

- 用户需要设置 `base_url="https://api.deepseek.com/beta"` 来开启 Beta 功能。

## 样例代码

下面给出了 FIM 补全的完整 Python 代码样例。在这个例子中，我们给出了计算斐波那契数列函数的开头和结尾，来让模型补全中间的内容。

```
from openai import OpenAIclient = OpenAI(    api_key="<your api key>",    base_url="https://api.deepseek.com/beta",)response = client.completions.create(    model="deepseek-flash",    prompt="def fib(a):",    suffix="    return fib(a-1) + fib(a-2)",    max_tokens=128,)print(response.choices[0].text)
```

## 配置 Continue 代码补全插件

[Continue](https://continue.dev) 是一款支持代码补全的 VSCode 插件，您可以参考[这篇文档](https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/continue/README_cn.md)来配置 Continue 以使用代码补全功能。
~~~~

来源#6：`deepseek-models-pricing.md`，chunk=1，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

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

来源#7：`deepseek-responses.md`，chunk=22，version=47a4c8df60e15d7982216687963fc076，HTTP=200

~~~~text
成有效的 JSON，且可能会虚构出您的函数模式中未定义的参数。在调用函数之前，请在您的代码中验证这些入参是否有效。

-

]

usage

object

该响应的 token 用量统计信息。

input_tokens integerrequired

输入 token 数。

input_tokens_details

object

输入 token 的细分信息。

cached_tokens integer

命中上下文缓存的输入 token 数。参考[上下文硬盘缓存](https://api-docs.deepseek.com/guides/kv_cache)。

output_tokens integerrequired

输出 token 数。

output_tokens_details

object

输出 token 的细分信息。

reasoning_tokens integer

模型生成的思维链 token 数。

total_tokens integerrequired

该请求使用的 token 总数（输入 + 输出）。

[同版本引用上下文]
content

object[]

用于 `message` item 时为 `output_text` 内容块列表。用于 `reasoning` item 时为 `reasoning_text` 内容块列表，以明文承载思维链内容。

-

Array [

type string

Possible values: [`output_text`, `reasoning_text`]

text string
-

]

call_id string

用于 `function_call` / `custom_tool_call` / `tool_search_call` item。将工具结果回传给 API 时使用的标识符。

name string

用于 `function_call` / `custom_tool_call` item。要调用的函数或 custom 工具的名称。

arguments string

用于 `function_call` item。模型生成的调用函数的入参，格式为 JSON。请注意，模型并不总是生成有效的 JSON，且可能会虚构出您的函数模式中未定义的参数。在调用函数之前，请在您的代码中验证这些入参是否有效。

-

]

usage

object

该响应的 token 用量统计信息。

input_tokens integerrequired

输入 token 数。

input_tokens_details

object

输入 token 的细分信息。

cached_tokens integer

命中上下文缓存的输入 token 数。参考[上下文硬盘缓存](https://api-docs.deepseek.com/guides/kv_cache)。

output_tokens integerrequired

输出 token 数。

output_tokens_details

object

输出 token 的细分信息。

reasoning_tokens integer

模型生成的思维链 token 数。

total_tokens integerrequired

该请求使用的 token 总数（输入 + 输出）。

```
{  "id": "string",  "object": "response",  "created_at": 0,  "status": "in_progress",  "error": {},  "incomplete_details": {    "reason": "max_output_tokens"  },  "model": "string",  "output": [    {      "type": "message",      "id": "string",      "status": "in_progress",      "role": "assistant",      "content": [        {          "type": "output_text",          "text": "string"        }      ],      "call_id": "string",      "name": "string",      "arguments": "string"    }  ],  "usage": {    "input_tokens": 0,    "input_tokens_details": {      "cached_tokens": 0    },    "output_tokens": 0,    "output_tokens_details": {      "reasoning_tokens": 0    },    "total_tokens": 0  }}
```
~~~~

来源#8：`deepseek-thinking.md`，chunk=3，version=5804eb2d06c65774b4ea7ca978d9f8da，HTTP=200

~~~~text
该参数恒为 `1.0`，传入的值会被忽略。

- `deepseek-v4-pro`：思考模式下会忽略传入值（携带 `tools` 时固定为 `0.95`，否则为 `1.0`）；非思考模式下生效。

在思考模式下，思维链内容通过 `reasoning_content` 参数返回，与 `content` 同级。在后续轮次的请求中，`reasoning_content` 是否需要回传、是否会被拼接进上下文，取决于请求是否携带 `tools` 参数：

- 若请求携带 `tools` 参数：历史轮次的 `reasoning_content` 均应回传给 API，并会被拼接进上下文。详见[工具调用](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/#tool-calls)。

[同版本引用上下文]
# DeepSeek API：思考模式

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 思考模式

DeepSeek 模型支持思考模式：在输出最终回答之前，模型会先输出一段思维链内容，以提升最终答案的准确性。

## 思考模式开关与思考强度控制

|  | 控制参数（OpenAI 格式） | 控制参数（Anthropic 格式） | 控制参数（Responses API 格式） |
| --- | --- | --- | --- |
| 思考模式开关 (1) | {"thinking": {"type": "enabled/disabled"}} | {"reasoning": {"effort": "none/low/high/max"}} (none 表示关闭思考模式) |  |
| 思考强度控制 (2) | {"reasoning_effort": "low/high/max"} | {"output_config": {"effort": "low/high/max"}} |  |

(1) 思考模式默认打开，且 effort 默认为 `high`

(2) 用户设置的 effort 与模型推理 effort 映射表如下：

| 请求传入 effort | 实际映射 effort |
| --- | --- |
| minimal | low |
| low | low |
| medium | high |
| high | high |
| xhigh | high |
| max | max |
| ultra | max |

您在 OpenAI SDK 中使用 Chat Completion 设置 `thinking` 参数时，需要将 `thinking` 参数传入 `extra_body` 中：

```
response = client.chat.completions.create(  model="deepseek-flash",  # ...  reasoning_effort="high",  extra_body={"thinking": {"type": "enabled"}},)
```

## 输入输出参数

思考模式不支持 `temperature`、`presence_penalty`、`frequency_penalty` 参数。请注意，为了兼容已有软件，设置参数不会报错，但也不会生效。

`top_p` 的行为因模型而异：

- `deepseek-flash`：仅在思考模式下生效，有效取值范围为 `0.95`–`1.0`，低于 `0.95` 的取值会按 `0.95` 处理。在非思考模式下，该参数恒为 `1.0`，传入的值会被忽略。

- `deepseek-v4-pro`：思考模式下会忽略传入值（携带 `tools` 时固定为 `0.95`，否则为 `1.0`）；非思考模式下生效。

在思考模式下，思维链内容通过 `reasoning_content` 参数返回，与 `content` 同级。在后续轮次的请求中，`reasoning_content` 是否需要回传、是否会被拼接进上下文，取决于请求是否携带 `tools` 参数：

- 若请求携带 `tools` 参数：历史轮次的 `reasoning_content` 均应回传给 API，并会被拼接进上下文。详见[工具调用](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/#tool-calls)。
~~~~

## N03 · deepseek · insufficient

DeepSeek余额查询接口的说明，能证明我现在余额足够支付下个月所有调用吗？

判分要求：文档不能代替真实余额和未来用量核查；不得以本项目Demo账单冒充DeepSeek账户

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**不能。** 余额查询接口的文档只能说明该接口的调用方式和返回字段含义，不能证明你当前账户的余额，更不能证明余额足以支付下个月所有调用。

具体说明：

1. **接口说明的性质**：`GET /user/balance` 返回 `is_available`（当前账户是否有余额可供 API 调用）和 `balance_infos`（含 `total_balance`、`granted_balance`、`topped_up_balance`）等字段，文档还给出了示例值。但这些是接口的字段定义和示例，不是你的账户实际数据，不能据此判断你的余额状况。来源#1: deepseek-balance.md

2. **“够不够支付下个月”无法由余额接口单独证明**：费用按 token 消耗量 × 模型单价计算，Search/Fetch 按成功请求次数计费，且价格可能变动、DeepSeek 保留修改价格的权利。要判断是否足够，需要结合你下个月的实际用量和届时价格，余额接口本身不提供这些信息。来源#2: deepseek-models-pricing.md、来源#5: deepseek-models-pricing.md

3. **余额不足时的表现**：若账号余额不足，调用会返回 402 错误码，可据此确认账户余额并前往充值页面充值。来源#3: deepseek-errors.md

**建议的下一步**：直接调用 `GET /user/balance` 查询你账户的实时余额，并结合下月预估用量（token 数 × 对应模型单价，注意区分空闲/高峰时段价格）自行测算；如测算后余额偏紧，可提前充值。如果你希望我们协助核查某次实际调用是否因余额不足失败，请提供 request_id、HTTP 状态/错误码、接口地址或发生时间。

来源#1: deepseek-balance.md
来源#2: deepseek-models-pricing.md
来源#3: deepseek-errors.md
来源#4: deepseek-rate-limits.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-files.md
来源#7: deepseek-multi-round.md
来源#8: deepseek-token-usage.md

### 实际引用锚点

来源#1：`deepseek-balance.md`，chunk=0，version=b9d037f89e24599d92ff9324e5649c74，HTTP=200

~~~~text
# DeepSeek API：余额查询

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[查询余额](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 查询余额

```
GET /user/balance
```

查询账号余额

## Responses

- 200

OK, 返回用户余额详情

- application/json

- Schema

- Example (from schema)

- Example

Schema

is_available boolean

当前账户是否有余额可供 API 调用

balance_infos

object[]

-

Array [

currency string

Possible values: [`CNY`, `USD`]

货币，人民币或美元

total_balance string

总的可用余额，包括赠金和充值余额

granted_balance string

未过期的赠金余额

[同版本引用上下文]
# DeepSeek API：余额查询

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[查询余额](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 查询余额

```
GET /user/balance
```

查询账号余额

## Responses

- 200

OK, 返回用户余额详情

- application/json

- Schema

- Example (from schema)

- Example

Schema

is_available boolean

当前账户是否有余额可供 API 调用

balance_infos

object[]

-

Array [

currency string

Possible values: [`CNY`, `USD`]

货币，人民币或美元

total_balance string

总的可用余额，包括赠金和充值余额

granted_balance string

未过期的赠金余额

topped_up_balance string

充值余额

-

]

```
{  "is_available": true,  "balance_infos": [    {      "currency": "CNY",      "total_balance": "110.00",      "granted_balance": "10.00",      "topped_up_balance": "100.00"    }  ]}
```

```
{  "is_available": true,  "balance_infos": [    {      "currency": "CNY",      "total_balance": "110.00",      "granted_balance": "10.00",      "topped_up_balance": "100.00"    }  ]}
```

Loading...
~~~~

来源#2：`deepseek-models-pricing.md`，chunk=4，version=611cccfe0fea5246b2d4347c4a485449，HTTP=200

~~~~text
请注意，当前用户在 DeepSeek Harness/Claude Code/Codex 中使用 DeepSeek API 时，已经会通过 Server 端工具调用访问到 Search/Fetch 接口，这部分 Search/Fetch 接口调用目前未计费，并将于北京时间 2026 年 11 月 1 日 00:00 起按次收取调用费用。

接口用法与完整计费规则详见[网页搜索与抓取](https://api-docs.deepseek.com/zh-cn/guides/search)。

## 扣费规则

模型调用费用 = token 消耗量 × 模型单价；Search 和 Fetch 按上表中的成功请求次数计费。对应的费用将直接从充值余额或赠送余额中进行扣减。
当充值余额与赠送余额同时存在时，优先扣减赠送余额。

产品价格可能发生变动，DeepSeek 保留修改价格的权利。请您依据实际用量按需充值，定期查看此页面以获知最新价格信息。

[同版本引用上下文]
请注意，当前用户在 DeepSeek Harness/Claude Code/Codex 中使用 DeepSeek API 时，已经会通过 Server 端工具调用访问到 Search/Fetch 接口，这部分 Search/Fetch 接口调用目前未计费，并将于北京时间 2026 年 11 月 1 日 00:00 起按次收取调用费用。

接口用法与完整计费规则详见[网页搜索与抓取](https://api-docs.deepseek.com/zh-cn/guides/search)。

## 扣费规则

模型调用费用 = token 消耗量 × 模型单价；Search 和 Fetch 按上表中的成功请求次数计费。对应的费用将直接从充值余额或赠送余额中进行扣减。
当充值余额与赠送余额同时存在时，优先扣减赠送余额。

产品价格可能发生变动，DeepSeek 保留修改价格的权利。请您依据实际用量按需充值，定期查看此页面以获知最新价格信息。
~~~~

来源#3：`deepseek-errors.md`，chunk=0，version=a5df631500ec55a689b45d1a015e55ff，HTTP=200

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

来源#4：`deepseek-rate-limits.md`，chunk=0，version=8359173480f55fa9bb47316d3477d5aa，HTTP=200

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

来源#6：`deepseek-files.md`，chunk=4，version=4412a6fe0a9a5724ae0821badf537a85，HTTP=200

~~~~text
```
curl https://api.deepseek.com/files \  -H "Authorization: Bearer <DeepSeek API Key>"
```

查询参数：

| 参数 | 说明 |
| --- | --- |
| after | 用于分页的 file_id 游标；返回此文件之后的文件。 |
| limit | 返回的文件数量，取值在 1 到 1000 之间。 |
| order | 按创建时间排序： asc （默认）或 desc 。 |
| purpose | 按用途过滤。仅支持 user_data 。 |

响应为分页列表：

```
{  "object": "list",  "data": [    {      "id": "file-api-xxxxxxxxxxxxxxxx",      "object": "file",      "bytes": 102400,      "created_at": 1700000000,      "filename": "image.jpg",      "purpose": "user_data"    }  ],  "first_id": "file-api-xxxxxxxxxxxxxxxx",  "last_id": "file-api-xxxxxxxxxxxxxxxx",

[同版本引用上下文]
```
curl https://api.deepseek.com/files \  -H "Authorization: Bearer <DeepSeek API Key>"
```

查询参数：

| 参数 | 说明 |
| --- | --- |
| after | 用于分页的 file_id 游标；返回此文件之后的文件。 |
| limit | 返回的文件数量，取值在 1 到 1000 之间。 |
| order | 按创建时间排序： asc （默认）或 desc 。 |
| purpose | 按用途过滤。仅支持 user_data 。 |

响应为分页列表：

```
{  "object": "list",  "data": [    {      "id": "file-api-xxxxxxxxxxxxxxxx",      "object": "file",      "bytes": 102400,      "created_at": 1700000000,      "filename": "image.jpg",      "purpose": "user_data"    }  ],  "first_id": "file-api-xxxxxxxxxxxxxxxx",  "last_id": "file-api-xxxxxxxxxxxxxxxx",  "has_more": false}
```

## 查询文件信息

```
info = client.files.retrieve("file-api-xxxxxxxxxxxxxxxx")print(info.filename, info.bytes)
```

```
curl https://api.deepseek.com/files/file-api-xxxxxxxxxxxxxxxx \  -H "Authorization: Bearer <DeepSeek API Key>"
```

## 删除文件

```
client.files.delete("file-api-xxxxxxxxxxxxxxxx")
```

```
curl -X DELETE https://api.deepseek.com/files/file-api-xxxxxxxxxxxxxxxx \  -H "Authorization: Bearer <DeepSeek API Key>"
```

```
{  "id": "file-api-xxxxxxxxxxxxxxxx",  "object": "file",  "deleted": true}
```

## 在对话请求中使用已上传的文件

使用 `file` 内容块引用返回的 `file_id`：

```
response = client.chat.completions.create(    model="deepseek-flash",    messages=[        {            "role": "user",            "content": [                {"type": "text", "text": "这张图片里有什么？"},                {"type": "file", "file_id": "file-api-xxxxxxxxxxxxxxxx"},            ],        },    ],)print(response.choices[0].message.content)
```

文件归属于你的账号：同一账号下的所有 API key 共享文件，且可被任一 API 家族引用。注意：通过 Anthropic 兼容 `/messages` 端点引用文件时需携带 `anthropic-beta: files-api-2025-04-14` 请求头。

与内联（base64）图片不同，通过 `file_id` 引用的文件不受 32 MiB 单图限制，请求中单张最大 64 MiB。
~~~~

来源#7：`deepseek-multi-round.md`，chunk=0，version=e53c4589cafa5c27b618be4c292e781a，HTTP=200

~~~~text
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

[同版本引用上下文]
# DeepSeek API：多轮对话

厂商：DeepSeek；产品范围：DeepSeek API；核对日期：2026-10-19。
官方来源：[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

本指南将介绍如何使用 DeepSeek `/chat/completions` API 进行多轮对话。

DeepSeek `/chat/completions` API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

```
from openai import OpenAIclient = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")# Round 1messages = [{"role": "user", "content": "What's the highest mountain in the world?"}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 1: {messages}")# Round 2messages.append({"role": "user", "content": "What is the second?"})response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,)messages.append(response.choices[0].message)print(f"Messages Round 2: {messages}")
```

在第一轮请求时，传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"}]
```

在第二轮请求时：

- 要将第一轮中模型的输出添加到 `messages` 末尾

- 将新的提问添加到 `messages` 末尾

最终传递给 API 的 `messages` 为：

```
[    {"role": "user", "content": "What's the highest mountain in the world?"},    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest."},    {"role": "user", "content": "What is the second?"}]
```
~~~~

来源#8：`deepseek-token-usage.md`，chunk=0，version=17decf9b6c8356c6a67b7826e5e99e08，HTTP=200

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

[同版本引用上下文]
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

[deepseek_tokenizer.zip](https://cdn.deepseek.com/api-docs/deepseek_v4_tokenizer.zip)

## 计算图片 Token 用量

您可以通过图片尺寸估算图片所占用的 token 数量。图片在进入模型前会被自动缩放，每张图片消耗的 token 数存在上限，详见[图像理解](https://api-docs.deepseek.com/zh-cn/guides/vision#token-usage)。

此处为估算值，实际处理时转换得到的 token 数量可能存在一定误差，请以接口返回的用量为准。

#### 图片 Token 计算器

宽度 (px)高度 (px)
~~~~

## N04 · qwen · fact

Qwen的OpenAI兼容流式聊天，想收到Token用量，应把include_usage放在哪里？请写参数结构。

判分要求：启用stream=true；stream_options={include_usage:true}，不是顶层include_usage

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

在 Qwen 的 OpenAI 兼容流式聊天中，`include_usage` 不是顶层参数，而是放在 `stream_options` 对象里，与 `stream: true` 一起使用。设置后，**最后一个返回的数据块**会包含 Token 消耗信息。

参数结构：

```json
{
  "model": "qwen-plus",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

Python SDK 写法：

```python
completion = client.chat.completions.create(
    model="qwen-plus",
    messages=[{"role": "user", "content": "你好"}],
    stream=True,
    stream_options={"include_usage": True}
)
```

处理响应时注意：当 `include_usage` 为 `true` 时，最后一个 chunk 的 `choices` 是空数组，需要跳过内容拼接，并通过 `chunk.usage` 读取 Token 用量。

适用范围：以上为 Qwen API 的 OpenAI 兼容接口规则；DashScope 原生接口的流式参数（如 `stream`、`incremental_output`）是另一套用法，不能把 OpenAI 兼容的 `stream_options` 当作 DashScope 原生接口的通用方案。

来源#1: qwen-streaming.md
来源#2: qwen-thinking.md
来源#3: qwen-streaming.md
来源#4: qwen-dashscope.md
来源#5: qwen-streaming.md
来源#6: qwen-dashscope.md
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

来源#2：`qwen-thinking.md`，chunk=4，version=e6859f3d2b78563c809872285470797d，HTTP=200

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

来源#3：`qwen-streaming.md`，chunk=10，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

~~~~text
messages: [
                        { role: "system", content: "You are a helpful assistant." },
                        { role: "user", content: "请介绍一下自己" },
                    ],
                    stream: true,
                    // 目的：在最后一个chunk中获取本次请求的Token用量。
                    stream_options: { include_usage: true },
                });

                // 3. 处理流式响应
                const contentParts = [];
                process.stdout.write("AI: ");

[同版本引用上下文]
<Tab title="Node.js">
        ```javascript expandable
        import OpenAI from "openai";

        async function main() {
            // 1. 准备工作：初始化客户端
            // 建议通过环境变量配置API Key，避免硬编码。
            if (!process.env.DASHSCOPE_API_KEY) {
                throw new Error("请设置环境变量 DASHSCOPE_API_KEY");
            }
            const client = new OpenAI({
                // 若没有配置环境变量，请将下行替换为：apiKey:"sk-xxx",
                // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
                apiKey: process.env.DASHSCOPE_API_KEY,
                // 以下为华北2（北京）地域的URL，调用时请将WorkspaceId替换为真实的业务空间ID，各地域的URL不同。
                baseURL: "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            });

            try {
                // 2. 发起流式请求
                const stream = await client.chat.completions.create({
                    model: "qwen-plus",
                    messages: [
                        { role: "system", content: "You are a helpful assistant." },
                        { role: "user", content: "请介绍一下自己" },
                    ],
                    stream: true,
                    // 目的：在最后一个chunk中获取本次请求的Token用量。
                    stream_options: { include_usage: true },
                });

                // 3. 处理流式响应
                const contentParts = [];
                process.stdout.write("AI: ");
~~~~

来源#4：`qwen-dashscope.md`，chunk=80，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
随机数种子。用于确保在相同输入和参数下生成结果可复现。若调用时传入相同的 `seed` 且其他参数不变，模型将尽可能返回相同结果。

        取值范围：`[0,2 31 −1]`。

        <Accordion title="seed默认值">
          其余模型均为1234。
        </Accordion>

        > 通过HTTP调用时，请将 <strong>seed</strong>放入 <strong>parameters</strong> 对象中。

        <strong>stream</strong>`boolean`（可选）默认值为`false`

        是否流式输出回复。参数值：

        - false：模型生成完所有内容后一次性返回结果。
        - true：边生成边输出，即每生成一部分内容就立即输出一个片段（chunk）。

        > 该参数仅支持Python SDK。通过Java SDK实现流式输出请通过`streamCall`接口调用；通过HTTP实现流式输出请在Header中指定`X-DashScope-SSE`为`enable`。

        > Qwen3商业版（思考模式）、Qwen3开源版、QwQ、QVQ只支持流式输出。

[同版本引用上下文]
随机数种子。用于确保在相同输入和参数下生成结果可复现。若调用时传入相同的 `seed` 且其他参数不变，模型将尽可能返回相同结果。

        取值范围：`[0,2 31 −1]`。

        <Accordion title="seed默认值">
          其余模型均为1234。
        </Accordion>

        > 通过HTTP调用时，请将 <strong>seed</strong>放入 <strong>parameters</strong> 对象中。

        <strong>stream</strong>`boolean`（可选）默认值为`false`

        是否流式输出回复。参数值：

        - false：模型生成完所有内容后一次性返回结果。
        - true：边生成边输出，即每生成一部分内容就立即输出一个片段（chunk）。

        > 该参数仅支持Python SDK。通过Java SDK实现流式输出请通过`streamCall`接口调用；通过HTTP实现流式输出请在Header中指定`X-DashScope-SSE`为`enable`。

        > Qwen3商业版（思考模式）、Qwen3开源版、QwQ、QVQ只支持流式输出。

        <strong>incremental\_output</strong>`boolean`（可选）默认为`false`（Qwen3-Max、Qwen3-VL、[Qwen3 开源版](/zh/model-studio/models)、[QwQ](/zh/model-studio/deep-thinking) 、[QVQ](/zh/model-studio/visual-reasoning)模型默认值为 `true`）

        在流式输出模式下是否开启增量输出。推荐您优先设置为`true`。

        参数值：

        - false：每次输出为当前已经生成的整个序列，最后一次输出为生成的完整结果。

        ```plaintext
        I
        I like
        I like apple
        I like apple.
        ```

        - true（推荐）：增量输出，即后续输出内容不包含已输出的内容。您需要实时地逐个读取这些片段以获得完整的结果。

        ```plaintext
        I
        like
        apple
        .
        ```

        > Java SDK中为<strong>incrementalOutput</strong>\*。\*通过HTTP调用时，请将 <strong>incremental\_output</strong>放入 <strong>parameters</strong> 对象中。

        > QwQ 模型与思考模式下的 Qwen3 模型只支持设置为 `true`。由于 Qwen3 商业版模型默认值为`false`，您需要在思考模式下手动设置为 `true`。

        > Qwen3 开源版模型不支持设置为 `false`。

        <strong>response\_format</strong>`object` （可选） 默认值为`{"type": "text"}`

        返回内容的格式。可选值：

        - `{"type": "text"}`：输出文字回复；
        - `{"type": "json_object"}`：输出标准格式的JSON字符串。
        - `{"type": "json_schema", "json_schema": {...}}`：输出严格符合指定 JSON Schema 的JSON字符串，可精确控制输出结构与字段类型。
~~~~

来源#5：`qwen-streaming.md`，chunk=60，version=d47058000f015b62a5722fa3bee5d02d，HTTP=200

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

来源#6：`qwen-dashscope.md`，chunk=62，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
h）。

        > 通过HTTP调用时，请将 <strong>reasoning\_effort</strong> 放入 <strong>parameters</strong> 对象中。

        <strong>tool\_stream</strong> `boolean` （可选）默认值为 `false`

        仅影响复杂工具参数的流式输出行为，仅在流式调用时生效。普通工具参数（所有参数类型均为string）只要开启流式调用即可流式输出，`tool_stream`对其无影响。复杂工具是指工具定义中某些参数类型为array或object。当前仅Qwen和GLM系列支持。

        <strong>Qwen系列支持列表：</strong>

        - qwen-max系列：qwen3.8-max系列、qwen3.7-max系列的文本模态
        - qwen-plus系列：qwen3.7-plus系列、qwen3.6-plus系列的文本模态，以及qwen3.5-plus系列的全模态
        - qwen-flash系列：qwen3.8-flash系列、qwen3.7-flash系列、qwen3.6-flash系列、qwen3.5-flash的全模态

[同版本引用上下文]
<strong>glm-5.3、ZHIPU/GLM-5.3、ZHIPU/GLM-5.3-Flash、ZHIPU/GLM-5.3-FlashX 与 kimi-k3（阿里云直供）模型：默认值为</strong>`max`

        可选值：

        - `max`（默认）：深度推理
        - `high`：增强推理
        - `low`：轻度推理

        该模型始终开启思考，`enable_thinking` 仅支持 `true`，传入 `false` 会导致 API 请求失败。

        <strong>deepseek-v4-flash-0731 与 deepseek-v4-pro-0813 模型：默认值为</strong>`high`

        可选值：

        - `max`：最大力度推理
        - `high`（默认）：高力度推理
        - `low`：低力度推理

        出于兼容性考虑，`medium` 映射为 high，`xhigh` 映射为 high。

        <strong>qwen3.8系列模型：默认值为</strong>`xhigh`

        可选值：

        - `xhigh`（默认）：高力度推理
        - `medium`：中力度推理
        - `low`：低力度推理

        `max` 映射为 xhigh，`high` 映射为 xhigh，`minimal` 映射为 low，`none` 映射为 enable\_thinking=False。

        > 设置上述可选值及映射值以外的值将会报错。

        <strong>重要：</strong>qwen3.8 系列不支持 reasoning\_effort 与 thinking\_budget 同时设置，同时设置会报错。但两者支持互转：

        - 未设置 thinking\_budget 时，reasoning\_effort 档位自动映射 thinking\_budget：`low` 对应 4096，`medium` 对应 16384，`xhigh` 对应 262144。
        - 未设置 reasoning\_effort 时，thinking\_budget 自动映射回 reasoning\_effort：0\~4096 对应 `low`，4097\~16384 对应 `medium`，16385\~262144 对应 `xhigh`。
        - 两者均未设置时，使用默认 thinking\_budget（131072），默认 reasoning\_effort（xhigh）。

        > 通过HTTP调用时，请将 <strong>reasoning\_effort</strong> 放入 <strong>parameters</strong> 对象中。

        <strong>tool\_stream</strong> `boolean` （可选）默认值为 `false`

        仅影响复杂工具参数的流式输出行为，仅在流式调用时生效。普通工具参数（所有参数类型均为string）只要开启流式调用即可流式输出，`tool_stream`对其无影响。复杂工具是指工具定义中某些参数类型为array或object。当前仅Qwen和GLM系列支持。

        <strong>Qwen系列支持列表：</strong>

        - qwen-max系列：qwen3.8-max系列、qwen3.7-max系列的文本模态
        - qwen-plus系列：qwen3.7-plus系列、qwen3.6-plus系列的文本模态，以及qwen3.5-plus系列的全模态
        - qwen-flash系列：qwen3.8-flash系列、qwen3.7-flash系列、qwen3.6-flash系列、qwen3.5-flash的全模态
~~~~

来源#7：`qwen-chat-completions.md`，chunk=82，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
](/zh/model-studio/qwen-code-interpreter)

        可选值：

        - `true`：开启
        - `false`：不开启

        > 该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 <strong>extra\_body</strong> 对象中。配置方式为：`extra_body={"enable_code_interpreter": xxx}`。

        <strong>seed</strong>`integer`（可选）

        随机数种子。用于确保在相同输入和参数下生成结果可复现。若调用时传入相同的 `seed` 且其他参数不变，模型将尽可能返回相同结果。

        取值范围：`[0,2 31 −1]`。

        <Accordion title="seed默认值">
          其余模型均为1234。
        </Accordion>

        <strong>logprobs</strong> `boolean` （可选）默认值为 `false`

        是否返回输出 Token 的对数概率，可选值：

        - `true`

[同版本引用上下文]
- qwen-max系列：qwen3.8-max系列、qwen3.7-max系列的文本模态
        - qwen-plus系列：qwen3.7-plus系列、qwen3.6-plus系列的文本模态，以及qwen3.5-plus系列的全模态
        - qwen-flash系列：qwen3.8-flash系列、qwen3.7-flash系列、qwen3.6-flash系列、qwen3.5-flash系列的全模态

        <strong>Qwen系列使用参考：</strong>

        tool\_stream仅影响复杂工具参数的情况。普通工具参数只要开启`stream=true`就会流式输出。复杂工具是指工具定义中某些参数类型为array或object。

        - `tool_stream=false`：复杂工具参数会一次性输出，默认行为，复杂格式会更准确。
        - `tool_stream=true`：复杂工具参数会流式输出，复杂格式没有超时风险。

        <strong>GLM系列支持列表：</strong>glm-5、glm-5.1（阿里云直供）。

        <strong>GLM系列使用参考：</strong>

        - `tool_stream=false`：工具参数会一次性输出，默认行为，复杂格式会更准确。
        - `tool_stream=true`：工具参数会流式输出，复杂格式没有超时风险。

        > 该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 <strong>extra\_body</strong> 对象中。配置方式为：`extra_body={"tool_stream": true}`。

        <strong>enable\_code\_interpreter</strong> `boolean` （可选）默认值为 `false`

        是否开启代码解释器功能。相关文档：[代码解释器](/zh/model-studio/qwen-code-interpreter)

        可选值：

        - `true`：开启
        - `false`：不开启

        > 该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 <strong>extra\_body</strong> 对象中。配置方式为：`extra_body={"enable_code_interpreter": xxx}`。

        <strong>seed</strong>`integer`（可选）

        随机数种子。用于确保在相同输入和参数下生成结果可复现。若调用时传入相同的 `seed` 且其他参数不变，模型将尽可能返回相同结果。

        取值范围：`[0,2 31 −1]`。

        <Accordion title="seed默认值">
          其余模型均为1234。
        </Accordion>

        <strong>logprobs</strong> `boolean` （可选）默认值为 `false`

        是否返回输出 Token 的对数概率，可选值：

        - `true`

          返回
        - `false`

          不返回

        > 思考阶段生成的内容（`reasoning_content`）不会返回对数概率。

        <Accordion title="支持的模型">
          - qwen-plus系列的快照模型（不包含稳定版模型）
          - qwen3-vl-plus系列模型（包含稳定版模型）
          - Qwen3 开源模型
        </Accordion>

        <strong>top\_logprobs</strong> `integer` （可选）默认值为0
~~~~

## N05 · qwen · fact

Qwen文本向量检索中，text_type的query与document各用于哪一侧？不传时是什么？

判分要求：检索查询query，底库document；默认document；对称任务可用默认

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

针对 Qwen 文本向量接口中 `text_type` 参数的用法，根据检索到的文档说明如下：

**1. query 与 document 各用于哪一侧**

`text_type` 用于区分非对称检索任务中的两类文本：

- **query**：用于查询侧，即用户发起的检索查询文本。
- **document**：用于底库侧，即入库（写入向量库）的文档文本。

文档建议：对检索这类非对称任务，为达到更好的检索效果，应区分查询文本（query）和底库文本（document）类型；入库、聚类、分类等对称任务可以不用特殊指定。

**2. 不传时是什么**

不传 `text_type` 时，采用系统默认值 **`document`**。

**补充说明（同一文档中的相关规则）**：`instruct` 参数仅在 `text_type` 取值为 `query` 时生效，并按输入文本条数计入 Token 用量；当 `text_type` 为 `document` 或未设置时，该参数不生效，也不计入 Token 用量。

以上为文档通用规则说明，不代表任何具体账户或单次请求的实际状态。

来源#1: qwen-embedding-api.md
来源#2: qwen-embedding-api.md
来源#3: qwen-function-calling.md
来源#4: qwen-embedding-api.md
来源#5: qwen-embedding-v4.md
来源#6: qwen-context-cache.md
来源#7: qwen-multi-round.md

### 实际引用锚点

来源#1：`qwen-embedding-api.md`，chunk=66，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
> 通过 HTTP 调用时，请将 <strong>text\_type</strong>放入parameters对象中。

        文本转换为向量后可以应用于检索、聚类、分类等下游任务，对检索这类非对称任务为了达到更好的检索效果建议区分查询文本（query）和底库文本（document）类型，入库、聚类、分类等对称任务可以不用特殊指定，采用系统默认值`document`即可。

        <strong>dimension</strong> `integer` <strong>可选</strong>

        > 通过 HTTP 调用时，请将 <strong>dimension</strong>放入parameters对象中。

        指定的向量维度，必须为以下值之一：`2560（仅适用于qwen3.7-text-embedding）、`2048（仅适用于`text-embedding-v4`）、1536（仅适用于`text-embedding-v4`）1024、768、512、256、128 或 64，默认值为1024。

        <strong>output\_type</strong> `string` <strong>可选</strong>

[同版本引用上下文]
> 通过 HTTP 调用时，请将 <strong>text\_type</strong>放入parameters对象中。

        文本转换为向量后可以应用于检索、聚类、分类等下游任务，对检索这类非对称任务为了达到更好的检索效果建议区分查询文本（query）和底库文本（document）类型，入库、聚类、分类等对称任务可以不用特殊指定，采用系统默认值`document`即可。

        <strong>dimension</strong> `integer` <strong>可选</strong>

        > 通过 HTTP 调用时，请将 <strong>dimension</strong>放入parameters对象中。

        指定的向量维度，必须为以下值之一：`2560（仅适用于qwen3.7-text-embedding）、`2048（仅适用于`text-embedding-v4`）、1536（仅适用于`text-embedding-v4`）1024、768、512、256、128 或 64，默认值为1024。

        <strong>output\_type</strong> `string` <strong>可选</strong>

        > 通过 HTTP 调用时，请将 <strong>output\_type</strong>放入parameters对象中。

        用户指定输出离散向量表示只适用于`qwen3.7-text-embedding、``text-embedding-v3`与`text-embedding-v4`模型，取值在dense、sparse、dense\&sparse之间，默认取dense，只输出连续向量。稀疏向量输出（`sparse`和`dense&sparse`）仅支持通过 DashScope 接口调用。

        <strong>instruct</strong> `string` <strong>可选</strong>

        添加自定义任务说明，可用于指导模型理解查询意图。建议使用英文撰写，通常可带来约 1%–5% 的效果提升。

        该参数仅在 `text_type` 取值为 `query` 时生效，并按输入文本的条数计入 Token 用量。`text_type` 取值为 `document` 或未设置 `text_type` 时，该参数不生效，也不计入 Token 用量。
      </td>

      <td>
        <Tabs>
          <Tab title="输入字符串">
            <CodeGroup dropdown>
              ```python Python
              import dashscope
              from http import HTTPStatus
              # 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
              dashscope.base_http_api_url = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1"
~~~~

来源#2：`qwen-embedding-api.md`，chunk=0，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
# Qwen / 阿里云百炼：向量接口

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[同步接口API详情](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 同步接口API详情

> 通用文本向量模型可将文本数据转换为数值向量，用于语义搜索、推荐、聚类、分类等下游任务。

<meta property="og:title" content="同步接口API详情" />

## 模型概览 <span id="0e41425c577u4" />

<Tabs>
  <Tab title="北京">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}>
      <colgroup>
        <col style={{ width: "16.89%" }} />

        <col style={{ width: "16.8%" }} />

[同版本引用上下文]
# Qwen / 阿里云百炼：向量接口

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[同步接口API详情](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 同步接口API详情

> 通用文本向量模型可将文本数据转换为数值向量，用于语义搜索、推荐、聚类、分类等下游任务。

<meta property="og:title" content="同步接口API详情" />

## 模型概览 <span id="0e41425c577u4" />

<Tabs>
  <Tab title="北京">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}>
      <colgroup>
        <col style={{ width: "16.89%" }} />

        <col style={{ width: "16.8%" }} />

        <col style={{ width: "6.85%" }} />

        <col style={{ width: "9.75%" }} />

        <col style={{ width: "11.39%" }} />

        <col style={{ width: "24.03%" }} />

        <col style={{ width: "14.29%" }} />
      </colgroup>

      <thead>
        <tr>
          <th>
            <strong>模型名称</strong>
          </th>

          <th>
            <strong>向量维度</strong>
          </th>

          <th>
            <strong>最大行数</strong>
          </th>

          <th>
            <strong>单行最大</strong>[Token](/zh/model-studio/billing-for-model-studio)<strong>数</strong>
          </th>

          <th>
            <strong>单价（每千输入Token）</strong>
          </th>

          <th>
            <strong>支持语种</strong>
          </th>

          <th>
            <strong>免费额度</strong>[（注）](/zh/model-studio/new-free-quota#977b13081ab56)
          </th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td>
            qwen3.7-text-embedding
          </td>

          <td>
            2560、2,048、1,536、1,024（默认）、768、512、256
          </td>

          <td>
            20
          </td>

          <td>
            128,000
          </td>

          <td>
            0.0005元
~~~~

来源#3：`qwen-function-calling.md`，chunk=352，version=d11353e48f7a58c692d4dad7870d011d，HTTP=200

~~~~text
- <strong>语义检索</strong>

  将工具描述信息（`description`）通过 Embedding 模型转化为向量，并存入向量数据库。当用户查询时，将查询向量通过向量相似度搜索，召回最相关的 Top-K 个工具。
- <strong>混合检索</strong>

  将语义检索的“模糊匹配”能力与传统关键词或元数据标签的“精确匹配”能力相结合。为工具添加 `tags` 或 `keywords` 字段，检索时同时进行向量搜索和关键词过滤，可以大幅提升高频或特定场景下的召回精准度。
- <strong>轻量级 LLM 路由器</strong>

  对于更复杂的路由逻辑，可以使用一个更小、更快、更便宜的模型（如 Qwen-Flash）作为前置“路由模型”。它的任务是根据用户问题输出相关的工具名称列表。

<strong>实践建议</strong>

[同版本引用上下文]
- <strong>语义检索</strong>

  将工具描述信息（`description`）通过 Embedding 模型转化为向量，并存入向量数据库。当用户查询时，将查询向量通过向量相似度搜索，召回最相关的 Top-K 个工具。
- <strong>混合检索</strong>

  将语义检索的“模糊匹配”能力与传统关键词或元数据标签的“精确匹配”能力相结合。为工具添加 `tags` 或 `keywords` 字段，检索时同时进行向量搜索和关键词过滤，可以大幅提升高频或特定场景下的召回精准度。
- <strong>轻量级 LLM 路由器</strong>

  对于更复杂的路由逻辑，可以使用一个更小、更快、更便宜的模型（如 Qwen-Flash）作为前置“路由模型”。它的任务是根据用户问题输出相关的工具名称列表。

<strong>实践建议</strong>

- <strong>保持候选集精简</strong>：无论使用何种方法，最终提供给主模型的工具数量建议<strong>不超过 20 个</strong>。这是在模型认知负荷、成本、延迟和准确率之间的最佳平衡点。
- <strong>分层过滤策略</strong>：可以构建一个漏斗式的路由策略。例如，先用成本极低的关键词/规则匹配进行第一轮筛选，过滤掉明显不相关的工具，再对剩余的工具进行语义检索，从而提高效率和质量。

### 工具安全性原则 <span id="438f2c17bc50x" /> <span id="24f0151c8bc54" />

向大模型开放工具执行能力时，安全是首要考量。核心原则：“最小权限”和“人类确认”。

- <strong>最小权限原则</strong>：为模型提供的工具集应严格遵守最小权限原则。默认情况下，工具应是只读的（如查询天气、搜索文档），避免直接提供任何涉及状态变更或资源操作的“写”权限。
- <strong>危险工具隔离</strong>：请勿向大模型直接提供危险工具，例如执行任意代码（`code interpreter`）、操作文件系统（`fs.delete`）、执行数据库删除或更新操作（`db.drop_table`）或涉及资金流转的工具（`payment.transfer`）。
- <strong>人类参与</strong>：对于所有高权限或不可逆的操作，必须引入人工审核和确认环节。模型可以生成操作请求，但最终的执行“按钮”必须由人类用户点击。例如，模型可以准备好一封邮件，但发送操作需要用户确认。

### 用户体验优化 <span id="c9653409d73qi" /> <span id="ca77c3eeccppz" />

Function Calling 链路较长，任何环节出问题都可能影响用户体验。

#### 处理工具运行失败 <span id="226e299496dqg" /> <span id="de16e4dc96qjl" />

工具运行失败是常见情况，可采取以下策略：

- <strong>最大重试次数</strong>：设置合理的重试上限（例如 3 次），避免因连续失败导致用户长时间等待或系统资源浪费。
- <strong>提供兜底话术</strong>：当重试耗尽或遇到无法解决的错误时，应向用户返回清晰、友好的提示信息，例如：“抱歉，我暂时无法查询到相关信息，可能是服务有些繁忙，请您稍后再试。”

#### 应对处理延迟 <span id="df704a5ddcq11" /> <span id="d241d77570f5a" />

较高延迟会降低用户满意度，需从前端交互和后端两方面优化。

- <strong>设置超时时间</strong>：为 Function Calling 的每一步设置独立且合理的超时时间。一旦超时，应立即中断操作并给出反馈。
- <strong>提供即时反馈</strong>：开始执行 Function Calling 时，建议在界面上给出提示，如“正在为您查询天气...”、“正在搜索相关信息...”，向用户实时反馈处理进度。

## 计费说明 <span id="61c4cd0841kdo" /> <span id="cf2f65edde0il" />
~~~~

来源#4：`qwen-embedding-api.md`，chunk=103，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
任务输出信息。

        <Accordion title="属性" defaultOpen>
          <strong>embeddings</strong>`array`

          本次请求的算法输出内容，是一个由结构组成的数组，每一个数组中包含一个对应的输入 text 的算法输出内容。

          <Accordion title="属性">
            <strong>sparse\_embedding</strong> `array`

            对应字符串的算法输出离散向量表示 （sparse embedding仅适用于`text-embedding-v3`与`text-embedding-v4`）。

            <Accordion title="属性">
              <strong>index</strong> `integer`

              词汇或字符在词汇表中的位置索引。

              <strong>value</strong> `float`

              表示该 `Token` 的权重或重要性分数，值越高，表示该 `Token` 在当前文本上下文中的重要性或相关性越大。

[同版本引用上下文]
<col style={{ width: "50%" }} />
  </colgroup>

  <tbody>
    <tr>
      <td>
        ### 响应对象 <span id="e9c6861476m70" />

        <strong>status\_code</strong> `string`

        状态码，表示请求的执行结果（如 200 表示成功）。

        <strong>request\_id</strong> `string`

        请求唯一标识。可用于请求明细溯源和问题排查。

        <strong>code</strong> `string`

        请求失败，表示错误码，成功时返回参数中该参数为空。

        <strong>message</strong> `string`

        请求失败，表示失败详细信息，成功时返回参数中该参数为空。

        <strong>output</strong>`object`

        任务输出信息。

        <Accordion title="属性" defaultOpen>
          <strong>embeddings</strong>`array`

          本次请求的算法输出内容，是一个由结构组成的数组，每一个数组中包含一个对应的输入 text 的算法输出内容。

          <Accordion title="属性">
            <strong>sparse\_embedding</strong> `array`

            对应字符串的算法输出离散向量表示 （sparse embedding仅适用于`text-embedding-v3`与`text-embedding-v4`）。

            <Accordion title="属性">
              <strong>index</strong> `integer`

              词汇或字符在词汇表中的位置索引。

              <strong>value</strong> `float`

              表示该 `Token` 的权重或重要性分数，值越高，表示该 `Token` 在当前文本上下文中的重要性或相关性越大。

              <strong>token</strong> `string`

              实际的文本单元或词汇表中的词。
            </Accordion>

            <strong>embedding</strong> `array`

            对应字符串的算法输出连续向量表示 （dense embedding)。

            <strong>text\_index</strong> `integer`

            本结构中的算法结果对应的输入文字在输入数组中的索引值。
          </Accordion>
        </Accordion>

        <strong>usage</strong>`object`

        本次请求的 Token 用量。`qwen3.7-text-embedding-flash` 返回 `prompt_tokens` 和 `total_tokens`；其他已上线的文本向量模型仅返回 `total_tokens`。

        <Accordion title="属性" defaultOpen>
          <strong>prompt\_tokens</strong> `integer`

          仅 `qwen3.7-text-embedding-flash` 返回。表示本次请求输入内容的 Token 总数，取值与 `total_tokens` 相同。
~~~~

来源#5：`qwen-embedding-v4.md`，chunk=0，version=52339fbb07d75e06a3325c666b05528e，HTTP=200

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

[同版本引用上下文]
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

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际
~~~~

来源#6：`qwen-context-cache.md`，chunk=108，version=adfbf3521c185946b90870bd3b32d606，HTTP=200

~~~~text
rong>基于长文本的问答</strong>

   适用于需要针对固定的长文本（如小说、教材、法律文件等）发送多次请求的业务场景。

   <strong>第一次请求的消息数组</strong>

```python
messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
          {"role": "user","content": "<文章内容> 这篇课文表达了作者怎样的思想感情？"}]
```

<strong>之后请求的消息数组</strong>

```python
messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
          {"role": "user","content": "<文章内容> 请赏析这篇课文的第三自然段。"}]
```

虽然提问的问题不同，但都基于同一篇文章。相同的系统提示和文章内容构成了大量重复的前缀信息，有较大概率命中缓存。
2\. <strong>代码自动补全</strong>

[同版本引用上下文]
}
          }
        }
        ```
      </Tab>

      <Tab title="Anthropic 兼容">
        当您使用 Anthropic兼容的方式调用视觉理解模型并触发了隐式缓存后，命中缓存的 Token 数会体现在 `usage.cache_read_input_tokens` 字段中（与文本生成模型一致）。

        ```json
        {
          "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
          "type": "message",
          "role": "assistant",
          "content": [
            {
              "type": "text",
              "text": "这张图片展示了一位女性和一只狗在海滩上互动的温馨场景。"
            }
          ],
          "model": "qwen3-vl-plus",
          "stop_reason": "end_turn",
          "usage": {
            "input_tokens": 369,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 896,
            "output_tokens": 28
          }
        }
        ```
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

### 典型场景 <span id="c54101d34fvj1" />

如果您的不同请求有着相同的前缀信息，上下文缓存可以有效提升这些请求的推理速度，降低推理成本与首包延迟。以下是几个典型的应用场景：

1. <strong>基于长文本的问答</strong>

   适用于需要针对固定的长文本（如小说、教材、法律文件等）发送多次请求的业务场景。

   <strong>第一次请求的消息数组</strong>

```python
messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
          {"role": "user","content": "<文章内容> 这篇课文表达了作者怎样的思想感情？"}]
```

<strong>之后请求的消息数组</strong>

```python
messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
          {"role": "user","content": "<文章内容> 请赏析这篇课文的第三自然段。"}]
```

虽然提问的问题不同，但都基于同一篇文章。相同的系统提示和文章内容构成了大量重复的前缀信息，有较大概率命中缓存。
2\. <strong>代码自动补全</strong>

在代码自动补全场景，大模型会结合上下文中存在的代码进行代码自动补全。随着用户的持续编码，代码的前缀部分会保持不变。上下文缓存可以缓存之前的代码，提升补全速度。
3\. <strong>多轮对话</strong>

实现多轮对话需要将每一轮的对话信息添加到 messages 数组中，因此每轮对话的请求都会存在与前轮对话前缀相同的情况，有较高概率命中缓存。

<strong>第一轮对话的消息数组</strong>

```python
messages=[{"role": "system","content": "You are a helpful assistant."},
          {"role": "user","content": "你是谁？"}]
```
~~~~

来源#7：`qwen-multi-round.md`，chunk=2，version=e49ea4538d3b5fbdaa484720a935ad93，HTTP=200

~~~~text
向`messages` 数组添加用户问题。

```json
// 使用文本模型
[
    {"role": "user", "content": "推荐一部关于太空探索的科幻电影。"}
]

// 使用多模态模型，以 Qwen-VL 为例
// {"role": "user",
//       "content": [{"type": "image_url","image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20251031/ownrof/f26d201b1e3f4e62ab4a1fc82dd5c9bb.png"}},
//                   {"type": "text", "text": "请问图片展现了有哪些商品？"}]
// }
```

2. <strong>第二轮对话</strong>

   向`messages`数组添加大模型回复内容与用户的最新提问。

[同版本引用上下文]
# Qwen / 阿里云百炼：多轮对话

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[多轮对话](https://help.aliyun.com/zh/model-studio/multi-round-conversation)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 多轮对话

> 通义千问 API 是无状态的，不会保存对话历史。要实现多轮对话，需在每次请求中显式传入历史对话消息，并可结合截断、摘要、召回等策略，高效管理上下文，减少 Token 消耗。

<meta property="og:title" content="多轮对话" />

> 本文介绍如何通过 OpenAI 兼容的 Chat Completion 接口或 DashScope 接口实现多轮对话。 Responses API 可更便捷地实现多轮对话，参见：[OpenAI兼容-Responses](/zh/model-studio/compatibility-with-openai-responses-api)。

## 工作原理 <span id="5b03a2da4d9lz" />

实现多轮对话的核心是维护一个 `messages` 数组。每一轮对话都需要将用户的最新提问和模型的回复追加到此数组中，并将其作为下一次请求的输入。

以下示例为多轮对话时 `messages` 的状态变化：

1. <strong>第一轮对话</strong>

   向`messages` 数组添加用户问题。

```json
// 使用文本模型
[
    {"role": "user", "content": "推荐一部关于太空探索的科幻电影。"}
]

// 使用多模态模型，以 Qwen-VL 为例
// {"role": "user",
//       "content": [{"type": "image_url","image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20251031/ownrof/f26d201b1e3f4e62ab4a1fc82dd5c9bb.png"}},
//                   {"type": "text", "text": "请问图片展现了有哪些商品？"}]
// }
```

2. <strong>第二轮对话</strong>

   向`messages`数组添加大模型回复内容与用户的最新提问。

```json
// 使用文本模型
[
    {"role": "user", "content": "推荐一部关于太空探索的科幻电影。"},
    {"role": "assistant", "content": "我推荐《xxx》，这是一部经典的科幻作品。"},
    {"role": "user", "content": "这部电影的导演是谁？"}
]
~~~~

## N06 · qwen · insufficient

Qwen官方说明能否直接确认我的账号已经买了跨地域通用Key服务？

判分要求：通用文档不能确认个人购买状态；不能把地域独立Key说成已购买的跨地域通用Key

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**不能。** Qwen 官方文档只能说明通用规则，不能确认您个人账号的购买或开通状态。

根据文档规则：

1. **各地域的 API Key 相互独立、不能跨地域使用**，每个地域有独立的接入域名、API Key 和模型列表，不能跨地域混用。因此文档中并不存在“跨地域通用 Key”这一通用产品形态。[来源#1][来源#7]
2. Base URL 必须与同一计费方案的 API Key 配套使用，否则会报 401；API Key 和 Base URL 属于不同地域时也会触发鉴权错误。[来源#7][来源#3]
3. 文档明确说明：资料仅用于对应厂商规则检索，**本地业务工具不代表厂商生产账户核查**，核对日期也不等于规则生效日。[来源#1][来源#6]

也就是说，官方说明只能告诉您“规则上 Key 按地域隔离”，无法证明您账号下是否已购买某项服务。

**下一步建议：** 请登录阿里云百炼控制台，在对应地域的 API Key 页面查看您账号下实际存在的 Key 及其归属地域与业务空间；如需确认计费方案或订阅状态，可在控制台“我的订阅”等账户页面核对，或联系阿里云官方客服核查账户。

来源#1: qwen-api-key.md
来源#2: qwen-errors.md
来源#3: qwen-errors.md
来源#4: qwen-regions.md
来源#5: qwen-api-key.md
来源#6: qwen-regions.md
来源#7: qwen-base-url.md

### 实际引用锚点

来源#1：`qwen-api-key.md`，chunk=1，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

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

来源#2：`qwen-errors.md`，chunk=87，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

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

来源#4：`qwen-regions.md`，chunk=11，version=d3a82cffaca35834b0a443d899c1c294，HTTP=200

~~~~text
>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        不提供
      </td>
    </tr>
  </tbody>
</table>

## 各地域接入信息 <span id="h2_cc92e61c" />

每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>。

[同版本引用上下文]
<td style={{ verticalAlign: "top" }}>
        RPM、TPM 按模型区分，主账号维度合并计算
      </td>

      <td style={{ verticalAlign: "top" }}>
        RPM、TPM 按模型区分，主账号维度合并计算
      </td>

      <td style={{ verticalAlign: "top" }}>
        RPM 为1000（主账号维度），TPM 按模型区分
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>请求超时</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        3600 秒
      </td>

      <td style={{ verticalAlign: "top" }}>
        600 秒
      </td>

      <td style={{ verticalAlign: "top" }}>
        600 秒
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>协议支持</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE、<Link href="/zh/model-studio/realtime-websocket-overview">WebSocket</Link>、<Link href="/zh/model-studio/realtime-webrtc-access">WebRTC</Link>、<Link href="/zh/model-studio/realtime-aoq-access">AOQ</Link>（AI over QUIC）
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE、<Link href="/zh/model-studio/realtime-websocket-overview">WebSocket</Link>
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>SLA</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        不提供
      </td>
    </tr>
  </tbody>
</table>

## 各地域接入信息 <span id="h2_cc92e61c" />

每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>。
~~~~

来源#5：`qwen-api-key.md`，chunk=22，version=2abad0191e4d5697b5e7e7fd0dafdba8，HTTP=200

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

来源#6：`qwen-regions.md`，chunk=0，version=d3a82cffaca35834b0a443d899c1c294，HTTP=200

~~~~text
# Qwen / 阿里云百炼：地域说明

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[选择地域、服务部署范围和接入域名](https://help.aliyun.com/zh/model-studio/regions)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 选择地域、服务部署范围和接入域名

> 调用百炼前先选择 地域 、 服务部署范围、接入域名：

<meta property="og:title" content="选择地域、服务部署范围和接入域名" />

## 地域概述 <span id="h2-region-overview" />

地域决定<strong>接入点和数据存储位置</strong>，就近选择可降低延迟。

- 服务部署范围：决定<strong>推理执行位置</strong>，有数据合规需求选择特定地理边界的部署范围，无合规需求选择全球部署范围（推理资源池更大）；
- 接入域名：影响<strong>并发上限、超时等服务保障</strong>，各地域具有独立的接入域名。

一次完整的模型调用流程如下：

[同版本引用上下文]
# Qwen / 阿里云百炼：地域说明

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[选择地域、服务部署范围和接入域名](https://help.aliyun.com/zh/model-studio/regions)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 选择地域、服务部署范围和接入域名

> 调用百炼前先选择 地域 、 服务部署范围、接入域名：

<meta property="og:title" content="选择地域、服务部署范围和接入域名" />

## 地域概述 <span id="h2-region-overview" />

地域决定<strong>接入点和数据存储位置</strong>，就近选择可降低延迟。

- 服务部署范围：决定<strong>推理执行位置</strong>，有数据合规需求选择特定地理边界的部署范围，无合规需求选择全球部署范围（推理资源池更大）；
- 接入域名：影响<strong>并发上限、超时等服务保障</strong>，各地域具有独立的接入域名。

一次完整的模型调用流程如下：

1. 应用经接入域名将请求发送到所选<strong>地域</strong>，请求数据存于该地域；
2. 接入地域将请求转发至<strong>服务部署范围</strong>内的推理节点完成计算（传输全程加密）；
3. 推理结果回到接入地域存储，再响应给应用（用户静态数据始终存于所选地域）。

<img src="https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/9377607871/CAEQchiBgICkyp3I_hkiIGFjZmY5ZThjZWM2MzRkMmJhNTk5NWVmYTkwMWY3ZGI07466796_20260515102254.505.svg" alt="image" />

## 选择地域和服务部署范围 <span id="h2_recommend" />

不同地域支持不同的服务部署范围，百炼将在所选范围内进行推理调度。例如美国（弗吉尼亚）支持全球和美国，德国（法兰克福）支持全球和欧盟等。各地域支持的服务部署范围和接入方式，请参见[华北2（北京）](/zh/model-studio/beijing-access-information)、[新加坡](/zh/model-studio/singapore-regional-access-information)、[美国（弗吉尼亚）](/zh/model-studio/usa-virginia-global)、[德国（法兰克福）](/zh/model-studio/germany-frankfurt-global)、[日本（东京）](/zh/model-studio/japan-tokyo-global)、[中国香港](/zh/model-studio/hong-kong-china-global)。

## 选择接入域名 <span id="39f66b0187bsx" />

百炼为模型推理 API 提供业务空间专属、DashScope 和试用三种接入域名，适用于从试用体验到企业级生产的不同场景。推荐使用<strong>业务空间专属域名</strong>，各域名的核心差异如下：

<table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
  <colgroup>
    <col style={{ width: "12.49%" }} />

    <col style={{ width: "33.81%" }} />

    <col style={{ width: "28.86%" }} />

    <col style={{ width: "24.84%" }} />
  </colgroup>
~~~~

来源#7：`qwen-base-url.md`，chunk=0，version=72cb3bb8918b53828c09820e34321827，HTTP=200

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

## N07 · gpt · fact

OpenAI后台响应在ZDR项目中的存储规则是什么？能否仅因ZDR就保证后台请求完全不写磁盘？

判分要求：当前快照ZDR后台请求store=false；后台执行仍需临时磁盘缓存，不能宣称零写盘

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论：不能仅因 ZDR 就保证后台请求完全不写磁盘。**

**1. ZDR 项目中后台响应的存储规则**

- 来自 Zero Data Retention（ZDR）项目的后台请求会以 `store=false` 运行。
- 但响应数据仍会**临时写入磁盘约 10 分钟**，用于支持异步执行和轮询。
- 也就是说，ZDR 下后台模式并非“零磁盘写入”，而是“不长期持久化 + 短暂落盘”。

**2. 为什么不能仅凭 ZDR 保证“完全不写磁盘”**

- 上述临时落盘是后台模式异步执行与轮询机制的一部分，与 `store=false` 并存，因此 ZDR 本身不排除这种短暂磁盘存储。
- 另外，在启用 Modified Abuse Monitoring（含增强版）的项目中，前台请求在省略 `store` 或设为 `true` 时按标准保留策略处理；后台响应只有在显式设置 `store=true` 时才在轮询期后继续保留。这说明保留行为取决于 `store` 等具体配置，不能仅由 ZDR 身份推断。

**3. 补充说明（ZDR 下其他相关机制）**

- 对 ZDR 组织，OpenAI 会自动强制 `store: false`。
- 当请求包含 `encrypted_content` 时，它会在内存中解密、用于生成下一次响应，然后被安全丢弃；新的推理 token 会立即加密并返回，不持久化中间状态。
- 无状态模式（`store` 为 `false` 或组织使用 ZDR）下，响应 `output` 中的推理项默认带 `encrypted_content`，可回传给后续调用。

以上均为 OpenAI API 的通用文档规则，不代表任何具体账户的实际状态；如需核查某次实际请求的落盘/保留情况，请提供 request_id、接口地址、发生时间等信息。

来源#1: gpt-background.md
来源#2: gpt-responses-migration.md
来源#3: gpt-responses-migration.md
来源#4: gpt-file-search.md
来源#5: gpt-prompt-caching.md
来源#6: gpt-reasoning.md
来源#7: gpt-reasoning.md

### 实际引用锚点

来源#1：`gpt-background.md`，chunk=0，version=fc4bfe66d6345d5a99f63f24a73252ff，HTTP=200

~~~~text
# GPT / OpenAI API：后台执行

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Background mode](https://developers.openai.com/api/docs/guides/background)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Background mode

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：后台执行

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Background mode](https://developers.openai.com/api/docs/guides/background)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Background mode

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

Agents like [Codex](https://openai.com/index/introducing-codex/) and [Deep Research](https://openai.com/index/introducing-deep-research/) show that reasoning models can take several minutes to solve complex problems. Background mode enables you to execute long-running tasks on models like GPT-5.2 and GPT-5.2 Pro reliably, without having to worry about timeouts or other connectivity issues.

Background mode kicks off these tasks asynchronously, and developers can poll response objects to check status over time. To start response generation in the background, make an API request with `background` set to `true`:

Background requests from Zero Data Retention (ZDR) projects run with
  `store=false`. Response data is temporarily stored to disk for roughly 10
  minutes to enable asynchronous execution and polling.

For projects using [Modified Abuse
Monitoring](https://developers.openai.com/api/docs/guides/your-data#modified-abuse-monitoring), including
enhanced Modified Abuse Monitoring, foreground requests follow standard
retention when `store` is omitted or set to `true`. Background responses are
retained after the polling period only when `store=true` is explicitly provided.
If `store` is omitted or set to `false` for a background request, the response
is deleted after roughly 10 minutes.

Generate a response in the background
~~~~

来源#2：`gpt-responses-migration.md`，chunk=88，version=bbd8a4ad224250d4bdd8ced7d2638f8e，HTTP=200

~~~~text
The API will then return an encrypted version of the reasoning tokens, which you can pass back in future requests just like regular reasoning items.
For ZDR organizations, OpenAI enforces `store: false` automatically. When a request includes `encrypted_content`, it is decrypted in memory, used for generating the next response, and then securely discarded. Any new reasoning tokens are immediately encrypted and returned to you, ensuring no intermediate state is persisted.

### 5. Update function definitions and outputs

Chat Completions and Responses define functions differently in two ways:

[同版本引用上下文]
The API will then return an encrypted version of the reasoning tokens, which you can pass back in future requests just like regular reasoning items.
For ZDR organizations, OpenAI enforces `store: false` automatically. When a request includes `encrypted_content`, it is decrypted in memory, used for generating the next response, and then securely discarded. Any new reasoning tokens are immediately encrypted and returned to you, ensuring no intermediate state is persisted.

### 5. Update function definitions and outputs

Chat Completions and Responses define functions differently in two ways:

1. In Chat Completions, function definitions are externally tagged. In Responses, they are internally tagged.
2. In Chat Completions, functions are non-strict by default. In Responses, omitting `strict` attempts strict mode; if the schema cannot be made compatible, Responses falls back to non-strict, best-effort function calling and returns the resolved tool with `strict: false`. To keep non-strict behavior in Responses explicitly, set `strict: false`.

The Responses API function example on the right is functionally equivalent to the Chat Completions example on the left.

#### Chat Completions API

```json
{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Determine weather in my location",
      "strict": true,
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string"
          }
        },
        "additionalProperties": false,
        "required": [
          "location"
        ]
      }
    }
}
```

#### Responses API
~~~~

来源#3：`gpt-responses-migration.md`，chunk=86，version=bbd8a4ad224250d4bdd8ced7d2638f8e，HTTP=200

~~~~text
n the chain are billed as input tokens in the API.

<a id="4-decide-when-to-use-statefulness"></a>

### 4. Decide when to store state

Responses are stored by default. Chat Completions are stored by default for new accounts. To disable storage in either API, set `store: false`.

Some organizations, such as those with Zero Data Retention (ZDR) requirements, cannot use the Responses API in a stateful way due to compliance or data retention policies.

[同版本引用上下文]
Console.WriteLine(second.GetOutputText());
```

```ruby
require "openai"

client = OpenAI::Client.new

first = client.responses.create(
  model: "gpt-6-astra",
  input: "What is the capital of France?",
  store: true
)

second = client.responses.create(
  model: "gpt-6-astra",
  previous_response_id: first.id,
  input: "And its population?",
  store: true
)

puts(second.output_text)
```

Even when using `previous_response_id`, all previous input tokens for responses in the chain are billed as input tokens in the API.

<a id="4-decide-when-to-use-statefulness"></a>

### 4. Decide when to store state

Responses are stored by default. Chat Completions are stored by default for new accounts. To disable storage in either API, set `store: false`.

Some organizations, such as those with Zero Data Retention (ZDR) requirements, cannot use the Responses API in a stateful way due to compliance or data retention policies. To support these cases, OpenAI offers encrypted reasoning items, allowing you to keep your workflow stateless while still benefiting from reasoning items.

To stop storing state while still using reasoning:

- Set `store: false` in the [store field](https://developers.openai.com/api/reference/resources/responses/methods/create#responses_create-store).
- Preserve and replay every returned reasoning item. Each item includes `encrypted_content` by default when you create a response.
~~~~

来源#4：`gpt-file-search.md`，chunk=69，version=ebd88720c9f85961a198f85a9167a73e，HTTP=200

~~~~text
={{"maxWidth": "150px"}}>
[Pricing](https://developers.openai.com/api/docs/pricing#built-in-tools)

[ZDR and data residency](https://developers.openai.com/api/docs/guides/your-data)
</td>
</tr>

</tbody>
</table>

[同版本引用上下文]
| `.rb`       | `text/x-ruby`                                                               |
| `.sh`       | `application/x-sh`                                                          |
| `.tex`      | `text/x-tex`                                                                |
| `.ts`       | `application/typescript`                                                    |
| `.txt`      | `text/plain`                                                                |

## Usage notes

<table>
<tbody>

<tr>
  <th>API Availability</th>
  <th>Rate limits</th>
  <th>Notes</th>
</tr>

<tr>
<td>

    [Responses](https://developers.openai.com/api/reference/resources/responses)

    [Chat Completions](https://developers.openai.com/api/reference/resources/chat)

    [Assistants](https://developers.openai.com/api/reference/resources/beta/subresources/assistants)

</td>
<td style={{"maxWidth": "150px"}}>
**Build**

500 RPM

**Launch and Grow**

1000 RPM

</td>
<td style={{"maxWidth": "150px"}}>
[Pricing](https://developers.openai.com/api/docs/pricing#built-in-tools)

[ZDR and data residency](https://developers.openai.com/api/docs/guides/your-data)
</td>
</tr>

</tbody>
</table>
~~~~

来源#5：`gpt-prompt-caching.md`，chunk=0，version=a338ee9707c1548d9fc03fe54bf3257f，HTTP=200

~~~~text
# GPT / OpenAI API：提示缓存

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Prompt caching

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

## Why prompt caching matters

Prompt caching reuses work when requests share the same prompt prefix. This provides three main benefits:

[同版本引用上下文]
# GPT / OpenAI API：提示缓存

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Prompt caching

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

## Why prompt caching matters

Prompt caching reuses work when requests share the same prompt prefix. This provides three main benefits:

- **Compute-efficient:** Avoid recalculating a prompt prefix that the model has already processed.
- **Cheaper input tokens:** Pay the model's reduced cached-input rate for reused tokens, discounted up to 95%.
- **Faster:** Reduce the time spent processing input before the response starts.

Prompt caching is enabled by default for supported OpenAI models. Use the [Prompt Caching Dashboard](https://platform.openai.com/usage?usage_section=prompt-caching) to monitor cache read hit rates and use the [Prompt Cache Diagnostics tool](https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics) to diagnose cache misses and improve cache reuse.

Agents API model calls use the same prompt-caching behavior as the Responses API. Reusing context within a session can preserve a shared prompt prefix, but maintaining a session doesn't guarantee a cache hit. See [Observability and usage](https://developers.openai.com/api/docs/guides/agents-api/observability) for session usage fields and subagent accounting.
~~~~

来源#6：`gpt-reasoning.md`，chunk=70，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
the rendered context for long-running workflows.

### Preserve reasoning without stored responses

When you create a response in stateless mode, reasoning items in the response's `output` array include an `encrypted_content` property by default. Stateless mode applies when `store` is `false` or when your organization uses Zero Data Retention (ZDR). The API still accepts the legacy `reasoning.encrypted_content` value in `include` for compatibility, but doesn't require it.

The following request returns encrypted reasoning content without specifying `include`:

[同版本引用上下文]
Use `current_turn` when replaying older response items that the model no longer needs. Those reasoning items can remain in the API payload for continuity, but the service does not render them into the new sample. This can reduce the rendered context for long-running workflows.

### Preserve reasoning without stored responses

When you create a response in stateless mode, reasoning items in the response's `output` array include an `encrypted_content` property by default. Stateless mode applies when `store` is `false` or when your organization uses Zero Data Retention (ZDR). The API still accepts the legacy `reasoning.encrypted_content` value in `include` for compatibility, but doesn't require it.

The following request returns encrypted reasoning content without specifying `include`:

```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-6-astra",
    "store": false,
    "reasoning": {"effort": "medium"},
    "input": "What is the weather like today?",
    "tools": [ ... function config here ... ]
  }'
```

Reasoning items in the `output` array will include an `encrypted_content` property containing encrypted reasoning tokens that you can pass to future calls.

To use `all_turns` with `store: false`, preserve every output item, append the next user message, and replay the complete history:

Preserve reasoning without storing responses

```javascript
import OpenAI from "openai";
import { toResponseInputItems } from "openai/lib/responses/ResponseInputItems";

const client = new OpenAI();

const history = [
  {
    role: "user",
    content: "Inspect this repository and identify the likely bug.",
  },
];
~~~~

来源#7：`gpt-reasoning.md`，chunk=99，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
store=True,
)
print(response.output_text)
```

```go
package main

import (
	"context"
	"fmt"

	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
)

func main() {
	client := openai.NewClient()
	ctx := context.Background()
	first, err := client.Responses.New(ctx, responses.ResponseNewParams{
		Store:     openai.Bool(true),
		Model:     "gpt-6-astra",
		Reasoning: shared.ReasoningParam{Effort: shared.ReasoningEffortLow},

[同版本引用上下文]
response = client.responses.create(
    model=model,
    previous_response_id=response.id,
    reasoning={"effort": "low"},
    input=[
        {
            "type": "configuration_update",
            "reasoning": {"effort": "high"},
        },
        {
            "role": "user",
            "content": "Analyze the failure modes and propose rollback steps.",
        },
    ],
    store=True,
)
print(response.output_text)
```

```go
package main

import (
	"context"
	"fmt"

	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
)

func main() {
	client := openai.NewClient()
	ctx := context.Background()
	first, err := client.Responses.New(ctx, responses.ResponseNewParams{
		Store:     openai.Bool(true),
		Model:     "gpt-6-astra",
		Reasoning: shared.ReasoningParam{Effort: shared.ReasoningEffortLow},
		Input:     responses.ResponseNewParamsInputUnion{OfString: openai.String("Draft a database migration plan.")},
	})
	if err != nil {
		panic(err)
	}
	fmt.Println(first.OutputText())
	response, err := client.Responses.New(ctx, responses.ResponseNewParams{
		Model:              "gpt-6-astra",
		PreviousResponseID: openai.String(first.ID),
		// Keep the original request-level setting; the item updates the conversation.
		Reasoning: shared.ReasoningParam{Effort: shared.ReasoningEffortLow},
		Input: responses.ResponseNewParamsInputUnion{OfInputItemList: responses.ResponseInputParam{
			{OfConfigurationUpdate: &responses.ResponseConfigurationUpdateItemParam{
				Reasoning: responses.ResponseConfigurationUpdateItemParamReasoning{Effort: shared.ReasoningEffortHigh},
			}},
			responses.ResponseInputItemParamOfMessage("Analyze the failure modes and propose rollback steps.", responses.EasyInputMessageRoleUser),
		}},
~~~~

## N08 · gpt · fact

OpenAI Responses的previous_response_id有什么作用？它与每次手工重传完整历史有什么区别？

判分要求：用previous_response_id串联前次响应上下文；可避免客户端每次手工传完整历史；不能说因此历史token不计费

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

以下仅基于已检索到的 OpenAI 文档说明通用规则，不代表你账户的实际状态。

## 1. `previous_response_id` 的作用

- **由 OpenAI 管理前序响应上下文**：当你希望由 OpenAI 管理之前响应的上下文时，使用 `previous_response_id`。这是 Responses API 三种常见状态管理方式之一（另两种是手工回传 prior `output` Items、使用 Conversations API）。来源#1
- **延续推理上下文**：`reasoning.context` 设为 `all_turns` 时，只有在请求能访问更早的响应项时才生效——可通过 `previous_response_id`、把响应挂到 conversation，或手工重放完整响应历史来实现。来源#3
- **函数调用场景**：可把上一响应的 reasoning items 通过 `previous_response_id` 传入，或手工把上一响应的全部 `output` items 放进新请求的 `input`。来源#6
- **WebSocket 模式**：延续使用与 HTTP 模式相同的 `previous_response_id` 语义。来源#2、来源#5

## 2. 与“每次手工重传完整历史”的区别

| 维度 | `previous_response_id` | 手工重传完整历史 |
|---|---|---|
| 上下文管理方 | OpenAI 管理前序响应上下文 来源#1 | 你自己管理或裁剪上下文 来源#1 |
| `instructions` | **不会**沿用上一响应的顶层 `instructions`，每次请求需重新发送稳定的 `instructions` 来源#1 | 由你在请求中自行携带 |
| 计费 | 即使使用 `previous_response_id`，链中所有先前输入 token 仍按输入 token 计费 来源#4 | 同样按你发送的输入 token 计费 |
| 缓存/解析失败 | 若未缓存的 ID 无法解析，应把 `previous_response_id` 设为 `null` 并传入完整输入上下文 来源#4 | 不涉及 ID 解析问题 |
| 推理复用 | 可复用持久化推理，但仅限同一模型家族；切换模型家族时 API 会省略不兼容的推理 来源#3 | 手工重放完整响应历史同样可让 `all_turns` 生效 来源#3 |

补充：Response 对象默认保存 30 天，可通过 `store: false` 关闭；Conversation 对象及其中的 items 不受 30 天 TTL 限制。来源#4

## 3. 选择建议（文档给出的定位）

- 想要最短的状态化集成、由 OpenAI 管理上下文 → 用 `previous_response_id`。来源#1、来源#3
- 需要自行管理或裁剪上下文 → 把先前的 `output` Items 回传到下一次请求。来源#1
- 需要持久化会话对象 → 使用 Conversations API。来源#1

以上为 OpenAI Responses API 的通用文档规则；不涉及你账户的具体配置或实际调用情况。

来源#1: gpt-responses-migration.md
来源#2: gpt-conversation-state.md
来源#3: gpt-reasoning.md
来源#4: gpt-conversation-state.md
来源#5: gpt-streaming.md
来源#6: gpt-reasoning.md

### 实际引用锚点

来源#1：`gpt-responses-migration.md`，chunk=54，version=bbd8a4ad224250d4bdd8ced7d2638f8e，HTTP=200

~~~~text
application, update your context logic. Responses gives you three common state-management options:

- Use `previous_response_id` when you want OpenAI to manage prior response context. Resend stable `instructions` on each request, because `previous_response_id` does not carry over the previous response's top-level `instructions`.
- Pass prior `output` Items back into the next request when you need to manage or trim context yourself.

[同版本引用上下文]
When you only need the final text, use the SDK `output_text` helper. When your flow uses reasoning, tools, or multimodal output, iterate over `response.output` and handle each Item by its `type`.

### 3. Update multi-turn conversations

If you have multi-turn conversations in your application, update your context logic. Responses gives you three common state-management options:

- Use `previous_response_id` when you want OpenAI to manage prior response context. Resend stable `instructions` on each request, because `previous_response_id` does not carry over the previous response's top-level `instructions`.
- Pass prior `output` Items back into the next request when you need to manage or trim context yourself.
- Use the [Conversations API](https://developers.openai.com/api/docs/guides/conversation-state?api-mode=responses#using-the-conversations-api) when you need a persistent conversation object.

Chat Completions

    In Chat Completions, you store the transcript and send the accumulated
    `messages` array on each request.
    Multi-turn conversation

```javascript
let messages = [
  { role: "system", content: "You are a helpful assistant." },
  { role: "user", content: "What is the capital of France?" },
];
const res1 = await client.chat.completions.create({
  model: "gpt-6-astra",
  messages,
});

messages = messages.concat([res1.choices[0].message]);
messages.push({ role: "user", content: "And its population?" });

const res2 = await client.chat.completions.create({
  model: "gpt-6-astra",
  messages,
});
```

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
]
res1 = client.chat.completions.create(model="gpt-6-astra", messages=messages)
~~~~

来源#2：`gpt-conversation-state.md`，chunk=47，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
why this is funny."
)
puts(second.output_text)
```

#### `previous_response_id` in WebSocket mode

If you are using [the Responses API WebSocket mode](https://developers.openai.com/api/docs/guides/websocket-mode), continuation uses the same `previous_response_id` semantics as HTTP mode, but over a persistent socket with repeated `response.create` events.

[同版本引用上下文]
var second =
    client
        .responses()
        .create(
            ResponseCreateParams.builder()
                .model("gpt-6-astra")
                .input("Explain why this is funny.")
                .previousResponseId(first.id())
                .build());
second.output().stream()
    .flatMap(item -> item.message().stream())
    .flatMap(message -> message.content().stream())
    .flatMap(content -> content.outputText().stream())
    .forEach(text -> System.out.println(text.text()));
```

```csharp
using OpenAI.Responses;
#pragma warning disable OPENAI001

string key = Environment.GetEnvironmentVariable("OPENAI_API_KEY")!;
ResponsesClient client = new(key);

ResponseResult first = await client.CreateResponseAsync(
    "gpt-6-astra",
    "Tell me a joke."
);
Console.WriteLine(first.GetOutputText());

ResponseResult second = await client.CreateResponseAsync(
    "gpt-6-astra",
    "Explain why this is funny.",
    previousResponseId: first.Id
);
Console.WriteLine(second.GetOutputText());
```

```ruby
require "openai"

client = OpenAI::Client.new

first = client.responses.create(
  model: "gpt-6-astra",
  input: "Tell me a joke."
)
puts(first.output_text)

second = client.responses.create(
  model: "gpt-6-astra",
  previous_response_id: first.id,
  input: "Explain why this is funny."
)
puts(second.output_text)
```

#### `previous_response_id` in WebSocket mode

If you are using [the Responses API WebSocket mode](https://developers.openai.com/api/docs/guides/websocket-mode), continuation uses the same `previous_response_id` semantics as HTTP mode, but over a persistent socket with repeated `response.create` events.
~~~~

来源#3：`gpt-reasoning.md`，chunk=59，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
reasoning with stored responses

Use `previous_response_id` for the shortest stateful integration:

Preserve reasoning with a previous response

```javascript
import OpenAI from "openai";

const client = new OpenAI();

const first = await client.responses.create({
  model: "gpt-6.1-sol",
  input: "Inspect this repository and identify the likely bug.",
  reasoning: { context: "current_turn" },
});

[同版本引用上下文]
The response's `reasoning.context` field contains the effective mode, either `current_turn` or `all_turns`. Check this field on each response to confirm which mode the model used. The setting does not create reasoning items that are not already available.

`all_turns` has an effect only when the request has access to earlier response items. Use `previous_response_id`, attach the response to a conversation, or manually replay the complete response history. On the first request, `current_turn` and `all_turns` behave the same because no earlier reasoning exists.

Persisted reasoning can be reused only within the same model family. For example, `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna` can reuse each other's reasoning, but reasoning does not carry between the GPT-5.6 and GPT-5.5 families.

When you switch model families, the API omits incompatible reasoning from the model's context, even when `reasoning.context` is `all_turns`.

### Continue reasoning with stored responses

Use `previous_response_id` for the shortest stateful integration:

Preserve reasoning with a previous response

```javascript
import OpenAI from "openai";

const client = new OpenAI();

const first = await client.responses.create({
  model: "gpt-6.1-sol",
  input: "Inspect this repository and identify the likely bug.",
  reasoning: { context: "current_turn" },
});

const second = await client.responses.create({
  model: "gpt-6.1-sol",
  previous_response_id: first.id,
  input: "Now patch the bug and explain the change.",
  reasoning: { context: "all_turns" },
});

console.log(second.output_text);
```

```python
from openai import OpenAI

client = OpenAI()
model = "gpt-6.1-sol"
~~~~

来源#4：`gpt-conversation-state.md`，chunk=48，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
The connection-local cache keeps recent previous responses in memory for low-latency continuation. When you use `stream_id`, each lane can retain its latest response; `previous_response_id` still controls lineage, so a new lane can fork from a response on another lane while that response remains available. If an uncached ID cannot be resolved, send a new turn with `previous_response_id` set to `null` and pass full input context.

##### Data retention for model responses

[同版本引用上下文]
The connection-local cache keeps recent previous responses in memory for low-latency continuation. When you use `stream_id`, each lane can retain its latest response; `previous_response_id` still controls lineage, so a new lane can fork from a response on another lane while that response remains available. If an uncached ID cannot be resolved, send a new turn with `previous_response_id` set to `null` and pass full input context.

##### Data retention for model responses

      Response objects are saved for 30 days by default. They can be viewed in the dashboard
      [logs](https://platform.openai.com/logs?api=responses) page or
      [retrieved](https://developers.openai.com/api/reference/resources/responses/methods/retrieve) via the API.
      You can disable this behavior by setting `store` to `false`
      when creating a Response.

      Conversation objects and items in them are not subject to the 30 day TTL. Any response attached to a conversation will have its items persisted with no 30 day TTL.

      OpenAI does not use data sent via API to train our models without your explicit consent—[learn more](https://developers.openai.com/api/docs/guides/your-data).

Even when using `previous_response_id`, all previous input tokens for responses in the chain are billed as input tokens in the API.

## Managing the context window

Understanding context windows will help you successfully create threaded conversations and manage state across model interactions.

The **context window** is the maximum number of tokens that can be used in a single request. This max tokens number includes input, output, and reasoning tokens. To learn your model's context window, see [model details](https://developers.openai.com/api/docs/models).

### Managing context for text generation
~~~~

来源#5：`gpt-streaming.md`，chunk=2，version=d5bac8319713536e98156754cdcd9bba，HTTP=200

~~~~text
or processing the beginning of the model's output while it continues generating the full response.

This guide focuses on HTTP streaming (`stream=true`) over server-sent events (SSE). For persistent WebSocket transport with incremental inputs via `previous_response_id`, see [the Responses API WebSocket mode](https://developers.openai.com/api/docs/guides/websocket-mode).

## Enable streaming

To start streaming responses, set `stream=True` in your request to the Responses endpoint:

```javascript
import { OpenAI } from "openai";
const client = new OpenAI();

[同版本引用上下文]
# GPT / OpenAI API：流式响应

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Streaming API responses

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

By default, when you make a request to the OpenAI API, we generate the model's entire output before sending it back in a single HTTP response. When generating long outputs, waiting for a response can take time. Streaming responses lets you start printing or processing the beginning of the model's output while it continues generating the full response.

This guide focuses on HTTP streaming (`stream=true`) over server-sent events (SSE). For persistent WebSocket transport with incremental inputs via `previous_response_id`, see [the Responses API WebSocket mode](https://developers.openai.com/api/docs/guides/websocket-mode).

## Enable streaming

To start streaming responses, set `stream=True` in your request to the Responses endpoint:

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
~~~~

来源#6：`gpt-reasoning.md`，chunk=90，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
g items that aren't relevant to your functions, and only retain those in context that are relevant. You can pass reasoning items from previous responses either using the `previous_response_id` parameter, or by manually passing in all the [output](https://developers.openai.com/api/reference/resources/responses#responses/object-output) items from a past response into the [input](https://developers.openai.com/api/reference/resources/responses/methods/create#responses-create-input) of a new one.

[同版本引用上下文]
When doing [function calling](https://developers.openai.com/api/docs/guides/function-calling) with a reasoning model in the [Responses API](https://developers.openai.com/api/reference/resources/responses), we highly recommend you pass back any reasoning items returned with the last function call (in addition to the output of your function). If the model calls multiple functions consecutively, you should pass back all reasoning items, function call items, and function call output items, since the last `user` message. This allows the model to continue its reasoning process to produce better results in the most token-efficient manner.

The simplest way to do this is to pass in all reasoning items from a previous response into the next one. Our systems will smartly ignore any reasoning items that aren't relevant to your functions, and only retain those in context that are relevant. You can pass reasoning items from previous responses either using the `previous_response_id` parameter, or by manually passing in all the [output](https://developers.openai.com/api/reference/resources/responses#responses/object-output) items from a past response into the [input](https://developers.openai.com/api/reference/resources/responses/methods/create#responses-create-input) of a new one.

For advanced use cases where you might be truncating and optimizing parts of the context window before passing them on to the next response, just ensure all items between the last user message and your function call output are passed into the next response untouched. This will ensure that the model has all the context it needs.

Check out [this guide](https://developers.openai.com/api/docs/guides/conversation-state) to learn more about manual context management.

## Change reasoning mid-conversation
~~~~

## N09 · gpt · insufficient

请确认GPT gpt-demo-private-2099模型在我的组织里已经开放，并给出它的准确上下文长度。

判分要求：未知型号和组织权限没有可核验证据；不猜上下文长度或宣称已开通

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

关于您提出的两个问题，我需要分别说明：

**1. 关于“gpt-demo-private-2099 模型在您的组织中已开放”**

这一点无法确认。现有证据中没有您组织的模型开通记录或账户状态数据，检索到的文档均为 OpenAI API 的通用说明，不能证明某个具体模型在您组织内是否已开放。因此我不能确认该模型已对您的组织开放。

**2. 关于该模型的“准确上下文长度”**

同样无法给出。现有文档只说明了上下文窗口的通用概念（即输入与输出 token 合计的上限），并举例说明 `gpt-4o-2024-08-06` 的上下文窗口为 128k tokens；文档中并未出现 `gpt-demo-private-2099` 这一模型，也没有其参数。因此不能提供该模型的准确上下文长度。

**下一步建议**

- 若需核实组织内模型开通情况，请在 OpenAI 平台的组织/项目设置中查看可用模型列表，或联系您的 OpenAI 账户管理员。
- 若需该模型的准确上下文长度，请以 OpenAI 官方模型页面（developers.openai.com/api/docs/models）中该模型条目为准；如该模型未在公开页面列出，则需向 OpenAI 支持渠道确认。

来源#1: gpt-text.md
来源#2: gpt-overview.md
来源#3: gpt-reasoning.md
来源#4: gpt-reasoning-practices.md
来源#5: gpt-prompt-caching.md
来源#6: gpt-conversation-state.md
来源#7: gpt-reasoning.md

### 实际引用锚点

来源#1：`gpt-text.md`，chunk=0，version=2f96fd65e2fb5f66ab164fb97fc9c821，HTTP=200

~~~~text
# GPT / OpenAI API：文本生成

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Text generation](https://developers.openai.com/api/docs/guides/text)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Text generation

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：文本生成

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Text generation](https://developers.openai.com/api/docs/guides/text)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Text generation

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

With the OpenAI API, you can use a [large language model](https://developers.openai.com/api/docs/models) to generate text from a prompt, as you might using [ChatGPT](https://chatgpt.com). Models can generate almost any kind of text response—like code, mathematical equations, structured JSON data, or human-like prose.

Use the [Responses API](https://developers.openai.com/api/reference/resources/responses) for direct model requests like this text-generation call.

Generate text from a simple prompt

```javascript
import OpenAI from "openai";
const client = new OpenAI();

const response = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a one-sentence bedtime story about a unicorn.",
});

console.log(response.output_text);
```

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-6-astra",
    input="Write a one-sentence bedtime story about a unicorn.",
)

print(response.output_text)
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

	resp, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: "gpt-6-astra",
		Input: responses.ResponseNewParamsInputUnion{OfString: openai.String("Say this is a test")},
	})
	if err != nil {
		panic(err.Error())
	}
~~~~

来源#2：`gpt-overview.md`，chunk=0，version=9feabad921a156d9a4741c5a7765bf77，HTTP=200

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

来源#3：`gpt-reasoning.md`，chunk=0，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
# GPT / OpenAI API：推理模型

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Reasoning models

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

[同版本引用上下文]
# GPT / OpenAI API：推理模型

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Reasoning models

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

**Reasoning models** use internal reasoning tokens before producing a response. This helps the model plan, use tools effectively, inspect alternatives, recover from ambiguity, and solve harder multi-step tasks. Reasoning models work especially well for complex problem solving, coding, scientific reasoning, and multi-step agentic workflows. They're also the best models for [Codex CLI](https://github.com/openai/codex), our lightweight coding agent.

Start with `gpt-6-astra` for most reasoning workloads. For lower cost, consider [`gpt-5.6-terra`](https://developers.openai.com/api/docs/models/gpt-5.6-terra), or [`gpt-5.6-luna`](https://developers.openai.com/api/docs/models/gpt-5.6-luna) for the lowest cost and latency. If you're using a GPT-5.6 or GPT-6 model, see [reasoning mode](#reasoning-mode) for its `pro` option.

**Reasoning models work better with the [Responses
  API](https://developers.openai.com/api/docs/guides/migrate-to-responses)**. While the Chat Completions API
  is still supported, you'll get improved model intelligence and performance by
  using Responses.

## Get started with reasoning

Call the [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) and specify your reasoning model and reasoning effort:

Using a reasoning model in the Responses API

```javascript
import OpenAI from "openai";
~~~~

来源#4：`gpt-reasoning-practices.md`，chunk=1，version=1faef98895c85ecca86307f8a91f49d4，HTTP=200

~~~~text
s.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI offers two types of models: [reasoning models](https://developers.openai.com/api/docs/models#o4-mini) (o3 and o4-mini, for example) and [GPT models](https://developers.openai.com/api/docs/models#gpt-4.1) (like GPT-4.1). These model families behave differently.

This guide covers:

1. The difference between our reasoning and non-reasoning GPT models
1. When to use our reasoning models
1. How to prompt reasoning models effectively

[同版本引用上下文]
# GPT / OpenAI API：推理最佳实践

厂商：OpenAI；产品范围：OpenAI API；核对日期：2026-10-19。
官方来源：[Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# Reasoning best practices

> For the complete documentation index, see [llms.txt](/llms.txt). Markdown versions of documentation pages are available by appending `.md` to the page URL.

OpenAI offers two types of models: [reasoning models](https://developers.openai.com/api/docs/models#o4-mini) (o3 and o4-mini, for example) and [GPT models](https://developers.openai.com/api/docs/models#gpt-4.1) (like GPT-4.1). These model families behave differently.

This guide covers:

1. The difference between our reasoning and non-reasoning GPT models
1. When to use our reasoning models
1. How to prompt reasoning models effectively

Read more about [reasoning models](https://developers.openai.com/api/docs/guides/reasoning) and how they work.

## Reasoning models vs. GPT models

Compared to GPT models, our o-series models excel at different tasks and require different prompts. One model family isn't better than the other—they're just different.

We trained our o-series models (“the planners”) to think longer and harder about complex tasks, making them effective at strategizing, planning solutions to complex problems, and making decisions based on large volumes of ambiguous information. These models can also execute tasks with high accuracy and precision, making them ideal for domains that would otherwise require a human expert—like math, science, engineering, financial services, and legal services.
~~~~

来源#5：`gpt-prompt-caching.md`，chunk=49，version=a338ee9707c1548d9fc03fe54bf3257f，HTTP=200

~~~~text
pt-5.1-codex`, `gpt-5.1-codex-mini`, `gpt-5.1-chat-latest`, `gpt-5`, `gpt-5-codex`, and `gpt-4.1`.

For models before GPT-5.6, the minimum cacheable input length varies with request settings, including tools, images, output schemas, reasoning effort, and verbosity.

Ask ChatGPT to find the cache minimum for my request

<a id="best-practices"></a>

## How to optimize prompt caching

[同版本引用上下文]
| Cache read charge          | 0.1× uncached input (0.05× for GPT-6.1 Sol)         | Model-dependent cached-input rate                           | Model-dependent cached-input rate                                               |
| Cache write charge         | 1.25× the uncached input-token rate                 | No additional cache-write charge                            | No additional cache-write charge                                                |
| Cache lifetime control     | `prompt_cache_options.ttl`                          | `prompt_cache_retention`                                    | `prompt_cache_retention`                                                        |
| Supported retention values | `"30m"`                                             | `"24h"` only                                                | `"in_memory"` or `"24h"`<sup>[\*](#extended-retention-models)</sup>             |
| Cache lifetime             | At least 30 minutes after the latest write or reuse | Typically around 30 minutes, up to 24 hours                 | Typically 5 to 10 minutes inactive for `in_memory`, or up to 24 hours for `24h` |

<a id="extended-retention-models"></a>

\* Extended retention is supported by `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.2`, `gpt-5.1-codex-max`, `gpt-5.1`, `gpt-5.1-codex`, `gpt-5.1-codex-mini`, `gpt-5.1-chat-latest`, `gpt-5`, `gpt-5-codex`, and `gpt-4.1`.

For models before GPT-5.6, the minimum cacheable input length varies with request settings, including tools, images, output schemas, reasoning effort, and verbosity.

Ask ChatGPT to find the cache minimum for my request

<a id="best-practices"></a>

## How to optimize prompt caching
~~~~

来源#6：`gpt-conversation-state.md`，chunk=54，version=7878189d34085e729b330cec723e6c26，HTTP=200

~~~~text
/api/docs/models). For example, `gpt-4o-2024-08-06` can generate a maximum of 16,384 output tokens.
- A **context window** describes the total tokens that can be used for both input and output tokens (and for some models, [reasoning tokens](https://developers.openai.com/api/docs/guides/reasoning)). Compare the [context window limits](https://developers.openai.com/api/docs/models) of our models. For example, `gpt-4o-2024-08-06` has a total context window of 128k tokens.

[同版本引用上下文]
As your inputs become more complex, or you include more turns in a conversation, you'll need to consider both **output token** and **context window** limits. Model inputs and outputs are metered in [**tokens**](https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them), which are parsed from inputs to analyze their content and intent and assembled to render logical outputs. Models have limits on token usage during the lifecycle of a text generation request.

- **Output tokens** are the tokens generated by a model in response to a prompt. Each model has different [limits for output tokens](https://developers.openai.com/api/docs/models). For example, `gpt-4o-2024-08-06` can generate a maximum of 16,384 output tokens.
- A **context window** describes the total tokens that can be used for both input and output tokens (and for some models, [reasoning tokens](https://developers.openai.com/api/docs/guides/reasoning)). Compare the [context window limits](https://developers.openai.com/api/docs/models) of our models. For example, `gpt-4o-2024-08-06` has a total context window of 128k tokens.

If you create a large prompt—often by including extra context, data, or examples for the model—you run the risk of exceeding the allocated context window for a model, which might result in truncated outputs.

Use the [tokenizer tool](https://platform.openai.com/tokenizer), built with the [tiktoken library](https://github.com/openai/tiktoken), to see how many tokens are in a particular string of text.
~~~~

来源#7：`gpt-reasoning.md`，chunk=15，version=4979af064cb15eb6bb6d1f7dc3a09fcb，HTTP=200

~~~~text
oss reasoning efforts, using fewer tokens for simpler tasks and thinking harder for complex tasks.

[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) does not support `none` reasoning
  effort. Setting `reasoning.effort` (Responses) or `reasoning_effort` (Chat
  Completions) to `none` returns HTTP 400. [GPT-6.1 Sol](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#gpt-61-sol)
  does not support `none` or `minimal` and defaults to `medium`.

[同版本引用上下文]
```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-6-astra",
    "reasoning": {"effort": "low"},
    "input": [
      {
        "role": "user",
        "content": "Write a bash script that takes a matrix represented as a string with format \"[1,2],[3,4],[5,6]\" and prints the transpose in the same format."
      }
    ]
  }'
```

## Reasoning effort

The `reasoning.effort` parameter guides the model on how much to think when performing a task.

Supported values are model-dependent and can include `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. Lower effort favors speed and lower token usage, while at higher effort the model thinks more completely to provide higher quality responses. The models also reason adaptively across reasoning efforts, using fewer tokens for simpler tasks and thinking harder for complex tasks.

[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) does not support `none` reasoning
  effort. Setting `reasoning.effort` (Responses) or `reasoning_effort` (Chat
  Completions) to `none` returns HTTP 400. [GPT-6.1 Sol](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#gpt-61-sol)
  does not support `none` or `minimal` and defaults to `medium`.

Use the [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) for function
calling. Chat Completions does not support function calling with GPT-6 Astra or
GPT-6.1 Sol.

Defaults are also model-dependent rather than universal. `gpt-5.5` defaults to `medium` reasoning effort. This is the best starting point for `gpt-5.5`’s full balance of quality, reliability and performance.
~~~~

## N10 · ambiguous · clarification

启用strict后枚举字段就一定正确吗？请给我的API配置参数。

判分要求：需确认厂商模型接口或逐家区分适用范围；不能保证所有API通用strict参数

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

## 关于“启用 strict 后枚举字段是否一定正确”

不能据此保证“一定正确”。现有文档只说明 strict 模式对 JSON Schema 的支持范围，并未承诺枚举字段在所有情况下都必然正确：

- strict 模式对 JSON Schema 关键字有支持范围，部分关键字（如 `minLength`、`maxLength`、`minItems`、`maxItems`）**不支持**，提交后会返回 400 错误；`enum`、`anyOf` 属于被列出的关键字之一。因此能否使用枚举，取决于所选厂商和模型对 Schema 关键字的支持情况，不能当作通用保证。[来源#5]
- 在 object 类型下，strict 要求所有属性都设为 `required`，且 `additionalProperties` 必须为 `false`；`additionalProperties` 为 `true` 时允许额外字段，为 `false` 时只输出定义的字段。这说明 strict 约束的是结构，并不等于“枚举值必然正确”的承诺。[来源#3][来源#5]
- 错误码文档中“style 不在枚举范围内”“style_level 不在枚举范围内”等条目，只解释通用报错含义，不能证明你本次请求发生过该错误。[来源#1]

## 关于“API 配置参数”

你未说明使用的厂商、模型和接口，而不同厂商参数并不通用，因此无法给出可直接套用的完整配置。可确认的厂商特定信息如下：

- **DeepSeek（chat completions）**：`strict` 为 boolean，默认 `false`；设为 `true` 时，API 会在函数调用中使用 strict 模式。该参数属于 `tools[].function` 下的字段。[来源#2]
- **DeepSeek 工具调用 Schema**：object 的所有属性需设为 `required`，且 `additionalProperties` 必须为 `false`；string 支持 `pattern`、`format`（email/hostname/ipv4/ipv6/uuid），不支持 `minLength`/`maxLength`；number/integer 支持 `const`、`default`、`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`；array 不支持 `minItems`/`maxItems`。[来源#5]
- **DeepSeek 思考模式**：携带 `tools` 的请求，后续所有请求必须完整回传 `reasoning_content`，否则返回 400。[来源#4]
- **千问（Qwen）结构化输出**：文档列出 strict 模式支持的 JSON Schema 关键字，不支持的关键字提交后返回 400。[来源#3]

请补充以下信息，我才能给出对应厂商的准确参数：厂商与模型名称、接口地址（如 chat/completions 或结构化输出接口）、是否使用工具调用。若你是在排查某次实际故障，请同时提供 request_id、HTTP 状态/错误码或发生时间。

来源#1: qwen-errors.md
来源#2: deepseek-chat-completions.md
来源#3: qwen-structured-outputs.md
来源#4: deepseek-thinking.md
来源#5: deepseek-tool-calling.md
来源#6: qwen-errors.md
来源#7: qwen-errors.md

### 实际引用锚点

来源#1：`qwen-errors.md`，chunk=59，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
数格式问题等。

### The style is invalid. <span id="a92e9d7b84avs" />

<strong>原因：</strong> style不在枚举范围内。

<strong>解决方案：</strong> 请检查`style`参数的取值是否正确。

### The style\_level is invalid. <span id="39a57aedebi9f" />

<strong>原因：</strong> style\_level不在枚举范围内。

<strong>解决方案：</strong> 详情参见[EMO 视频生成](/zh/model-studio/emo-api)。

### parameters.video\_ratio must be 9:16 or 3:4. <span id="d147c86a163yl" />

<strong>原因：</strong> video\_ratio 入参只能为 9:16 或 3:4。

<strong>解决方案：</strong> 请修改`video_ratio`参数为 "9:16" 或 "3:4"。

### the xxx parm is invalid! <span id="f78e96731aa4l" />

<strong>原因：</strong> 输入参数超出范围。

[同版本引用上下文]
<strong>解决方案：</strong> 请并使用正确的`content`参数。

### Invalid video file. <span id="43da9d83ef2dz" />

<strong>原因：</strong> 传入的视频文件无效。

<strong>解决方案：</strong> 请检查视频文件是否损坏或格式是否正确。

### The video modality input does not meet the requirements because: The video file is too long. <span id="4789f1ff21nlu" />

<strong>原因：</strong> 传入千问VL模型或者Qwen-Omni 模型的视频时长超过限制。

<strong>解决方案：</strong>

- Qwen2.5-VL模型支持的视频时长应在2秒至10分钟之间。
- 其他千问VL或 Qwen-Omni-Turbo 模型支持的视频时长应在2秒至40秒之间。

其他 Qwen-Omni 型号的视频限制见[单一模态输入](/zh/model-studio/qwen-omni#h2-single-modal-input)。

### Field required: xxx <span id="936d0ca16e2wm" />

<strong>原因：</strong> 缺少入参。

<strong>解决方案：</strong> 请根据错误提示`xxx`补充对应的参数。

### The request is missing required parameters or in a wrong format, please check the parameters that you send. <span id="cb2ec4543be2h" />

<strong>原因：</strong> 缺少入参，或入参格式错误。

<strong>解决方案：</strong> 请检查请求参数是否完整且格式正确。

### Missing training files. <span id="3443400d5aoxp" />

<strong>原因：</strong> 参数错误，缺少参数或者参数格式问题等。

### The style is invalid. <span id="a92e9d7b84avs" />

<strong>原因：</strong> style不在枚举范围内。

<strong>解决方案：</strong> 请检查`style`参数的取值是否正确。

### The style\_level is invalid. <span id="39a57aedebi9f" />

<strong>原因：</strong> style\_level不在枚举范围内。

<strong>解决方案：</strong> 详情参见[EMO 视频生成](/zh/model-studio/emo-api)。

### parameters.video\_ratio must be 9:16 or 3:4. <span id="d147c86a163yl" />

<strong>原因：</strong> video\_ratio 入参只能为 9:16 或 3:4。

<strong>解决方案：</strong> 请修改`video_ratio`参数为 "9:16" 或 "3:4"。

### the xxx parm is invalid! <span id="f78e96731aa4l" />

<strong>原因：</strong> 输入参数超出范围。

<strong>解决方案：</strong> 详情参见[视频风格重绘](/zh/model-studio/video-style-transform-api-reference)。

### input json error. <span id="f74242572fvns" />

<strong>原因：</strong> 输入JSON错误。

<strong>解决方案：</strong> 请检查请求的JSON格式是否正确。
~~~~

来源#2：`deepseek-chat-completions.md`，chunk=15，version=acb1ddea03df5b2cb00d72d0f989cf84，HTTP=200

~~~~text
rg/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

property name* any

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

strict boolean

Default value: `false`

如果设置为 true，API 将在函数调用中使用 strict 模式，以确保输出始终符合函数的 JSON schema 定义。该功能为 Beta 功能，详细使用方式请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)

-

]

tool_choice string | object

nullable

控制模型调用 tool 的行为。

[同版本引用上下文]
无论是否设置，`data: [DONE]` 之前的最后一个块都会在其 `usage` 字段中给出整个请求的 token 使用统计信息。请注意，这里不会单独下发一个只含 usage 的块：统计信息附加在最后一个内容块上，该块的 `choices` 数组始终只包含一个元素，其中不含新增内容且 `finish_reason` 非 null。

temperature numbernullable

Possible values: `<= 2`

Default value: `1`

采样温度，介于 0 和 2 之间。更高的值，如 0.8，会使输出更随机，而更低的值，如 0.2，会使其更加集中和确定。 我们通常建议可以更改这个值或者更改 `top_p`，但不建议同时对两者进行修改。思考模式下不生效。

top_p numbernullable

Possible values: `<= 1`

Default value: `1`

作为调节采样温度的替代方案，模型会考虑前 `top_p` 概率的 token 的结果。所以 0.1 就意味着只有包括在最高 10% 概率中的 token 会被考虑。 取值必须大于 0 且不超过 1。我们通常建议修改这个值或者更改 `temperature`，但不建议同时对两者进行修改。该参数仅在思考模式下生效，有效取值范围为 0.95–1.0，低于 0.95 的取值会按 0.95 处理；在非思考模式下恒为 1.0，传入的值会被忽略。

tools

object[]

nullable

模型可能会调用的 tool 的列表。目前，仅支持 function 作为工具。使用此参数来提供以 JSON 作为输入参数的 function 列表。tool 名称必须唯一。

-

Array [

type stringrequired

Possible values: [`function`]

tool 的类型。目前仅支持 function。

function

object

required

description string

function 的功能描述，供模型理解何时以及如何调用该 function。

name stringrequired

要调用的 function 名称。必须由 a-z、A-Z、0-9 字符组成，或包含下划线和连字符，最大长度为 128 个字符。

parameters

object

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

property name* any

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

strict boolean

Default value: `false`

如果设置为 true，API 将在函数调用中使用 strict 模式，以确保输出始终符合函数的 JSON schema 定义。该功能为 Beta 功能，详细使用方式请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)

-

]

tool_choice string | object

nullable

控制模型调用 tool 的行为。
~~~~

来源#3：`qwen-structured-outputs.md`，chunk=171，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
}><p>允许额外字段</p></td><td style={{ verticalAlign: "top" }}><p>需要捕获更多信息</p></td></tr></tbody></table>

- <strong>支持的 JSON Schema 关键字</strong>

  以下列出 JSON Schema 模式（strict 模式）所支持的关键字。标记为"不支持"的关键字提交后会返回 400 错误。关键字的完整定义请参考 [JSON Schema 官方规范](https://json-schema.org/draft/2020-12)。

  **Schema 层面公共关键字**

[同版本引用上下文]
```json
{
  "properties": {"name": {"type": "string"}},
  "required": ["name"],
  "additionalProperties": true  // 允许额外字段
}
```

示例输入：`"我叫张三，25岁"`；输出：`{"name": "张三", "age": 25}`（包含未定义的 `age` 字段）。

<table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>值</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>行为</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>适用场景</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p><code>false</code></p></td><td style={{ verticalAlign: "top" }}><p>只输出定义的字段</p></td><td style={{ verticalAlign: "top" }}><p>需要精确控制结构</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p><code>true</code></p></td><td style={{ verticalAlign: "top" }}><p>允许额外字段</p></td><td style={{ verticalAlign: "top" }}><p>需要捕获更多信息</p></td></tr></tbody></table>

- <strong>支持的 JSON Schema 关键字</strong>

  以下列出 JSON Schema 模式（strict 模式）所支持的关键字。标记为"不支持"的关键字提交后会返回 400 错误。关键字的完整定义请参考 [JSON Schema 官方规范](https://json-schema.org/draft/2020-12)。

  **Schema 层面公共关键字**
~~~~

来源#4：`deepseek-thinking.md`，chunk=11，version=5804eb2d06c65774b4ea7ca978d9f8da，HTTP=200

~~~~text
给 API——即使该轮模型未实际进行工具调用。若您的代码中未正确回传 `reasoning_content`，API 会返回 400 报错。正确回传方法请您参考下面的样例代码。

### 样例代码

下面是一个简单的在思考模式下进行工具调用的样例代码：

[同版本引用上下文]
```
from openai import OpenAIclient = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")# Turn 1messages = [{"role": "user", "content": "9.11 and 9.8, which is greater?"}]response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stream=True,    reasoning_effort="high",    extra_body={"thinking": {"type": "enabled"}},)reasoning_content = ""content = ""for chunk in response:    if chunk.choices[0].delta.reasoning_content:        reasoning_content += chunk.choices[0].delta.reasoning_content    else:        content += chunk.choices[0].delta.content# Turn 2# The reasoning_content will be ignored by the APImessages.append({"role": "assistant", "reasoning_content": reasoning_content, "content": content})messages.append({'role': 'user', 'content': "How many Rs are there in the word 'strawberry'?"})response = client.chat.completions.create(    model="deepseek-flash",    messages=messages,    stream=True,    reasoning_effort="high",    extra_body={"thinking": {"type": "enabled"}},)# ...
```

## 工具调用

DeepSeek 模型的思考模式支持工具调用功能。模型在输出最终答案之前，可以进行多轮的思考与工具调用，以提升答案的质量。其调用模式如下图所示：

请注意，携带了 `tools` 参数的请求，在后续所有请求中，必须完整回传 `reasoning_content` 给 API——即使该轮模型未实际进行工具调用。若您的代码中未正确回传 `reasoning_content`，API 会返回 400 报错。正确回传方法请您参考下面的样例代码。

### 样例代码

下面是一个简单的在思考模式下进行工具调用的样例代码：
~~~~

来源#5：`deepseek-tool-calling.md`，chunk=9，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

~~~~text
- enum

- anyOf

#### object 类型

object 定义一个包含键值对的深层结构，其中 properties 定义了对象中每个键（属性）的 schema。每个 `object` 的所有属性均需设置为 `required`，且 `object` 中 `additionalProperties` 属性必须为 `false`。

示例：

```
{    "type": "object",    "properties": {        "name": { "type": "string" },        "age": { "type": "integer" }    },    "required": ["name", "age"],    "additionalProperties": false}
```

#### string 类型

- 支持的参数：

- pattern：使用正则表达式来约束字符串的格式

- format：使用预定义的常见格式进行校验，目前支持：

- email：电子邮件地址

- hostname：主机名

- ipv4：IPv4 地址

- ipv6：IPv6 地址

- uuid：uuid

- 不支持的参数

- minLength

- maxLength

示例：

[同版本引用上下文]
- enum

- anyOf

#### object 类型

object 定义一个包含键值对的深层结构，其中 properties 定义了对象中每个键（属性）的 schema。每个 `object` 的所有属性均需设置为 `required`，且 `object` 中 `additionalProperties` 属性必须为 `false`。

示例：

```
{    "type": "object",    "properties": {        "name": { "type": "string" },        "age": { "type": "integer" }    },    "required": ["name", "age"],    "additionalProperties": false}
```

#### string 类型

- 支持的参数：

- pattern：使用正则表达式来约束字符串的格式

- format：使用预定义的常见格式进行校验，目前支持：

- email：电子邮件地址

- hostname：主机名

- ipv4：IPv4 地址

- ipv6：IPv6 地址

- uuid：uuid

- 不支持的参数

- minLength

- maxLength

示例：

```
{    "type": "object",    "properties": {        "user_email": {            "type": "string",            "description": "The user's email address",            "format": "email"         },        "zip_code": {            "type": "string",            "description": "Six digit postal code",            "pattern": "^\\d{6}$"        }    }}
```

#### number/integer 类型

- 支持的参数

- const：固定数字为常数

- default：数字的默认值

- minimum：最小值

- maximum：最大值

- exclusiveMinimum：不小于

- exclusiveMaximum：不大于

- multipleOf：数字输出为这个值的倍数

示例：

```
{    "type": "object",    "properties": {        "score": {            "type": "integer",            "description": "A number from 1-5, which represents your rating, the higher, the better",            "minimum": 1,            "maximum": 5        }    },    "required": ["score"],    "additionalProperties": false}
```

#### array 类型

- 不支持的参数

- minItems

- maxItems

示例：
~~~~

来源#6：`qwen-errors.md`，chunk=79，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
ders）部分中查找Content-Type字段。
</Accordion>

### Field required: image\_url <span id="068dee94174u6" />

<strong>原因：</strong> 缺少入参`image_url`。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入`image_url`参数。

### Field required: driven\_id <span id="e204d0079324i" />

<strong>原因：</strong> 缺少入参`driven_id`。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入`driven_id`参数。

### Invalid ext\_bbox <span id="6b8ba11ceeyae" />

<strong>原因：</strong> 输入`ext_bbox`参数无效。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入正确的`ext_bbox`。

[同版本引用上下文]
- 若通过代码调用，请勿将content设置为如`[{"type": "text", "text": "你是谁？"}]`的array类型。
- 若使用 [Cline](/zh/model-studio/cline) ，请在设置界面单击`MODEL CONFIGURATION`，并勾选 <strong>Enable R1 messages format</strong>。

### The image size is not supported for the data inspection. <span id="80fd826206ngp" />

<strong>原因：</strong>

- 传入千问VL模型的图像尺寸（长度和宽度）不符合模型的要求。
- 输出图像大小超出限制（10MB）。

<strong>解决方案：</strong>

- 图像尺寸需满足以下要求：

  - 图像的宽度和高度均不小于10像素。
  - 宽高比不应超过200:1或1:200
- 调整生成图像的参数。

### Wrong Content-Type of multimodal url <span id="065e89dd58uf2" />

<strong>原因</strong>：URL请求的响应头信息`Content-Type`字段不正确。

> 千问VL模型支持的Content Type为：image/bmp、image/bmp、image/icns、image/x-icon、image/jpeg、image/jp2、image/png、image/sgi、image/tiff、image/webp。详情可参见[千问VL模型支持的图像](/zh/model-studio/vision)。

<strong>解决方案</strong>：

<Accordion title="查看 Content-Type 字段">
  1. 打开浏览器（如Chrome或Firefox）。
  2. 打开开发者工具（通常按F12或右键选择“检查”）。
  3. 切换到Network标签。
  4. 将图片的URL输入到地址栏并访问。
  5. 找到对应的请求，查看Headers部分，在“响应头”（Response Headers）部分中查找Content-Type字段。
</Accordion>

### Field required: image\_url <span id="068dee94174u6" />

<strong>原因：</strong> 缺少入参`image_url`。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入`image_url`参数。

### Field required: driven\_id <span id="e204d0079324i" />

<strong>原因：</strong> 缺少入参`driven_id`。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入`driven_id`参数。

### Invalid ext\_bbox <span id="6b8ba11ceeyae" />

<strong>原因：</strong> 输入`ext_bbox`参数无效。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入正确的`ext_bbox`。

### Driven not exist: driven\_id <span id="ed5667fb76b8l" />

<strong>原因：</strong>输入`driven_id`不存在。

<strong>解决方案：</strong> 请参考[Emoji 视频生成](/zh/model-studio/emoji-api)，传入正确的`driven_id`。
~~~~

来源#7：`qwen-errors.md`，chunk=62，version=1b6d411c48635d1caf9d6e9a2a37e4fe，HTTP=200

~~~~text
coarse\_image分辨率和person\_image不一致。

<strong>解决方案：</strong> 请确保`coarse_image`和`person_image`的分辨率一致。

### The request is missing required parameters or the parameters are out of the specified range, please check the parameters that you send. <span id="4801e93aceyx4" />

<strong>原因：</strong> 缺少必要的接口调用参数或参数越界。

<strong>解决方案：</strong> 请检查并修正请求参数。

### image format error <span id="02fbd65b8914g" />

<strong>原因：</strong> 图片格式错误。

<strong>解决方案：</strong> 需要是图片url或者Base64字符串。

### No messages found in input <span id="c44c41e120xr0" />

<strong>原因：</strong> 请求参数中需要有messages字段。

[同版本引用上下文]
### read image error. <span id="3aa64fea0bu40" />

<strong>原因：</strong> 读取图像失败。

<strong>解决方案：</strong> 请检查图像文件是否损坏或格式是否正确。

### the parameters must conform to the specification: xxx. <span id="d2c213820br34" />

<strong>原因：</strong> 输入参数值超出范围。

<strong>解决方案：</strong> 请根据错误提示`xxx`检查并修正参数值。

### The size of person image and coarse\_image are not the same. <span id="7e3ee4babdgjw" />

<strong>原因：</strong> coarse\_image分辨率和person\_image不一致。

<strong>解决方案：</strong> 请确保`coarse_image`和`person_image`的分辨率一致。

### The request is missing required parameters or the parameters are out of the specified range, please check the parameters that you send. <span id="4801e93aceyx4" />

<strong>原因：</strong> 缺少必要的接口调用参数或参数越界。

<strong>解决方案：</strong> 请检查并修正请求参数。

### image format error <span id="02fbd65b8914g" />

<strong>原因：</strong> 图片格式错误。

<strong>解决方案：</strong> 需要是图片url或者Base64字符串。

### No messages found in input <span id="c44c41e120xr0" />

<strong>原因：</strong> 请求参数中需要有messages字段。

<strong>解决方案：</strong> 详情参见[千问-图像编辑](/zh/model-studio/qwen-image-edit-api)。

### Invalid image format or corrupted file <span id="942bf3bd8bsz2" />

<strong>原因：</strong> 输入图片格式错误或文件损坏。

<strong>解决方案：</strong> 请检查文件是否可正常打开和下载，确保文件完整且格式符合要求。

### download image failed <span id="1356a14c63oq9" />

<strong>原因：</strong> 图片不能下载。

<strong>解决方案：</strong> 请检查文件是否可正常下载。

### messages length only support 1 <span id="913b3852abn4n" />

<strong>原因：</strong> messages数组长度仅支持 1。

<strong>解决方案：</strong> 即只能传入一条对话消息。详情参见[千问-图像编辑](/zh/model-studio/qwen-image-edit-api)。

### content length only support 2 <span id="23cf5fcc0dc3m" />

<strong>原因：</strong> content数组长度仅支持为2。

<strong>解决方案：</strong> 即只能传入一组text和image。详情参见[千问-图像编辑](/zh/model-studio/qwen-image-edit-api)。

### lack of image or text <span id="20bab1af67gld" />
~~~~

## N11 · comparison · comparison

DeepSeek JSON Output与Qwen的JSON Object模式，哪一种能自动确保符合指定JSON Schema？请区分合法JSON与Schema约束。

判分要求：两种JSON Object/JSON Output仅合法JSON不自动Schema保证；Qwen JSON Schema模式另有Schema约束，明确与JSON Object区分；分别引用两家依据

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**结论：两者都不能“自动确保符合指定 JSON Schema”。** 它们都只保证输出是合法 JSON 字符串，不保证字段结构、键名或类型符合你指定的 Schema。要约束 Schema，需要改用各自的 JSON Schema 模式。

**1. DeepSeek JSON Output**
- 作用：确保模型输出合法的 JSON 字符串（`response_format={'type':'json_object'}`），并要求提示词含 `json` 字样、给出格式样例来“指导”模型输出合法 JSON；还需合理设置 `max_tokens` 防止截断，且 API 有概率返回空 content。来源#4
- 它不提供 Schema 约束。DeepSeek 的 Schema 约束能力在别处：Responses API 的 `response_format` 支持 `{"type":"json_schema","name":...,"schema":...}`，输出符合给定 JSON Schema；来源#5 另外工具调用的 `strict` 模式（Beta，需 `base_url=https://api.deepseek.com/beta`、function 设 `strict:true`）会让 Function 调用严格遵循其 JSON Schema。来源#2

**2. Qwen JSON Object 模式**
- 作用：确保输出为标准格式的 JSON 字符串，但**不保证符合特定结构**；文档明确“JSON Object 模式不保证键名与字段类型稳定，不同提示词或不同次调用的返回结果可能存在差异。如需固定结构，请使用 JSON Schema 模式”。来源#1、来源#7
- 使用要求：`response_format={"type":"json_object"}`，且提示词需含 “JSON” 关键词，否则报错。来源#1、来源#3
- Qwen 的 Schema 约束在 JSON Schema 模式：`{"type":"json_schema","json_schema":{...,"strict":true}}`，输出严格符合指定 Schema，提示词无需含 JSON 关键词；`strict` 推荐设为 `true`，`additionalProperties` 推荐 `false`。来源#1、来源#3、来源#6

**3. 合法 JSON 与 Schema 约束的区别**
- 合法 JSON：只要求能被 JSON 解析器解析（无多余文本、无截断）。DeepSeek JSON Output 与 Qwen JSON Object 都属于这一层。来源#4、来源#1
- Schema 约束：还要求字段名、必填项、类型、是否允许额外字段等符合给定 JSON Schema。需使用 DeepSeek Responses API 的 `json_schema`（或工具调用 `strict`）／Qwen 的 `json_schema` 模式。来源#5、来源#2、来源#3、来源#6
- 适用范围提示：以上均为各厂商文档中的通用规则，具体可用模型/接口以对应文档为准（如 Qwen 注明 `json_object` 与 `json_schema` 支持的模型不同）。来源#3、来源#6

**建议**：若目标是“自动确保符合指定 JSON Schema”，不要依赖 DeepSeek JSON Output 或 Qwen JSON Object，应分别改用 DeepSeek Responses API 的 `json_schema`（或工具 `strict` 模式）与 Qwen 的 `json_schema` 模式，并在应用侧仍做一次 Schema 校验兜底。

来源#1: qwen-structured-outputs.md
来源#2: deepseek-tool-calling.md
来源#3: qwen-chat-completions.md
来源#4: deepseek-json-output.md
来源#5: deepseek-responses.md
来源#6: qwen-dashscope.md
来源#7: qwen-structured-outputs.md

### 实际引用锚点

来源#1：`qwen-structured-outputs.md`，chunk=1，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
Object 与 JSON Schema两种模式：

- <strong>JSON Object 模式</strong>：确保输出为标准格式的 JSON 字符串，但不保证符合特定结构。使用方式：

  1. <strong>设置</strong>`response_format`<strong>参数</strong>：在请求体中，将 `response_format` 参数设置为 `{"type": "json_object"}`。
  2. <strong>提示词包含 JSON 关键词</strong>：System Message 或 User Message 中需要包含 "JSON" 关键词（不区分大小写），否则会报错：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`

[同版本引用上下文]
# Qwen / 阿里云百炼：结构化输出

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 结构化输出

> 执行信息抽取或结构化数据生成任务时，大模型可能返回多余文本（如 ```json ）导致下游解析失败。开启结构化输出可确保大模型输出标准格式的 JSON 字符串，使用 JSON Schema 模式还能精确控制输出结构和类型，无需额外验证或重试。

<meta property="og:title" content="结构化输出" />

## 使用方式 <span id="364b79f28ebin" />

结构化输出支持JSON Object 与 JSON Schema两种模式：

- <strong>JSON Object 模式</strong>：确保输出为标准格式的 JSON 字符串，但不保证符合特定结构。使用方式：

  1. <strong>设置</strong>`response_format`<strong>参数</strong>：在请求体中，将 `response_format` 参数设置为 `{"type": "json_object"}`。
  2. <strong>提示词包含 JSON 关键词</strong>：System Message 或 User Message 中需要包含 "JSON" 关键词（不区分大小写），否则会报错：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`
- [<strong>JSON Schema 模式</strong>](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)：确保输出内容为指定的结构。使用方式：设置 `response_format` 为`{"type": "json_schema", "json_schema": {..., "strict": true}}`。

  > 提示词无需包含 JSON 关键词。

功能对比：
~~~~

来源#2：`deepseek-tool-calling.md`，chunk=6，version=436317cc6c7e5f0f90c8994f22196a0f，HTTP=200

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

来源#3：`qwen-chat-completions.md`，chunk=57，version=c176070e4f935753b783f52a5b593c2b，HTTP=200

~~~~text
- `{"type": "json_schema", "json_schema": {...}}`：输出严格符合指定 JSON Schema 的JSON字符串，可精确控制输出结构与字段类型。

        > 相关文档：[结构化输出](/zh/model-studio/qwen-structured-output)。`json_object` 与 `json_schema` 支持的模型不同，参见[支持的模型](/zh/model-studio/qwen-structured-output#7a8e438e89xeq)。

        > 若指定为`{"type": "json_object"}`，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错；若指定为`{"type": "json_schema", ...}`，提示词无需包含 JSON 关键词。

        <Accordion title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

[同版本引用上下文]
参数值为-2.0：这部电影很好。情节很好，演技很好，音乐也很好，总的来说，整部电影都很好。实际上，它真的很棒。情节非常好，演技也非常好，音乐也非常好。
        </Accordion>

        > 不建议修改QVQ模型的默认presence\_penalty值。

        <strong>response\_format</strong>`object` （可选） 默认值为`{"type": "text"}`

        返回内容的格式。可选值：

        - `{"type": "text"}`：输出文字回复；
        - `{"type": "json_object"}`：输出标准格式的JSON字符串。
        - `{"type": "json_schema", "json_schema": {...}}`：输出严格符合指定 JSON Schema 的JSON字符串，可精确控制输出结构与字段类型。

        > 相关文档：[结构化输出](/zh/model-studio/qwen-structured-output)。`json_object` 与 `json_schema` 支持的模型不同，参见[支持的模型](/zh/model-studio/qwen-structured-output#7a8e438e89xeq)。

        > 若指定为`{"type": "json_object"}`，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错；若指定为`{"type": "json_schema", ...}`，提示词无需包含 JSON 关键词。

        <Accordion title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > 通过 OpenAI SDK 的 `parse` 方法调用时，可直接传入 Python Pydantic 类或 Node.js Zod 对象，SDK 会自动将其转换为 JSON Schema，无需手动构造。

          <Accordion title="属性">
            <strong>name</strong>`string`<strong>（必选）</strong>

            Schema 的名称。

            <strong>schema</strong>`object`<strong>（必选）</strong>

            描述输出结构的 JSON Schema 对象。通过 `properties` 定义字段结构，通过 `required` 声明必填字段列表，通过 `additionalProperties` 控制是否允许输出未在 Schema 中定义的字段（推荐设置为 `false`，即只输出已定义的字段）。支持的数据类型：string、number、integer、boolean、object、array、enum。相关文档：[配置指南](/zh/model-studio/qwen-structured-output#001cb6ae072tc)。
~~~~

来源#4：`deepseek-json-output.md`，chunk=0，version=8ca3370a65d15df5b4e04f783542de05，HTTP=200

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

来源#5：`deepseek-responses.md`，chunk=12，version=47a4c8df60e15d7982216687963fc076，HTTP=200

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

[同版本引用上下文]
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

模型可能会调用的工具的列表。函数名必须非空、不超过 128 个字符、匹配 `^[a-zA-Z0-9_-]+$`，且所有工具的名称必须唯一。支持 `function` 工具；`web_search` 在 `deepseek-v4-pro` 下支持，其余内置工具类型会被忽略。详情请参考 [Responses API 指南](https://api-docs.deepseek.com/zh-cn/guides/responses_api)。

-

Array [

type stringrequired

Possible values: [`function`, `custom`, `web_search`]

工具的类型：`function`、`custom`（仅 `apply_patch`）或 `web_search`（仅 `deepseek-v4-pro`）。

name string

用于 `function` / `custom` 工具。工具的名称。对于函数工具，必须非空、不超过 128 个字符、匹配 `^[a-zA-Z0-9_-]+$`，且所有工具的名称必须唯一。对于 custom 工具，必须为 `apply_patch`。

description string

用于 `function` 工具。函数功能的描述，供模型理解何时以及如何调用该函数。

parameters

object

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

property name* any

function 的输入参数，以 JSON Schema 对象描述。请参阅[Tool Calls 指南](https://api-docs.deepseek.com/zh-cn/guides/tool_calls)获取示例，并参阅[JSON Schema 参考](https://json-schema.org/understanding-json-schema/)了解有关格式的文档。省略 `parameters` 会定义一个参数列表为空的 function。

-

]

tool_choice string | object

nullable

控制模型调用工具的行为。

`none` 意味着模型不会调用任何工具，而是生成一条消息。

`auto`（默认）意味着模型可以选择生成一条消息或调用一个或多个工具。

`required` 意味着模型必须调用一个或多个工具。

通过 `{"type": "function", "name": "my_function"}` 指定特定工具，会强制模型调用该工具。

oneOf

- Tool choice mode

- Named tool choice

string
~~~~

来源#6：`qwen-dashscope.md`，chunk=85，version=1568cf9930fa57e9b69311da840590de，HTTP=200

~~~~text
n title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > DashScope 方式需手动构造 JSON Schema，格式与示例参见[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。暂不支持 Java SDK。

[同版本引用上下文]
> 相关文档：[结构化输出](/zh/model-studio/qwen-structured-output)。`json_object` 与 `json_schema` 支持的模型不同，参见[支持的模型](/zh/model-studio/qwen-structured-output#7a8e438e89xeq)。

        > 若指定为`{"type": "json_object"}`，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错；若指定为`{"type": "json_schema", ...}`，提示词无需包含 JSON 关键词。

        > Java SDK中为responseFormat\*。\*通过HTTP调用时，请将 <strong>response\_format</strong>放入 <strong>parameters</strong> 对象中。

        <Accordion title="属性">
          <strong>type</strong>`string`<strong>（必选）</strong>

          返回内容的格式。可选值：

          - `text`：输出文字回复；
          - `json_object`：输出标准格式的JSON字符串；
          - `json_schema`：输出严格符合 `json_schema` 字段所定义结构的JSON字符串。

          <strong>json\_schema</strong>`object`（可选）

          `type` 为 `json_schema` 时必须设置，用于定义模型输出需要遵循的 JSON 结构。相关文档：[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。

          > DashScope 方式需手动构造 JSON Schema，格式与示例参见[获取指定格式的输出](/zh/model-studio/qwen-structured-output#a4f5d7108anxd)。暂不支持 Java SDK。

          <Accordion title="属性">
            <strong>name</strong>`string`<strong>（必选）</strong>

            Schema 的名称。

            <strong>schema</strong>`object`<strong>（必选）</strong>

            描述输出结构的 JSON Schema 对象。通过 `properties` 定义字段结构，通过 `required` 声明必填字段列表，通过 `additionalProperties` 控制是否允许输出未在 Schema 中定义的字段（推荐设置为 `false`，即只输出已定义的字段）。支持的数据类型：string、number、integer、boolean、object、array、enum。相关文档：[配置指南](/zh/model-studio/qwen-structured-output#001cb6ae072tc)。

            <strong>strict</strong>`boolean`（可选）

            是否严格遵循 `schema` 定义的结构。推荐设置为 `true`。
          </Accordion>
        </Accordion>

        <strong>result\_format</strong>`string`（可选）默认为`text`（Qwen3-Max、Qwen3-VL、[QwQ](/zh/model-studio/deep-thinking) 模型、Qwen3 开源模型与 Qwen-Long 模型默认值为 message）
~~~~

来源#7：`qwen-structured-outputs.md`，chunk=11，version=9de8f6837c4c5954b043ce88cf404f69，HTTP=200

~~~~text
<Tab title="JSON Schema">
    Qwen3.7-Plus 系列、Qwen3.8-Flash 系列、Qwen3.7-Flash 系列、Qwen3.7-Max 系列、Qwen3.8-Max 系列模型
  </Tab>
</Tabs>

## 快速开始 <span id="d571e02f03kzc" />

以从个人简介中抽取信息为例，演示结构化输出的基本用法。

> JSON Object 模式不保证键名与字段类型稳定，不同提示词或不同次调用的返回结果可能存在差异。如需固定结构，请使用 JSON Schema 模式。

您需要已[获取与配置 API Key](/zh/model-studio/get-api-key)并[配置API Key到环境变量](/zh/model-studio/configure-api-key-through-environment-variables)。如果通过OpenAI SDK或DashScope SDK进行调用，还需要[安装SDK](/zh/model-studio/install-sdk)。请将示例代码中的 `DASHSCOPE_API_HOST` 替换为获取的 API Host。

[同版本引用上下文]
<Tab title="JSON Schema">
    Qwen3.7-Plus 系列、Qwen3.8-Flash 系列、Qwen3.7-Flash 系列、Qwen3.7-Max 系列、Qwen3.8-Max 系列模型
  </Tab>
</Tabs>

## 快速开始 <span id="d571e02f03kzc" />

以从个人简介中抽取信息为例，演示结构化输出的基本用法。

> JSON Object 模式不保证键名与字段类型稳定，不同提示词或不同次调用的返回结果可能存在差异。如需固定结构，请使用 JSON Schema 模式。

您需要已[获取与配置 API Key](/zh/model-studio/get-api-key)并[配置API Key到环境变量](/zh/model-studio/configure-api-key-through-environment-variables)。如果通过OpenAI SDK或DashScope SDK进行调用，还需要[安装SDK](/zh/model-studio/install-sdk)。请将示例代码中的 `DASHSCOPE_API_HOST` 替换为获取的 API Host。

<Tabs>
  <Tab title="OpenAI兼容">
    <Tabs>
      <Tab title="Python">
        ```python expandable
        from openai import OpenAI
        import os

        client = OpenAI(
            # 如果没有配置环境变量，请用API Key将下行替换为：api_key="sk-xxx"
            # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
            base_url="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        )

        completion = client.chat.completions.create(
            model="qwen3.8-max",
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "请抽取用户的姓名与年龄信息，以JSON格式返回"}]
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "大家好，我叫刘五，今年34岁，邮箱是liuwu@example.com，平时喜欢打篮球和旅游"}],
                },
            ],
            response_format={"type": "json_object"}
        )

        json_string = completion.choices[0].message.content
        print(json_string)
        ```
~~~~

## N12 · qwen · insufficient

现有Qwen文档能否保证text-embedding-v4在2099年仍然免费、批量上限不变？

判分要求：当前资料不足以保证未来费用与限制；当前快照价格和限制不得当成未来承诺

审阅：UNREVIEWED。待按冻结要求审阅

### 原始回答

**不能。** 现有 Qwen 文档无法保证 text-embedding-v4 在 2099 年仍然免费，也无法保证批量上限不变。

**关于“免费”**
- 文档显示 text-embedding-v4 当前为**无免费额度**，按量计费（0.000514元）[来源#2]。也就是说，现有资料本身并不支持“该模型免费”这一前提。
- 文档是某一时点的官方正文快照（核对日期 2026-10-19），核对日期不等于规则生效日，也不构成对未来价格或免费政策的承诺[来源#1]。
- 因此，文档既不能证明它现在免费，更不能保证到 2099 年仍免费。

**关于“批量上限不变”**
- 文档只说明 text-embedding-v4 **支持批量推理**[来源#1]，并列出其限流数值（Batch API 调用不受限流限制，RPM 1,800 / TPM 1,200,000）[来源#5]。
- 这些是当前快照中的数值，文档没有任何“长期不变”或“未来版本保持”的承诺。
- 因此不能据此保证 2099 年批量上限不变。

**建议下一步**
- 如需长期稳定性承诺（价格、配额、SLA），请以阿里云百炼官方最新公告和商务合同条款为准，或联系阿里云商务/支持获取书面确认。
- 如需核对当前实际配额与计费，请在阿里云百炼控制台查看您账户下的实时数据。

来源#1: qwen-embedding-v4.md
来源#2: qwen-embedding-api.md
来源#3: qwen-embedding-api.md
来源#4: qwen-rate-limits.md
来源#5: qwen-rate-limits.md
来源#6: qwen-embedding-api.md
来源#7: qwen-batch.md

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

[同版本引用上下文]
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

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际
~~~~

来源#2：`qwen-embedding-api.md`，chunk=12，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
<tbody>
        <tr>
          <td>
            qwen3.7-text-embedding
          </td>

          <td>
            2560、2,048、1,536、1,024（默认）、768、512、256
          </td>

          <td>
            20
          </td>

          <td>
            128,000
          </td>

          <td>
            0.000525元
          </td>

          <td>
            中文、英语、西班牙语、法语、葡萄牙语、印尼语、日语、韩语、德语、俄罗斯语等201种主流语种与方言
          </td>

          <td>
            无免费额度
          </td>
        </tr>

        <tr>
          <td>
            text-embedding-v4

[同版本引用上下文]
<tbody>
        <tr>
          <td>
            qwen3.7-text-embedding
          </td>

          <td>
            2560、2,048、1,536、1,024（默认）、768、512、256
          </td>

          <td>
            20
          </td>

          <td>
            128,000
          </td>

          <td>
            0.000525元
          </td>

          <td>
            中文、英语、西班牙语、法语、葡萄牙语、印尼语、日语、韩语、德语、俄罗斯语等201种主流语种与方言
          </td>

          <td>
            无免费额度
          </td>
        </tr>

        <tr>
          <td>
            text-embedding-v4

            > 属于[Qwen3-Embedding](https://qwenlm.github.io/zh/blog/qwen3-embedding/)系列
          </td>

          <td>
            2,048、1,536、1,024（默认）、768、512、256、128、64
          </td>

          <td rowSpan={2}>
            10
          </td>

          <td rowSpan={2}>
            8,192
          </td>

          <td rowSpan={2}>
            0.000514元
          </td>

          <td>
            中文、英语、西班牙语、法语、葡萄牙语、印尼语、日语、韩语、德语、俄罗斯语等100+主流语种及多种编程语言
          </td>

          <td>
            无免费额度
          </td>
        </tr>

        <tr>
          <td>
            text-embedding-v3
          </td>

          <td>
            1,024（默认）、768、512
          </td>

          <td>
            中文、英语、西班牙语、法语、葡萄牙语、印尼语、日语、韩语、德语、俄罗斯语等50+主流语种
          </td>

          <td>
            50万Token

            有效期：百炼开通后90天内
          </td>
        </tr>
      </tbody>
    </table>
  </Tab>
</Tabs>

关于模型限流，请参考[限流](/zh/model-studio/rate-limit#953ddcd76495l)。

## 前提条件 <span id="9d4c1e7735hni" />

若熟悉OpenAI生态，可使用兼容API快速迁移；DashScope API则提供更丰富的独有特性。请根据您的需求选择。
~~~~

来源#3：`qwen-embedding-api.md`，chunk=73，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
TextEmbeddingParam param = TextEmbeddingParam
                                  .builder()
                                  .model("qwen3.7-text-embedding")  // 使用text-embedding-v4模型
                                  .texts(Arrays.asList("衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买"))  // 输入文本
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();

[同版本引用上下文]
/**
               * 千问文本向量模型调用示例
               */
              public final class Main {
                  public static void main(String[] args) {
                      // 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                      Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
                      try {
                          // 构建请求参数
                          TextEmbeddingParam param = TextEmbeddingParam
                                  .builder()
                                  .model("qwen3.7-text-embedding")  // 使用text-embedding-v4模型
                                  .texts(Arrays.asList("衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买"))  // 输入文本
                                  .parameter("dimension", 1024)  // 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                                  .build();

                          // 创建模型实例并调用
                          TextEmbedding textEmbedding = new TextEmbedding();
                          TextEmbeddingResult result = textEmbedding.call(param);

                          // 输出结果
                          System.out.println(result);

                      } catch (ApiException | NoApiKeyException e) {
                          System.out.println("调用失败：" + e.getMessage());
                      }
                  }
              }
              ```
~~~~

来源#4：`qwen-rate-limits.md`，chunk=5，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
模型输出速度与是否付费无关。免费额度和付费调用使用相同的模型服务基础设施，同一模型的生成速度相同。免费额度仅控制请求是否被接受——额度耗尽时返回 403 错误（开通<strong>免费额度用完即停</strong>后），不会降低已接受请求的生成速度。

### 什么因素影响模型响应速度？ <span id="faq-speed-factors-h" />

- <strong>模型类型</strong>：轻量模型（如 qwen-flash）比大型模型（如 qwen-max）生成更快。
- <strong>输出长度</strong>：输出 Token 越多，总耗时越长。
- <strong>服务器负载</strong>：高峰期可能略有波动。

### 限流会降低已接受请求的生成速度吗？ <span id="faq-rate-limit-speed-h" />

不会。限流（RPM/TPM）仅导致超出限制的请求被拒绝（返回 429 错误）。免费额度耗尽时（开通<strong>免费额度用完即停</strong>）返回 403 错误，同样不影响已接受请求的速度。429 为速率限制，403 为配额耗尽，两者均为拒绝机制。

### 如何避免限流？ <span id="0e4e875b9c2eg" />

1. <strong>选用高限流模型</strong>

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

来源#5：`qwen-rate-limits.md`，chunk=740，version=48620305e68a513793942e9733fecea9，HTTP=200

~~~~text
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

[同版本引用上下文]
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
~~~~

来源#6：`qwen-embedding-api.md`，chunk=93，version=912a49054a48508fbb057489c39f548c，HTTP=200

~~~~text
# 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                    )

                    if resp.status_code == HTTPStatus.OK:
                        print(resp)
                    else:
                        print(resp)
                ```
              </Tab>

[同版本引用上下文]
```bash curl
              curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding' \
              --header "Authorization: Bearer $DASHSCOPE_API_KEY" \
              --header 'Content-Type: application/json' \
              --data '{
                  "model": "qwen3.7-text-embedding",
                  "input": {
                      "texts": [
                        "风急天高猿啸哀",
                        "渚清沙白鸟飞回",
                        "无边落木萧萧下",
                        "不尽长江滚滚来"
                      ]
                  },
                  "parameters": {
                        "dimension": 1024,
                        "output_type": "dense"
                  }
              }'
              ```
            </CodeGroup>
          </Tab>

          <Tab title="输入文件">
            <Tabs>
              <Tab title="Python">
                ```python
                from http import HTTPStatus
                from dashscope import TextEmbedding
                # 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
                dashscope.base_http_api_url = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1"

                with open('texts_to_embedding.txt', 'r', encoding='utf-8') as f:
                    resp = TextEmbedding.call(
                        model="qwen3.7-text-embedding",
                        input=f,
                        dimension=1024 # 指定向量维度（仅 qwen3.7-text-embedding、text-embedding-v3及 text-embedding-v4支持该参数）
                    )

                    if resp.status_code == HTTPStatus.OK:
                        print(resp)
                    else:
                        print(resp)
                ```
              </Tab>
~~~~

来源#7：`qwen-batch.md`，chunk=5，version=242cba5e060250b996ca68582c1a898c，HTTP=200

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
