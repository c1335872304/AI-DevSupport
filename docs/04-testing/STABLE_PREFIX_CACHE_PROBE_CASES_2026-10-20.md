# 稳定前缀独立缓存实验：逐题答复

固定已授权证据的格式对照，不替代真实检索验收；来源签名不公开。

## baseline · P-DS-1

DeepSeek JSON Output接入时response_format和提示词应如何配置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

接入 DeepSeek JSON Output 时，请求需将 `response_format` 设为 `{"type": "json_object"}`；该参数默认值为 `text`，可选值仅 `text` 与 `json_object`（来源#1、来源#5）。同时，system 或 user prompt 中必须出现 `json` 字样，并给出期望输出的 JSON 格式样例，否则模型可能持续生成空白直至 token 上限（来源#1、来源#5）。还应合理设置 `max_tokens`，避免 JSON 被截断；若 `finish_reason="length"`，内容可能不完整（来源#1、来源#5）。注意 API 有概率返回空 content，可调整 prompt 缓解（来源#1）。`deepseek-flash` 与 `deepseek-v4-pro` 均支持 JSON Output（来源#2）。

```json
{
  "model": "deepseek-flash",
  "messages": [
    {"role": "system", "content": "请输出 json，格式示例：{\"question\":\"...\",\"answer\":\"...\"}"},
    {"role": "user", "content": "..."}
  ],
  "response_format": {"type": "json_object"},
  "max_tokens": 1024
}
```

来源#1: deepseek-json-output.md
来源#2: deepseek-models-pricing.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-rate-limits.md
来源#5: deepseek-chat-completions.md
来源#6: deepseek-anthropic-protocol.md
来源#7: deepseek-quickstart.md

## baseline · P-DS-2

DeepSeek JSON Output接入时，response_format的type如何设置，提示词需要包含什么？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

DeepSeek JSON Output 接入时，将 `response_format` 设为 `{"type": "json_object"}` 即可启用 JSON 模式，该模式保证模型生成的消息是有效 JSON（来源#3、来源#7）。提示词方面，system 或 user prompt 中必须含有 `json` 字样，并给出希望模型输出的 JSON 格式样例，以指导模型输出合法 JSON（来源#7）。此外需合理设置 `max_tokens`，防止 JSON 字符串被中途截断；若 `finish_reason="length"`，说明生成超过 `max_tokens` 或对话超过最大上下文长度，内容可能被部分截断（来源#3、来源#7）。注意使用 JSON 模式时若未通过系统或用户消息指示模型生成 JSON，模型可能持续生成空白字符直至达到 token 限制，导致请求长时间运行（来源#3）。文档还提示该功能有概率返回空 content，可通过修改 prompt 缓解（来源#7）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    response_format={"type": "json_object"},
    max_tokens=1024,
)
```

来源#1: deepseek-quickstart.md
来源#2: deepseek-anthropic-protocol.md
来源#3: deepseek-chat-completions.md
来源#4: deepseek-rate-limits.md
来源#5: deepseek-fim-api.md
来源#6: deepseek-models-pricing.md
来源#7: deepseek-json-output.md

## baseline · P-DS-3

DeepSeek JSON模式的参数和prompt该怎么设置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

DeepSeek JSON 模式需同时设置参数和 prompt：请求体中将 `response_format` 设为 `{"type": "json_object"}`，并在 system 或 user prompt 中明确出现 `json` 字样，同时给出期望的 JSON 结构示例，以引导模型输出合法 JSON（来源#4、来源#7）。还需合理设置 `max_tokens`，避免 JSON 被截断；若 `finish_reason="length"`，内容可能不完整（来源#4、来源#7）。注意该功能有概率返回空 content，可通过调整 prompt 缓解（来源#7）。模型可选 `deepseek-flash` 或 `deepseek-v4-pro`，二者均支持 JSON Output（来源#1）。

```json
{
  "model": "deepseek-flash",
  "messages": [
    {"role": "system", "content": "请以 json 输出，格式示例：{\"question\":\"...\",\"answer\":\"...\"}"},
    {"role": "user", "content": "世界最长的河流是什么？尼罗河。"}
  ],
  "response_format": {"type": "json_object"},
  "max_tokens": 1024
}
```

来源#1: deepseek-models-pricing.md
来源#2: deepseek-fim-api.md
来源#3: deepseek-rate-limits.md
来源#4: deepseek-chat-completions.md
来源#5: deepseek-anthropic-protocol.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-json-output.md

## baseline · P-DS-4

DeepSeek JSON Output接入时response_format和提示词应如何配置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

接入 DeepSeek JSON Output 时，在 Chat Completions 请求中把 `response_format` 设为 `{"type": "json_object"}`，该模式保证模型生成的消息是有效 JSON（来源#1、来源#5）。同时，system 或 user prompt 中必须出现 `json` 字样，并给出期望输出格式的样例，以指导模型生成合法 JSON；否则模型可能持续输出空白字符直至达到 token 限制（来源#1、来源#5）。还需合理设置 `max_tokens`，防止 JSON 被截断；若 `finish_reason="length"`，内容可能不完整（来源#1、来源#5）。注意该功能有概率返回空 content，可通过调整 prompt 缓解（来源#1）。`deepseek-flash` 与 `deepseek-v4-pro` 均支持 JSON Output（来源#2）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": "请以 JSON 格式输出，示例：{\"question\": \"...\", \"answer\": \"...\"}"},
        {"role": "user", "content": user_prompt},
    ],
    response_format={"type": "json_object"},
    max_tokens=1024,
)
```

