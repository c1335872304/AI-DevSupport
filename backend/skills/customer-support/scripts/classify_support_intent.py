import json, sys
p=json.load(sys.stdin)
q=str(p.get("question") or "").lower()
classes=[
 ("api_diagnostic", ["request_id","request id","api key","401","429","qps","限流","接口报错","错误码"]),
 ("billing", ["扣费","支付","付款","账单","费用","用量","调用量","配额","套餐","billing","invoice","usage","quota"]),
 ("refund", ["退款","退钱","refund"]),
 ("account", ["账户","账号","登录","密码","account","login"]),
 ("order", ["订单","发货","物流","order","shipping","delivery"]),
 ("subscription", ["会员","订阅","subscription","membership"]),
 ("how_to", ["怎么用","如何使用","怎么操作","how to"]),
]
category="general"
for name, words in classes:
    if any(w in q for w in words): category=name; break
private_terms=["我的订单","我的退款","我的付款","我的账户","我的账号","我的余额","我的账单","我的用量","我的套餐","是否到账","有没有到账"]
explicit_handoff=any(w in q for w in ["人工客服","转人工","人工处理","投诉","human agent","representative","escalate"])
troubleshooting=category=="api_diagnostic" or any(w in q for w in ["报错","失败","打不开","不能用","无法","收不到","卡住","error","failed","not working","can't","cannot"])
print(json.dumps({"category":category,"requiresPrivateData":any(w in q for w in private_terms),"explicitHandoff":explicit_handoff,"likelyTroubleshooting":troubleshooting}, ensure_ascii=False))
