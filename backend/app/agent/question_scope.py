"""Separate documentation questions from customer incident verification."""

import re

from app.knowledge.product_scope import named_products


def asks_about_personal_state(question: str) -> bool:
    return bool(re.search(
        r"(?:我(?:的|这个|这次|本次|刚才|当前)|本人(?:的)?|my\s+|my\s+current\s+)"
        r".{0,20}(?:账号|账户|会话|请求|接口|调用|上限|版本|配额|账单|套餐|[45]\d\d|"
        r"account|session|request|quota|invoice|plan)",
        question,
        re.IGNORECASE,
    ))


def document_request(question: str, entities: dict | None = None) -> bool:
    text = question.lower()
    entities = entities or {}
    # Actual incident identifiers and explicit failed calls retain the diagnostic
    # path. Numbers in technical limits (256 dimensions, 512 tokens) are not HTTP evidence.
    if entities.get("request_id") or re.search(
        r"返回\s*[45]\d\d|报错|调用失败|请求失败|一直\s*[45]\d\d", text
    ):
        return False
    return bool(
        named_products(question)
        or re.search(r"文档|规范|json|schema|结构化输出|向量|embedding|参数|前缀续写|后台响应", text)
        or re.search(
            r"(?:公开|官方)(?:说明|含义|定义)"
            r"|(?:认证|鉴权|环境变量).{0,12}(?:配置|设置)\s*(?:方式|方法|是什么|怎么)"
            r"|(?:单批|单次|每批).{0,16}(?:限制|上限)"
            r"|\b[45]\d\d\b.{0,12}(?:是否总|总是|一定)",
            text,
        )
    )


def vendor_clarification(question: str) -> str:
    text = question.lower()
    if (
        not named_products(question)
        and re.search(r"json|schema|结构化|strict", text)
        and re.search(r"参数|设置|配置|保证|一定", text)
    ):
        return "请先确认使用的厂商（DeepSeek、Qwen 或 OpenAI）、模型和接口类型；JSON/Schema 模式及 strict 参数的支持范围不同，不能给出适用于所有 API 的配置保证。"
    return ""