来源#1: deepseek-json-output.md
来源#2: deepseek-models-pricing.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-rate-limits.md
来源#5: deepseek-chat-completions.md
来源#6: deepseek-anthropic-protocol.md
来源#7: deepseek-quickstart.md

## baseline · P-GPT-1

OpenAI后台响应如何开启，queued和in_progress时怎样轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

开启后台响应：创建 Responses 时设置 `background: true`（Python 为 `background=True`，Go 为 `Background: openai.Bool(true)`），并指定模型与输入；返回对象含 `id` 和 `status`（来源#1、来源#5）。轮询时用该 `id` 调用 Responses 的 GET/retrieve 接口，只要状态仍为 `queued` 或 `in_progress` 就继续，离开这两个状态即进入终态，可读取最终结果（来源#1、来源#2、来源#5）。示例间隔为 2 秒，仅为文档示例，并非强制参数（来源#1、来源#5）。

```python
resp = client.responses.create(model="gpt-6-astra", input="...", background=True)
while resp.status in {"queued", "in_progress"}:
    time.sleep(2)
    resp = client.responses.retrieve(resp.id)
```

上述代码需由调用方提供 `client` 并导入 `time`；`resp` 在循环中重新赋值，不能声明为只读常量（来源#5）。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-background.md
来源#6: gpt-webhooks.md

## baseline · P-GPT-2

OpenAI Responses后台模式怎么开启？queued和in_progress期间如何查询进度？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

开启后台模式：调用 Responses 创建接口时设置 `background=true`（Go 为 `Background: openai.Bool(true)`，C# 为 `BackgroundModeEnabled = true`），创建后保存返回的响应 ID（来源#2、来源#5、来源#6）。

查询进度：在状态为 `queued` 或 `in_progress` 期间，用该 ID 调用 GET `/v1/responses/{response_id}` 轮询，示例间隔为 2 秒；状态离开这两个值即进入终态，可读取 `output_text`（来源#2、来源#6）。轮询变量需在循环中更新，不能声明为只读常量。

```python
resp = client.responses.create(model="gpt-6-astra", input="...", background=True)
while resp.status in {"queued", "in_progress"}:
    resp = client.responses.retrieve(resp.id)
    sleep(2)
print(resp.status, resp.output_text)
```

也可用 `response.completed` webhook 事件获知完成（来源#1）。文档片段未说明轮询频率上限或超时策略。

来源#1: gpt-webhooks.md
来源#2: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-background.md
来源#6: gpt-background.md

## baseline · P-GPT-3

OpenAI后台响应怎样配置background，什么时候停止轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

在 OpenAI Responses API 创建请求时，将 `background` 设为 `true`（部分 SDK 为 `BackgroundModeEnabled`/`Background: true`）即可启用后台响应，创建后返回响应 ID 和状态（来源#1、来源#4、来源#6）。轮询时用该 ID 调用 GET `/v1/responses/{id}` 检索；只要状态仍为 `queued` 或 `in_progress` 就继续轮询，离开这两个状态即到达终态，应停止轮询并读取最终状态与输出（来源#6）。示例间隔为 2 秒，仅为示例，不是强制值（来源#1、来源#4）。后台响应也可取消（来源#1）。

