from __future__ import annotations

import re
from datetime import date
from typing import Any


SCALAR_FIELDS = {
    "category": "knowledge_category",
    "product": "knowledge_product",
    "region": "knowledge_region",
    "channel": "knowledge_channel",
    "version": "knowledge_version",
    "error_code": "knowledge_error_code",
    "plan": "knowledge_plan",
    "superseded_by": "knowledge_superseded_by",
}

ES_FIELD_MAP = {
    "category": "category",
    "product": "product",
    "region": "region",
    "channel": "channel",
    "version": "knowledgeVersion",
    "error_code": "errorCode",
    "plan": "plan",
    "superseded_by": "supersededBy",
}

TEXT_FALLBACK_FIELDS = {"error_code", "plan"}


def metadata_matches(value: str | None, expected: str | list[str], field: str, text: str) -> bool:
    values = expected if isinstance(expected, list) else [expected]
    if value:
        return value in values
    if field not in TEXT_FALLBACK_FIELDS:
        return False
    return any(
        re.search(rf"(?<![a-zA-Z0-9_]){re.escape(term)}(?![a-zA-Z0-9_])", text, flags=re.IGNORECASE)
        for term in values
    )


def clean_scalar(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:255] if text else None


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def normalize_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    output: dict[str, Any] = {}
    aliases = {
        "knowledge_category": "category", "knowledgeCategory": "category",
        "knowledge_product": "product", "knowledgeProduct": "product",
        "knowledge_region": "region", "knowledgeRegion": "region",
        "knowledge_channel": "channel", "knowledgeChannel": "channel",
        "knowledge_version": "version", "knowledgeVersion": "version",
        "knowledge_error_code": "error_code", "errorCode": "error_code",
        "knowledge_plan": "plan", "knowledgePlan": "plan",
        "effectiveDate": "effective_date", "effectiveUntil": "effective_until", "effective_at": "effective_at",
    }
    normalized_input: dict[str, Any] = {}
    for key, value in raw.items():
        normalized_input[aliases.get(str(key), str(key))] = value
    for key in SCALAR_FIELDS:
        value = normalized_input.get(key)
        if isinstance(value, list):
            values = [clean_scalar(item) for item in value]
            values = [item for item in values if item]
            if values:
                output[key] = values
        else:
            cleaned = clean_scalar(value)
            if cleaned:
                output[key] = cleaned
    if normalized_input.get("effective_date") not in (None, ""):
        output["effective_date"] = parse_date(normalized_input["effective_date"])
    if normalized_input.get("effective_at") not in (None, ""):
        output["effective_at"] = parse_date(normalized_input["effective_at"])
    if normalized_input.get("effective_until") not in (None, ""):
        output["effective_until"] = parse_date(normalized_input["effective_until"])
    if output.get("effective_date") and output.get("effective_until") and output["effective_until"] <= output["effective_date"]:
        raise ValueError("effective_until must be later than effective_date")
    return output


def file_metadata(file) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for public_name, column_name in SCALAR_FIELDS.items():
        value = getattr(file, column_name, None)
        if value:
            output[public_name] = value
    effective = getattr(file, "knowledge_effective_date", None)
    if effective:
        output["effective_date"] = effective.isoformat()
    until = getattr(file, "knowledge_effective_until", None)
    if until:
        output["effective_until"] = until.isoformat()
    return output


def es_metadata(file) -> dict[str, Any]:
    metadata = file_metadata(file)
    output: dict[str, Any] = {}
    for public_name, es_name in ES_FIELD_MAP.items():
        if public_name in metadata:
            output[es_name] = metadata[public_name]
    if metadata.get("effective_date"):
        output["effectiveDate"] = metadata["effective_date"]
    if metadata.get("effective_until"):
        output["effectiveUntil"] = metadata["effective_until"]
    return output


def apply_metadata_to_file(file, raw: dict[str, Any] | None) -> None:
    # Partial-update semantics are important for chunked uploads: a later chunk that omits
    # metadata must not erase metadata captured on the first chunk. Explicit non-empty
    # values update the document; a dedicated admin migration can clear fields if needed.
    metadata = normalize_metadata(raw)
    for public_name, column_name in SCALAR_FIELDS.items():
        if public_name not in metadata:
            continue
        value = metadata[public_name]
        if isinstance(value, list):
            value = value[0] if value else None
        setattr(file, column_name, value)
    if "effective_date" in metadata:
        file.knowledge_effective_date = metadata["effective_date"]
    if "effective_until" in metadata:
        file.knowledge_effective_until = metadata["effective_until"]


def stage_metadata(file, raw):
    """Do not relabel an active revision before its replacement is published."""
    import json
    desired = json.loads(file.desired_metadata_json) if file.desired_metadata_json else file_metadata(file)
    desired.update(normalize_metadata(raw))
    # Validate a combined range, including dates carried over from the old snapshot.
    normalize_metadata(desired)
    file.desired_metadata_json = json.dumps(desired, ensure_ascii=False, default=str)


def metadata_filter_schema() -> dict[str, Any]:
    string_or_array = lambda description: {
        "oneOf": [
            {"type": "string", "minLength": 1, "maxLength": 255},
            {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 255}, "minItems": 1, "maxItems": 10},
        ],
        "description": description,
    }
    return {
        "type": "object",
        "properties": {
            "category": string_or_array("Knowledge category such as authentication, rate_limit, billing, refund."),
            "product": string_or_array("Product or service name."),
            "region": string_or_array("Region such as CN, APAC, GLOBAL."),
            "channel": string_or_array("Knowledge channel such as api, billing, web, mobile."),
            "version": string_or_array("Knowledge/policy version."),
            "error_code": string_or_array("Exact platform error code. When untagged, the passage must mention the code."),
            "plan": string_or_array("Plan/tier such as Professional. An untagged passage mention does not establish applicability."),
            "effective_at": {"type": "string", "format": "date", "description": "Only use knowledge effective on or before this YYYY-MM-DD date."},
        },
        "additionalProperties": False,
    }
