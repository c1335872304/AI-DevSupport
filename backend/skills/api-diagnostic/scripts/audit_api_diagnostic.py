import json
import sys


def main():
    payload = json.load(sys.stdin)
    answer = str(payload.get("answer") or "")
    tool_results = payload.get("toolResults") or []
    verified_facts = [item for item in (payload.get("verifiedFacts") or []) if isinstance(item, dict)]
    entities = payload.get("entities") or {}
    blocking_warnings = []
    warnings = []
    lowered = answer.lower()
    if any(secret in lowered for secret in ("authorization: bearer", "完整 api key", "完整token")):
        blocking_warnings.append("answer_contains_credential")
    if "已确认" in answer and not tool_results:
        blocking_warnings.append("unverified_confirmation")

    # A code catalog explains a code; it never proves that this customer's
    # request returned that code.  Customer incident claims need a scoped log
    # record or a scoped aggregate observation.
    has_request_incident = any(
        item.get("tool") == "query_call_log" and item.get("found") and item.get("httpStatus") == 429
        for item in verified_facts
    )
    has_recent_observation = any(
        item.get("tool") == "query_recent_call_stats" and int(item.get("rateLimitedCount") or 0) > 0
        for item in verified_facts
    )
    has_rate_limit_definition = any(
        item.get("tool") == "query_error_code" and item.get("found") and item.get("code") == "RATE_LIMIT_EXCEEDED"
        for item in verified_facts
    )
    has_observed_rate_limit = has_request_incident or has_recent_observation
    personal_claim_markers = (
        "已核验", "已确认", "本次调用触发了限流", "本次或近期调用触发了限流",
        "该请求触发了限流", "该请求返回 http 429", "该请求返回http 429",
    )
    if not has_observed_rate_limit and any(marker in lowered for marker in personal_claim_markers):
        blocking_warnings.append("unsupported_personal_rate_limit_claim")
    has_diagnostic_anchor = any(str(entities.get(key) or "").strip() for key in ("request_id", "error_code", "http_status", "endpoint"))
    unanchored_tool_claim_markers = (
        "当前已确认的信息", "我查询了错误码", "没有找到与该错误码相关的记录",
    )
    if not has_diagnostic_anchor and any(marker in answer for marker in unanchored_tool_claim_markers):
        blocking_warnings.append("unsupported_unanchored_diagnostic_query_claim")

    rate_limit_coverage_warnings = []
    if has_observed_rate_limit:
        compact = answer.replace(" ", "")
        if "429" not in compact:
            rate_limit_coverage_warnings.append("missing_confirmed_429_fact")
        if "不能仅凭429推断月额度已经用尽" not in compact:
            rate_limit_coverage_warnings.append("missing_quota_boundary")
        for item in verified_facts:
            if item.get("tool") == "query_call_log" and not item.get("found"):
                request_id = str(item.get("requestId") or "").strip()
                if request_id and (request_id not in answer or "未查询到" not in answer):
                    rate_limit_coverage_warnings.append("missing_not_found_request_boundary")
            if item.get("tool") == "query_call_log" and item.get("found") and item.get("httpStatus") == 429:
                request_id = str(item.get("requestId") or "").strip()
                if request_id and request_id not in answer:
                    rate_limit_coverage_warnings.append("missing_request_id")
            if item.get("tool") == "query_recent_call_stats" and int(item.get("rateLimitedCount") or 0) > 0:
                for key in ("total", "rateLimitedCount"):
                    value = item.get(key)
                    if value is not None and str(value) not in answer:
                        rate_limit_coverage_warnings.append(f"missing_rate_limit_{key}")
    if rate_limit_coverage_warnings:
        warnings.append("answer_omits_verified_rate_limit_facts")
        warnings.extend(rate_limit_coverage_warnings)
    warnings = [*blocking_warnings, *warnings]
    print(json.dumps({"passed": not blocking_warnings, "warnings": warnings, "checks": {
        "readOnly": True,
        "rateLimitEvidenceSufficient": has_observed_rate_limit,
        "rateLimitIncidentObserved": has_request_incident,
        "rateLimitRecentObservation": has_recent_observation,
        "rateLimitDefinitionKnown": has_rate_limit_definition,
        "hasDiagnosticAnchor": has_diagnostic_anchor,
        "rateLimitFactsCovered": has_observed_rate_limit and not rate_limit_coverage_warnings,
    }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