```python
resp = client.responses.create(model="gpt-6-astra", input="...", background=True)
while resp.status in {"queued", "in_progress"}:
    time.sleep(2)
    resp = client.responses.retrieve(resp.id)
```

来源#1: gpt-background.md
来源#2: gpt-rate-limits.md
来源#4: gpt-background.md
来源#5: gpt-webhooks.md
来源#6: gpt-background.md

## baseline · P-GPT-4

OpenAI后台响应如何开启，queued和in_progress时怎样轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

开启后台响应：创建 Response 时设置 `background: true`（C# 为 `BackgroundModeEnabled = true`），模型与输入按调用方配置；创建后读取返回的 `status` 和 `id`（来源#1、来源#5）。

轮询：在 `status` 为 `queued` 或 `in_progress` 时，用 GET `/v1/responses/{response_id}`（SDK 为 `responses.retrieve(id)`）重复查询；离开这两个状态即进入终态，可读取最终状态及输出。

```javascript
let resp = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true,
});
while (resp.status === "queued" || resp.status === "in_progress") {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  resp = await client.responses.retrieve(resp.id);
}
```

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-background.md
来源#6: gpt-webhooks.md

## baseline · P-QW-1

Qwen北京地域的API Key应配哪里的Base URL，还要匹配什么计费方案？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 Qwen API Key 应配 Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`（OpenAI 兼容）；若用 Anthropic 兼容则为 `https://dashscope.aliyuncs.com/apps/anthropic`（来源#1、来源#4）。计费方案上，该地址属于“按量付费”下的 Dashscope 域名，API Key 必须与同一计费方案的 Base URL 配套，否则返回 401（来源#1）。此外，API Key 与 Base URL 必须同属北京地域，各地域 Key 相互独立、不能跨地域混用（来源#1、来源#2）。若使用 Coding Plan 或 Token Plan 团队版等套餐专属 Key（`sk-sp-` 开头），须改用各自专属 Base URL，不能与上述通用地址混用（来源#3）。

来源#1: qwen-base-url.md
来源#2: qwen-api-key.md
来源#3: qwen-errors.md
来源#4: qwen-api-key.md
来源#5: qwen-batch.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

## baseline · P-QW-2

Qwen北京地域的API Key应配哪一个OpenAI兼容Base URL，计费方案有什么匹配要求？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 OpenAI 兼容 Base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#3、来源#4、来源#7）。计费方案匹配要求：Base URL 必须与同一计费方案的 API Key 配套使用，否则会返回 401（来源#7）；同时 API Key 与 Base URL 必须属于同一地域，不能跨地域混用（来源#6、来源#7）。若使用 Coding Plan 或 Token Plan 团队版等套餐专属 Key（`sk-sp-` 开头），须改用各自专属 Base URL，不可与通用地址混用（来源#5）。

```text
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=<北京地域对应计费方案的 API Key>
```

来源#1: qwen-regions.md
来源#2: qwen-quickstart.md
来源#3: qwen-batch.md
来源#4: qwen-api-key.md
来源#5: qwen-errors.md
来源#6: qwen-api-key.md
来源#7: qwen-base-url.md

## baseline · P-QW-3

Qwen北京的Base URL和API Key怎么配套，能否跨地域或计费方案混用？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 Qwen API 需使用北京地域的 API Key 配套调用，OpenAI 兼容 Base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#3、来源#7）。每个地域有独立的接入域名、API Key 和模型列表，不能跨地域混用；例如北京 API Key 配新加坡 Base URL 会报鉴权错误（来源#1、来源#2）。此外，Base URL 必须与同一计费方案的 API Key 配套，否则返回 401；Coding Plan、Token Plan 团队版的 `sk-sp-` 专属 Key 只能配各自专属 Base URL，不可与通用 Key/URL 混用（来源#2、来源#7）。其他地域地址需查 Base URL 总览（来源#3）。

来源#1: qwen-api-key.md
来源#2: qwen-errors.md
来源#3: qwen-api-key.md
来源#4: qwen-batch.md
来源#5: qwen-quickstart.md
来源#6: qwen-regions.md
来源#7: qwen-base-url.md

## baseline · P-QW-4

