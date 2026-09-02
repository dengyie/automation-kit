from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Union

from automation_core.redaction import redact


class FailureCategory(str, Enum):
    REGISTRATION = "registration"
    RESOLUTION = "resolution"
    CONFIG = "config"
    PROVIDER = "provider"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    BUSINESS = "business"
    CLEANUP = "cleanup"


def _required_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


@dataclass(frozen=True)
class ExecutionFailure:
    category: Union[FailureCategory, str]
    code: str
    message: str
    retryable: bool
    source: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.category, FailureCategory):
            category = self.category
        else:
            try:
                category = FailureCategory(str(self.category))
            except ValueError as exc:
                raise ValueError("category must be a known failure category") from exc

        object.__setattr__(self, "category", category)
        object.__setattr__(self, "code", _required_string(self.code, "code"))
        object.__setattr__(self, "message", _required_string(self.message, "message"))
        object.__setattr__(self, "source", _required_string(self.source, "source"))
        object.__setattr__(self, "details", dict(self.details))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "source": self.source,
            "details": redact(self.details),
        }
