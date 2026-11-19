"""Resolve named API vendors without expanding explicit caller constraints."""

import re

from app.knowledge.metadata import normalize_metadata

_VENDORS = (
    ("OpenAI API", r"(?<![a-z0-9_])(?:openai|gpt)(?![a-z0-9_])"),
    ("Qwen API", r"(?<![a-z0-9_])qwen(?:\d[\w-]*)?(?![a-z0-9_])|通义千问|千问|百炼"),
    ("DeepSeek API", r"(?<![a-z0-9_])deepseek(?![a-z0-9_])|深度求索"),
)


class ProductScopeConflict(ValueError):
    pass


def named_products(query):
    products = [product for product, pattern in _VENDORS if re.search(pattern, query, re.IGNORECASE)]
    if (
        "OpenAI API" in products
        and len(products) > 1
        and not re.search(r"比较|对比|区别|分别|\b(?:versus|vs|compare)\b", query, re.IGNORECASE)
    ):
        # OpenAI-compatible protocols / SDKs do not change a Qwen or DeepSeek
        # endpoint into an OpenAI-hosted service. Keep genuine comparisons.
        service_mentions = re.sub(
            r"openai[\s-]*(?:(?:兼容|compatible)|(?:(?:python|node(?:\.js)?)\s*)?sdk)",
            "",
            query,
            flags=re.IGNORECASE,
        )
        if not re.search(_VENDORS[0][1], service_mentions, re.IGNORECASE):
            products.remove("OpenAI API")
    return products


def scoped_filters(query, filters=None):
    result = normalize_metadata(filters)
    named = named_products(query)
    if not named:
        return result
    explicit = result.get("product")
    allowed = [explicit] if isinstance(explicit, str) else explicit
    products = [p for p in named if not allowed or p in allowed]
    if not products:
        raise ProductScopeConflict("Named vendor conflicts with product filter")
    result["product"] = products[0] if len(products) == 1 else products
    return result
