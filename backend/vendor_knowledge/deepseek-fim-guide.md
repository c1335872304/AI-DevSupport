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
