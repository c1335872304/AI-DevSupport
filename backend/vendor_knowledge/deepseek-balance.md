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
