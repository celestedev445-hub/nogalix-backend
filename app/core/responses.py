from typing import Any, Optional


def ok(
    data: Any = None,
    message: Optional[str] = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return payload


def fail(
    message: str,
    *,
    code: Optional[str] = None,
    errors: Optional[dict[str, Any]] = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": message}
    if code:
        payload["code"] = code
    if errors:
        payload["errors"] = errors
    payload.update(extra)
    return payload
