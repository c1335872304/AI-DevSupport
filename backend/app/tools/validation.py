from __future__ import annotations

from typing import Any


class ToolValidationError(ValueError):
    pass


def validate_json_schema(value: Any, schema: dict[str, Any], path: str = "arguments") -> None:
    """Enforce tool arguments against JSON Schema at the runtime boundary.

    ``jsonschema`` is used when installed so dynamically discovered MCP schemas can use
    modern constructs such as anyOf/oneOf.  A strict dependency-free subset remains as a
    fallback for minimal development environments. Tool schemas are therefore a security
    boundary, not merely prompting hints.
    """
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        return _validate_subset(value, schema, path)
    try:
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    except SchemaError as exc:
        raise ToolValidationError(f"Invalid tool schema: {exc.message}") from exc
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path)
    where = f"{path}.{location}" if location else path
    raise ToolValidationError(f"{where}: {error.message}")


def _validate_subset(value: Any, schema: dict[str, Any], path: str = "arguments") -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ToolValidationError(f"{path} must be an object")
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                raise ToolValidationError(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ToolValidationError(f"{path} contains unsupported fields: {', '.join(unknown)}")
        for key, item in value.items():
            child = properties.get(key)
            if child:
                _validate_subset(item, child, f"{path}.{key}")
        return
    if expected == "array":
        if not isinstance(value, list):
            raise ToolValidationError(f"{path} must be an array")
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            raise ToolValidationError(f"{path} requires at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            raise ToolValidationError(f"{path} allows at most {schema['maxItems']} items")
        child = schema.get("items")
        if child:
            for index, item in enumerate(value):
                _validate_subset(item, child, f"{path}[{index}]")
        return
    if expected == "string":
        if not isinstance(value, str):
            raise ToolValidationError(f"{path} must be a string")
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise ToolValidationError(f"{path} is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            raise ToolValidationError(f"{path} is longer than {schema['maxLength']}")
    elif expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolValidationError(f"{path} must be an integer")
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolValidationError(f"{path} must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolValidationError(f"{path} must be <= {schema['maximum']}")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolValidationError(f"{path} must be a number")
    elif expected == "boolean":
        if not isinstance(value, bool):
            raise ToolValidationError(f"{path} must be a boolean")
    elif expected == "null" and value is not None:
        raise ToolValidationError(f"{path} must be null")

    if "enum" in schema and value not in schema["enum"]:
        raise ToolValidationError(f"{path} must be one of {schema['enum']}")
