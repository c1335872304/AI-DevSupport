"""Versioned Demo API decision rules. Vendor documentation is not account evidence."""

import math

SERVICE_ID = "demo-api"
RULE_VERSION = "2026-10-v1"
SAFE_OBSERVATIONS = {
    "authPresent",
    "authSchemeValid",
    "keyStateAtCall",
    "keyAppIdAtCall",
    "limiterKind",
    "rateObserved",
    "rateLimit",
    "concurrencyObserved",
    "concurrencyLimit",
    "quotaRemaining",
}
CAUSES = {
    "AUTH_MISSING": (401, "缺少认证", "为请求配置认证头；不要提供完整 Key 或认证头"),
    "AUTH_FORMAT": (401, "认证格式错误", "按 Demo API 的 Bearer 格式检查认证头，保留密钥在本地"),
    "KEY_INVALID": (401, "Key 无效或已撤销", "在本地检查 Key 是否有效；需要权限时由拥有者更换凭据"),
    "KEY_EXPIRED": (401, "Key 在请求时已过期", "由拥有者检查有效期并配置有效凭据，随后发送新请求"),
    "APP_MISMATCH": (401, "Key 与应用不匹配", "核对目标应用及其凭据，勿跨应用复用 Key"),
    "RATE_LIMIT": (429, "请求频率限制", "降低发送频率，按服务规则使用指数退避与随机抖动"),
    "CONCURRENCY_LIMIT": (429, "并发限制", "降低同时在途请求数，并为客户端增加有界队列"),
    "QUOTA_LIMIT": (429, "配额限制", "由拥有者核对该服务配额；助手不自动变更套餐或额度"),
}


def _evaluate(code, obs, app_id):
    auth, scheme, state = obs.get("authPresent"), obs.get("authSchemeValid"), obs.get("keyStateAtCall")
    if code == "AUTH_MISSING":
        return None if type(auth) is not bool else auth is False
    if code in {"AUTH_FORMAT", "KEY_INVALID", "KEY_EXPIRED", "APP_MISMATCH"}:
        if auth is False:
            return False
        if auth is not True:
            return None
        if code == "AUTH_FORMAT":
            return None if type(scheme) is not bool else scheme is False
        if scheme is False:
            return False
        if scheme is not True or state is None:
            return None
        if state not in {"ACTIVE", "INVALID", "REVOKED", "EXPIRED"}:
            return None
        if code == "KEY_INVALID":
            return state in {"INVALID", "REVOKED"}
        if state in {"INVALID", "REVOKED"}:
            return False
        if code == "KEY_EXPIRED":
            return state == "EXPIRED"
        if state == "EXPIRED":
            return False
        if state != "ACTIVE":
            return None
        return None if not obs.get("keyAppIdAtCall") else obs["keyAppIdAtCall"] != app_id
    kind = obs.get("limiterKind")
    if kind not in {"RATE", "CONCURRENCY", "QUOTA"}:
        return None
    if kind == "QUOTA":
        number = obs.get("quotaRemaining")
        consistent = type(number) in {int, float} and math.isfinite(number) and number <= 0
    else:
        prefix = "rate" if kind == "RATE" else "concurrency"
        observed, limit = obs.get(prefix + "Observed"), obs.get(prefix + "Limit")
        consistent = (
            type(observed) in {int, float}
            and type(limit) in {int, float}
            and math.isfinite(observed)
            and math.isfinite(limit)
            and limit >= 0
            and observed > limit
        )
    if not consistent:
        return None
    return code == {"RATE": "RATE_LIMIT", "CONCURRENCY": "CONCURRENCY_LIMIT", "QUOTA": "QUOTA_LIMIT"}[kind]


def analyze(records, *, request_id, app_id=None, endpoint=None):
    """Only matching, versioned at-call observations support a cause."""
    log = next(
        (
            e
            for e in reversed(records)
            if e.get("tool") == "query_call_log"
            and e.get("verified")
            and e.get("requestId") == request_id
            and (e.get("facts") or [{}])[0].get("found")
        ),
        None,
    )
    observation = next(
        (
            e
            for e in reversed(records)
            if e.get("tool") == "query_request_observation"
            and e.get("verified")
            and e.get("requestId") == request_id
        ),
        None,
    )
    status = (log.get("facts") or [{}])[0].get("httpStatus") if log else None
    fact = (observation.get("facts") or [{}])[0] if observation else {}
    trusted = bool(
        log
        and observation
        and fact.get("serviceId") == SERVICE_ID
        and fact.get("ruleVersion") == RULE_VERSION
        and observation.get("appId") == log.get("appId")
        and observation.get("eventAt") == log.get("eventAt")
        and (not app_id or app_id == log.get("appId"))
    )
    candidates, actions = [], []
    for code, (expected, title, action) in CAUSES.items():
        if status not in {401, 429} or expected != status:
            continue
        answer = _evaluate(code, fact.get("observations") or {}, log.get("appId")) if trusted else None
        ids = [e["evidenceId"] for e in (log, observation) if e]
        state = "SUPPORTED" if answer is True else "EXCLUDED" if answer is False else "UNDETERMINED"
        candidates.append(
            {
                "cause": code,
                "title": title,
                "status": state,
                "supportingEvidenceIds": ids if answer is True else [],
                "opposingEvidenceIds": ids if answer is False else [],
                "missing": [] if answer is not None else ["matching_versioned_at_call_observation"],
                "eventAt": log.get("eventAt") if log else None,
                "serviceId": SERVICE_ID,
                "ruleVersion": RULE_VERSION,
            }
        )
        if answer is True:
            actions.append(
                {
                    "cause": code,
                    "instruction": action,
                    "evidenceIds": ids,
                    "recheck": "执行修正后提供同一应用、接口的新 request_id",
                }
            )
    code_map = {
        "AUTH_MISSING": "AUTH_MISSING",
        "AUTH_FORMAT_INVALID": "AUTH_FORMAT",
        "AUTH_KEY_INVALID": "KEY_INVALID",
        "AUTH_KEY_EXPIRED": "KEY_EXPIRED",
        "AUTH_APP_MISMATCH": "APP_MISMATCH",
        "RATE_LIMIT_EXCEEDED": "RATE_LIMIT",
        "CONCURRENCY_LIMIT_EXCEEDED": "CONCURRENCY_LIMIT",
        "QUOTA_EXCEEDED": "QUOTA_LIMIT",
    }
    error = (log.get("facts") or [{}])[0].get("errorCode") if log else None
    conflict = error in code_map and any(
        c["status"] == "SUPPORTED" and c["cause"] != code_map[error] for c in candidates
    )
    if conflict:
        for candidate in candidates:
            candidate.update(status="UNDETERMINED", missing=["instrumentation_error_code_conflict"])
        actions = []
    return {
        "serviceId": SERVICE_ID,
        "ruleVersion": RULE_VERSION,
        "requestId": request_id,
        "appId": log.get("appId") if log else app_id,
        "endpoint": endpoint,
        "candidates": candidates,
        "actions": actions,
        "causeConfirmed": any(c["status"] == "SUPPORTED" for c in candidates),
        "missing": ["instrumentation_error_code_conflict"]
        if conflict
        else []
        if trusted
        else ["versioned_request_observation"],
        "scope": "historical_request_only",
    }
