import json, sys
p=json.load(sys.stdin); t=str(p.get("text") or p.get("question") or "").lower()
rows=[
 ("api_auth",["401","api key","auth_key","鉴权","密钥"]),
 ("api_rate_limit",["429","rate_limit","限流","qps","quota"]),
 ("api_request",["request_id","request id","接口报错","错误码"]),
 ("auth",["登录","密码","验证码","token","login","auth"]),
 ("network",["网络","连接","timeout","超时","connection"]),
 ("upload",["上传","文件","upload"]),
 ("payment",["支付","扣费","付款","payment","charged"]),
 ("client",["页面","浏览器","客户端","app","browser"]),
 ("server",["500","服务异常","server error"]),
]
category="unknown"
for n,ws in rows:
    if any(w in t for w in ws): category=n; break
print(json.dumps({"category":category,"hasErrorCode":any(ch.isdigit() for ch in t),"needsKnowledgeSearch":category not in {"api_auth","api_rate_limit","api_request"},"apiDiagnostic":category.startswith("api_")}, ensure_ascii=False))