Qwen北京地域的API Key应配哪里的Base URL，还要匹配什么计费方案？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 Qwen API Key 应配 Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`（OpenAI 兼容）；若用 Anthropic 兼容则为 `https://dashscope.aliyuncs.com/apps/anthropic`（来源#1、来源#4）。计费方案上，Base URL 必须与同一计费方案的 API Key 配套，否则返回 401；上述地址属于按量付费的 Dashscope 域名（来源#1）。此外各地域 API Key 相互独立、不能跨地域使用，需确保 Key 与北京地域一致（来源#1、来源#2）。若使用 Coding Plan 或 Token Plan 团队版等套餐专属 Key（`sk-sp-` 开头），则须改用各自专属 Base URL，不能与通用地址混用（来源#3）。

来源#1: qwen-base-url.md
来源#2: qwen-api-key.md
来源#3: qwen-errors.md
来源#4: qwen-api-key.md
来源#5: qwen-batch.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

## final · P-DS-1

DeepSeek JSON Output接入时response_format和提示词应如何配置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

DeepSeek JSON Output 需同时配置参数和提示词：

1. **response_format**：设为 `{"type": "json_object"}`，该模式保证模型生成的消息是有效 JSON（来源#2、来源#4）。
2. **提示词**：system 或 user prompt 中必须含有 `json` 字样，并给出期望输出的 JSON 格式样例，以指导模型生成合法 JSON（来源#4）。
3. **max_tokens**：需合理设置，防止 JSON 字符串被中途截断；若 `finish_reason="length"`，内容可能被部分截断（来源#2、来源#4）。
4. **注意**：使用 JSON Output 时 API 有概率返回空 content，可尝试修改 prompt 缓解（来源#4）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,  # 含 json 字样及格式样例
    response_format={"type": "json_object"},
    max_tokens=1000,
)
```

`deepseek-flash` 与 `deepseek-v4-pro` 均支持 JSON Output（来源#5）。

来源#1: deepseek-anthropic-protocol.md
来源#2: deepseek-chat-completions.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-json-output.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-rate-limits.md

## final · P-DS-2

DeepSeek JSON Output接入时，response_format的type如何设置，提示词需要包含什么？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

在 DeepSeek API 中启用 JSON Output，需将 `response_format` 设为 `{"type": "json_object"}`（来源#2、来源#4）。同时，system 或 user 提示词中必须出现 `json` 字样，并给出期望输出的 JSON 格式样例，以引导模型生成合法 JSON（来源#4）。还应合理设置 `max_tokens`，避免 JSON 被截断；若 `finish_reason="length"`，内容可能不完整（来源#2、来源#4）。注意该功能有概率返回空 content，可通过调整提示词缓解（来源#4）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,  # 提示词需含 "json" 及格式样例
    response_format={"type": "json_object"},
    max_tokens=1000,
)
```

来源#1: deepseek-anthropic-protocol.md
来源#2: deepseek-chat-completions.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-json-output.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-rate-limits.md

## final · P-DS-3

DeepSeek JSON模式的参数和prompt该怎么设置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

DeepSeek JSON 模式需在 Chat Completions 请求中设置 `response_format` 为 `{"type": "json_object"}`，该参数默认值为 `text`，可选值仅 `text` 或 `json_object`（来源#2）。同时，system 或 user prompt 中必须出现 `json` 字样，并给出期望输出的 JSON 格式样例，以指导模型生成合法 JSON（来源#4）。还需合理设置 `max_tokens`，防止 JSON 被截断；若 `finish_reason="length"`，内容可能不完整（来源#2、来源#4）。注意该功能有概率返回空 content，可通过调整 prompt 缓解（来源#4）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,  # 由调用方提供，含 json 字样及格式样例
    response_format={"type": "json_object"},
    max_tokens=1000,  # 由调用方按需设置
)
```

来源#1: deepseek-anthropic-protocol.md
来源#2: deepseek-chat-completions.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-json-output.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-rate-limits.md

## final · P-DS-4

DeepSeek JSON Output接入时response_format和提示词应如何配置？

审阅：PASS；JSON模式、prompt含json及格式样例、防截断和空content风险正确；引用对应本轮编号。

DeepSeek JSON Output 需同时配置参数和提示词，缺一不可：

1. **参数**：在 Chat Completions 请求中设置 `response_format={"type": "json_object"}`，该模式保证模型生成的消息是有效 JSON（来源#2、来源#4）。
2. **提示词**：system 或 user prompt 中必须含有 `json` 字样，并给出期望输出 JSON 格式的样例，以指导模型生成合法 JSON（来源#4）。
3. **max_tokens**：需合理设置，防止 JSON 字符串被中途截断；若 `finish_reason="length"`，内容可能被部分截断（来源#2、来源#4）。

注意：API 有概率返回空 content，可通过修改 prompt 缓解（来源#4）。`deepseek-flash` 与 `deepseek-v4-pro` 均支持 JSON Output（来源#5）。

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": "请以 json 格式输出，样例：{\"question\": \"...\", \"answer\": \"...\"}"},
        {"role": "user", "content": "..."}
    ],
    response_format={"type": "json_object"},
    max_tokens=1000
)
```

