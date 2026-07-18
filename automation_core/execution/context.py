from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


_RESERVED_IDENTITY_KEYS = {
    "run_id",
    "task_id",
    "workflow_name",
    "correlation_id",
    "deadline",
}
_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "x5sec",
    "x5secdata",
)


def _required_string(value: Optional[str], name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


def _optional_string(value: Optional[str], name: str) -> Optional[str]:
    if value is None:
        return None
    return _required_string(value, name)


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        safe = {}
        for key, nested in value.items():
            output_key = str(key)
            lowered = output_key.lower()
            if any(term in lowered for term in _SENSITIVE_TERMS):
                safe[output_key] = "[redacted]"
            else:
                safe[output_key] = _safe_value(nested)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _safe_value(to_dict())
    return f"<{type(value).__name__}>"


@dataclass(frozen=True)
class ExecutionContext:
    run_id: str
    task_id: Optional[str]
    workflow_name: str
    correlation_id: Optional[str] = None
    deadline: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        run_id = _required_string(self.run_id, "run_id")
        workflow_name = _required_string(self.workflow_name, "workflow_name")
        task_id = _optional_string(self.task_id, "task_id")
        correlation_id = _optional_string(self.correlation_id, "correlation_id")
        if self.deadline is not None and not isinstance(self.deadline, (int, float)):
            raise ValueError("deadline must be a number or None")

        metadata = dict(self.metadata)
        reserved = sorted(_RESERVED_IDENTITY_KEYS.intersection(metadata))
        if reserved:
            raise ValueError(
                f"metadata cannot override reserved identity fields: {', '.join(reserved)}"
            )

        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "workflow_name", workflow_name)
        object.__setattr__(self, "correlation_id", correlation_id)
        object.__setattr__(self, "deadline", float(self.deadline) if self.deadline is not None else None)
        object.__setattr__(self, "metadata", metadata)

    def for_step(self, task_id: str) -> "ExecutionContext":
        step_id = _required_string(task_id, "task_id")
        return ExecutionContext(
            run_id=self.run_id,
            task_id=step_id,
            workflow_name=self.workflow_name,
            correlation_id=self.correlation_id,
            deadline=self.deadline,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "workflow_name": self.workflow_name,
            "correlation_id": self.correlation_id,
            "deadline": self.deadline,
            "metadata": _safe_value(self.metadata),
        }
