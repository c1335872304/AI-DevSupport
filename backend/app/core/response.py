from typing import Any


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    payload: dict[str, Any] = {"code": 200, "message": message}
    if data is not None:
        payload["data"] = data
    return payload


def fail(code: int, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **extra}