来源#1: deepseek-anthropic-protocol.md
来源#2: deepseek-chat-completions.md
来源#3: deepseek-fim-api.md
来源#4: deepseek-json-output.md
来源#5: deepseek-models-pricing.md
来源#6: deepseek-quickstart.md
来源#7: deepseek-rate-limits.md

## final · P-GPT-1

OpenAI后台响应如何开启，queued和in_progress时怎样轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

开启后台响应：在 Responses 创建请求中设置 `background: true`（C# 为 `BackgroundModeEnabled = true`，Go 为 `Background: openai.Bool(true)`），并指定模型与输入；返回后读取 `status`（来源#1、来源#2、来源#3）。

轮询：用响应 `id` 调用 Responses 的 GET/retrieve 接口；当状态为 `queued` 或 `in_progress` 时继续轮询，离开这两个状态即进入终态，可读取最终状态和输出。示例间隔为 2 秒（来源#1、来源#2、来源#3）。

```python
resp = client.responses.create(model="gpt-6-astra", input="...", background=True)
while resp.status in {"queued", "in_progress"}:
    time.sleep(2)
    resp = client.responses.retrieve(resp.id)
print(resp.status, resp.output_text)
```

上述模型名仅为文档示例，不代表唯一可选模型；实际可用模型及账户限额需以对应文档或控制台为准（来源#1、来源#4）。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-webhooks.md

## final · P-GPT-2

OpenAI Responses后台模式怎么开启？queued和in_progress期间如何查询进度？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

开启后台模式：在创建 Responses 请求时设置 `background: true`（Python 为 `background=True`，Go 为 `Background: openai.Bool(true)`），模型示例为 `gpt-6-astra`（来源#1、来源#2、来源#3）。创建后返回的响应含 `status` 和 `id`。

查询进度：用 Responses 的 GET 接口按响应 ID 轮询，例如 `GET https://api.openai.com/v1/responses/resp_123`；当 `status` 为 `queued` 或 `in_progress` 时继续轮询，离开这两个状态即进入终态（来源#1）。轮询间隔示例为 2 秒（来源#1、来源#2）。

```python
resp = client.responses.create(model="gpt-6-astra", input="...", background=True)
while resp.status in {"queued", "in_progress"}:
    sleep(2)
    resp = client.responses.retrieve(resp.id)
```

上述片段仅说明通用流程；具体账户的可用模型、速率限制及后台任务时限未在所给资料中说明（来源#4仅描述限流指标，未给出具体额度）。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-webhooks.md

## final · P-GPT-3

OpenAI后台响应怎样配置background，什么时候停止轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

在 OpenAI Responses API 中，创建请求时把 `background` 设为 `true` 即可启用后台模式，例如 `model: "gpt-6-astra", input: "...", background: true`（来源#1、来源#3）。随后用 Responses 的 GET/retrieve 接口按响应 ID 轮询状态；当状态为 `queued` 或 `in_progress` 时继续轮询，离开这两个状态即进入终态，应停止轮询（来源#1、来源#2）。轮询间隔示例为 2 秒，可按需调整（来源#1）。后台响应也可通过 cancel 接口取消（来源#3）。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-webhooks.md

## final · P-GPT-4

OpenAI后台响应如何开启，queued和in_progress时怎样轮询？

审阅：PASS；background开启、GET/retrieve按queued/in_progress继续轮询及终态停止正确；片段变量及client由调用方提供。

在 OpenAI Responses API 中，创建请求时把 `background` 设为 `true`（C# 为 `BackgroundModeEnabled = true`）即可开启后台响应，例如指定 `model: "gpt-6-astra"` 和输入内容（来源#1、来源#2）。创建后轮询 `GET /v1/responses/{response_id}`：只要状态仍为 `queued` 或 `in_progress` 就继续等待并重新获取，离开这两个状态即到达终态；示例间隔为 2 秒（来源#1、来源#2）。轮询时需用返回的响应 ID 调用 retrieve，不能只保留首次响应对象（来源#1、来源#3）。

