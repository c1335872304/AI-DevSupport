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
