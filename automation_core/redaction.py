"""Single authoritative sensitive-key redaction implementation.

Every report, event, artifact metadata and capability payload boundary must
pass through :func:`redact` so the sensitive term list exists exactly once.
"""

from pathlib import Path
from typing import Any, Dict, List

SENSITIVE_KEY_TERMS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "x5sec",
    "x5secdata",
)

REDACTED = "[redacted]"


def _is_sensitive_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(term in lowered for term in SENSITIVE_KEY_TERMS)


def redact(value: Any) -> Any:
    """Return a recursively sanitized copy safe for public reports.

    Primitive values pass through; dict keys are matched against
    ``SENSITIVE_KEY_TERMS`` case-insensitively at every depth; paths become
    strings; objects exposing ``to_dict`` are unwrapped; anything else is
    replaced by a type placeholder so page/driver objects and raw bytes can
    never reach a report.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        safe: Dict[str, Any] = {}
        for key, nested in value.items():
            output_key = key if isinstance(key, str) else str(key)
            if _is_sensitive_key(output_key):
                safe[output_key] = REDACTED
            else:
                safe[output_key] = redact(nested)
        return safe
    if isinstance(value, (list, tuple)):
        safe_list: List[Any] = [redact(item) for item in value]
        return safe_list
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return redact(to_dict())
    return f"<{type(value).__name__}>"