```javascript
let resp = await client.responses.create({
  model: "gpt-6-astra",
  input: "Write a very long novel about otters in space.",
  background: true,
});
while (resp.status === "queued" || resp.status === "in_progress") {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  resp = await client.responses.retrieve(resp.id);
}
```

上述代码中的 `client` 需由调用方预先初始化并配置 API 密钥（来源#1）。

来源#1: gpt-background.md
来源#2: gpt-background.md
来源#3: gpt-background.md
来源#4: gpt-rate-limits.md
来源#5: gpt-webhooks.md

## final · P-QW-1

Qwen北京地域的API Key应配哪里的Base URL，还要匹配什么计费方案？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 Qwen API Key 应配合同地域的 Base URL：OpenAI 兼容调用使用 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#2、来源#3）。Base URL 必须与同一计费方案的 API Key 配套使用，否则会返回 401；API Key 与 Base URL 也不能跨地域混用（来源#3）。此外，Coding Plan、Token Plan 团队版等套餐使用 `sk-sp-` 开头的专属 Key，必须配合各自专属 Base URL，不能与通用 Key/Base URL 混用（来源#5）。

来源#1: qwen-api-key.md
来源#2: qwen-api-key.md
来源#3: qwen-base-url.md
来源#4: qwen-batch.md
来源#5: qwen-errors.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

## final · P-QW-2

Qwen北京地域的API Key应配哪一个OpenAI兼容Base URL，计费方案有什么匹配要求？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

Qwen 北京地域的 OpenAI 兼容 Base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#2、来源#3）。计费方案匹配要求：Base URL 必须与同一计费方案的 API Key 配套使用，否则会返回 401（来源#3）；API Key 与 Base URL 还必须属于同一地域，不能跨地域混用（来源#1、来源#3）。此外，以 `sk-sp-` 开头的套餐专属 API Key（Coding Plan / Token Plan 团队版）必须配合各自专属 Base URL，不可与通用 API Key/Base URL 混用（来源#5）。若使用新加坡等其他地域，需同时更换对应地域的 Base URL 和 API Key（来源#4）。

来源#1: qwen-api-key.md
来源#2: qwen-api-key.md
来源#3: qwen-base-url.md
来源#4: qwen-batch.md
来源#5: qwen-errors.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

## final · P-QW-3

Qwen北京的Base URL和API Key怎么配套，能否跨地域或计费方案混用？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 OpenAI 兼容 Base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#2、来源#3）。API Key 需在百炼控制台选择北京地域后获取；每个地域有独立的接入域名、API Key 和模型列表（来源#1）。

不能混用：Base URL 必须与同一计费方案的 API Key 配套，否则返回 401；各地域 API Key 相互独立、不能跨地域使用（来源#3）。例如北京 Key 配新加坡 Base URL 会因地域不匹配报错（来源#5）。Coding Plan、Token Plan 团队版等套餐的 `sk-sp-` 专属 Key 必须配各自专属 Base URL，不可与通用 Key/Base URL 混用（来源#5）。切换地域时需同时更换 API Key（来源#4）。

来源#1: qwen-api-key.md
来源#2: qwen-api-key.md
来源#3: qwen-base-url.md
来源#4: qwen-batch.md
来源#5: qwen-errors.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md

## final · P-QW-4

Qwen北京地域的API Key应配哪里的Base URL，还要匹配什么计费方案？

审阅：PASS；北京兼容地址、同地域同计费方案及套餐专属地址例外正确；未声称查询个人账户。

北京地域的 Qwen API Key 应配北京地域的 Base URL：OpenAI 兼容模式为 `https://dashscope.aliyuncs.com/compatible-mode/v1`（来源#3、来源#4）。Base URL 必须与同一计费方案的 API Key 配套使用，否则会报 401；各地域 API Key 相互独立，不能跨地域使用（来源#3）。若使用以 `sk-sp-` 开头的套餐专属 Key（Coding Plan / Token Plan 团队版），必须改用各自专属 Base URL，不能与通用 Key/Base URL 混用（来源#5）。

来源#1: qwen-api-key.md
来源#2: qwen-api-key.md
来源#3: qwen-base-url.md
来源#4: qwen-batch.md
来源#5: qwen-errors.md
来源#6: qwen-quickstart.md
来源#7: qwen-regions.md
