"""Conservative admission to a single-read documentation workflow."""

import re

from app.agent.question_scope import document_request
from app.knowledge.product_scope import named_products


def simple_document_question(question: str, history=None, entity_memory=None) -> bool:
    if history or entity_memory or len(named_products(question)) != 1:
        return False
    if len(question) > 400 or not document_request(question):
        return False
    # These requests need evidence collection, multi-turn state, semantic
    # interpretation or explicit risk policy, even if they mention API docs.
    if re.search(
        r"req_[\w-]+|request[ _-]?id|(?<!\d)[45]\d\d(?!\d)|报错|失败|故障|排查|诊断|复查|恢复|核验|核查|确认|"
        r"比较|对比|区别|差异|我的|我这个|账号|账户|组织|账单|费用|收费|免费|购买|配额|余额|未来|2099|"
        r"退款|退订|投诉|人工|合同|删除|重置|停用|开通|套餐|订阅|充值|扣费|订单|计费(?!方案)|"
        r"refund|reimburse|charge|account|invoice|quota|subscription|payment|purchase|upgrade|downgrade|"
        r"compare|diagnos|error|fail|recover|delete|reset|cancel|contract|human|rotate|revoke|broken|incident|issue",
        question,
        re.IGNORECASE,
    ):
        return False
    topic = re.search(
        r"json|schema|response_format|base\s*url|api\s*key|bearer|后台响应|流式|stream|embedding|向量",
        question,
        re.IGNORECASE,
    )
    purpose = re.search(
        r"如何|怎么|怎样|哪里|哪个|什么|应配|配置|设置|开启|用法|支持|how|configure|setup|parameter",
        question,
        re.IGNORECASE,
    )
    return bool(topic and purpose)


def usable_document_read(outcomes, question: str) -> bool:
    """A failed, empty, conflicting or unscoped read must use full planning."""
    product = named_products(question)
    if len(product) != 1:
        return False
    for call, result in outcomes:
        if call.name != "search_knowledge" or result.status != "SUCCESS":
            continue
        data = result.data
        if (
            not isinstance(data, dict)
            or data.get("status") != "OK"
            or any(data.get(k) for k in ("conflicts", "missingFields", "warnings"))
        ):
            continue
        rows = data.get("results") or []
        if rows and all(
            isinstance(row, dict)
            and row.get("product") == product[0]
            and row.get("citationId")
            and row.get("indexVersion")
            and row.get("fileMd5")
            and len(str(row.get("textContent") or "").strip()) >= 80
            for row in rows
        ):
            return True
    return False
