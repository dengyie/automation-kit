from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from automation_core.drivers import ArtifactHandle
from automation_core.events import EventEnvelope


_CAPABILITY_NAME = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_OPERATION_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "x5sec",
    "x5secdata",
)


def _required_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


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
class CapabilityManifest:
    name: str
    version: str
    operations: Tuple[str, ...]
    platforms: Tuple[str, ...] = ()
    default_cancellation: str = "cooperative"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        name = _required_string(self.name, "name")
        if not _CAPABILITY_NAME.fullmatch(name):
            raise ValueError("name must use lowercase dotted capability syntax")
        version = _required_string(self.version, "version")
        operations = tuple(self.operations)
        if not operations:
            raise ValueError("operations must contain at least one operation")
        for operation in operations:
            if not isinstance(operation, str) or not _OPERATION_NAME.fullmatch(operation):
                raise ValueError("operations must use lowercase snake_case names")
        platforms = tuple(self.platforms)
        for platform in platforms:
            _required_string(platform, "platform")

        cancellation = _required_string(self.default_cancellation, "default_cancellation")
        if cancellation not in {"cooperative", "unsupported"}:
            raise ValueError("default_cancellation must be cooperative or unsupported")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "operations", operations)
        object.__setattr__(self, "platforms", platforms)
        object.__setattr__(self, "default_cancellation", cancellation)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def supports(self, operation: str, platform: Optional[str] = None) -> bool:
        if operation not in self.operations:
            return False
        return platform is None or not self.platforms or platform in self.platforms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "operations": list(self.operations),
            "platforms": list(self.platforms),
            "default_cancellation": self.default_cancellation,
            "metadata": _safe_value(self.metadata),
        }


@dataclass(frozen=True)
class CapabilityExecutionProfile:
    cancellation: str = "cooperative"
    blocking: bool = False

    def __post_init__(self) -> None:
        cancellation = _required_string(self.cancellation, "cancellation")
        if cancellation not in {"cooperative", "unsupported"}:
            raise ValueError("cancellation must be cooperative or unsupported")
        object.__setattr__(self, "cancellation", cancellation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cancellation": self.cancellation,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class CapabilityRequest:
    capability: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        capability = _required_string(self.capability, "capability")
        operation = _required_string(self.operation, "operation")
        if not _CAPABILITY_NAME.fullmatch(capability):
            raise ValueError("capability must use lowercase dotted capability syntax")
        if not _OPERATION_NAME.fullmatch(operation):
            raise ValueError("operation must use lowercase snake_case syntax")
        object.__setattr__(self, "capability", capability)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "parameters", dict(self.parameters))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "operation": self.operation,
            "parameters": _safe_value(self.parameters),
            "metadata": _safe_value(self.metadata),
        }


@dataclass(frozen=True)
class CapabilityResult:
    success: bool
    provider: str
    data: Optional[Any] = None
    error_code: Optional[str] = None
    retryable: bool = False
    artifacts: List[ArtifactHandle] = field(default_factory=list)
    events: List[EventEnvelope] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = _required_string(self.provider, "provider")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "artifacts", list(self.artifacts))
        object.__setattr__(self, "events", list(self.events))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> Dict[str, Any]:
        artifacts = [
            {
                "artifact_type": artifact.artifact_type,
                "path": str(artifact.path),
                "metadata": _safe_value(artifact.metadata),
            }
            for artifact in self.artifacts
        ]
        return {
            "success": self.success,
            "provider": self.provider,
            "data": _safe_value(self.data),
            "error_code": self.error_code,
            "retryable": self.retryable,
            "artifacts": artifacts,
            "events": [_safe_value(event) for event in self.events],
            "metadata": _safe_value(self.metadata),
        }
