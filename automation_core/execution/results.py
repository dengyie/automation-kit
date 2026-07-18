from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from automation_core.capabilities.models import CapabilityResult
from automation_core.drivers import ActionResult, ArtifactHandle
from automation_core.events import EventEnvelope
from automation_core.execution.context import ExecutionContext
from automation_core.execution.failures import ExecutionFailure


class StepKind(str, Enum):
    ACTION = "action"
    CAPABILITY = "capability"
    ARTIFACT = "artifact"


class StepStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _required_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


def _serialize_action_result(result: ActionResult) -> Dict[str, Any]:
    data = result.data
    if data is not None and not isinstance(data, (bool, int, float, str, list, dict, type(None))):
        data = f"<{type(data).__name__}>"
    return {
        "success": result.success,
        "message": result.message,
        "data": data,
    }


def _serialize_artifact(artifact: ArtifactHandle) -> Dict[str, Any]:
    return {
        "artifact_type": artifact.artifact_type,
        "path": str(artifact.path),
        "metadata": dict(artifact.metadata),
    }


@dataclass(frozen=True)
class StepExecutionResult:
    step_id: str
    step_name: str
    kind: Union[StepKind, str]
    status: Union[StepStatus, str]
    attempts: int
    duration_ms: int
    context: ExecutionContext
    action_result: Optional[ActionResult] = None
    capability_result: Optional[CapabilityResult] = None
    artifact_result: Optional[ArtifactHandle] = None
    error: Optional[ExecutionFailure] = None

    def __post_init__(self) -> None:
        kind = self.kind if isinstance(self.kind, StepKind) else StepKind(str(self.kind))
        status = (
            self.status if isinstance(self.status, StepStatus) else StepStatus(str(self.status))
        )
        if not isinstance(self.context, ExecutionContext):
            raise ValueError("context must be an ExecutionContext")
        if self.attempts < 0:
            raise ValueError("attempts must be non-negative")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")

        has_action = self.action_result is not None
        has_capability = self.capability_result is not None
        has_artifact = self.artifact_result is not None
        present = sum(1 for flag in (has_action, has_capability, has_artifact) if flag)
        if present != 1:
            raise ValueError(
                "step result requires exactly one of action_result, capability_result, or artifact_result"
            )
        if kind is StepKind.ACTION and not has_action:
            raise ValueError("action step requires action_result")
        if kind is StepKind.CAPABILITY and not has_capability:
            raise ValueError("capability step requires capability_result")
        if kind is StepKind.ARTIFACT and not has_artifact:
            raise ValueError("artifact step requires artifact_result")

        object.__setattr__(self, "step_id", _required_string(self.step_id, "step_id"))
        object.__setattr__(self, "step_name", _required_string(self.step_name, "step_name"))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "status", status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "kind": self.kind.value,
            "status": self.status.value,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
            "context": self.context.to_dict(),
            "action_result": (
                _serialize_action_result(self.action_result)
                if self.action_result is not None
                else None
            ),
            "capability_result": (
                self.capability_result.to_dict()
                if self.capability_result is not None
                else None
            ),
            "artifact_result": (
                _serialize_artifact(self.artifact_result)
                if self.artifact_result is not None
                else None
            ),
            "error": self.error.to_dict() if self.error is not None else None,
        }


@dataclass(frozen=True)
class WorkflowResult:
    context: ExecutionContext
    status: Union[WorkflowStatus, str]
    steps: Sequence[StepExecutionResult] = ()
    artifacts: Sequence[ArtifactHandle] = ()
    events: Sequence[Any] = field(default_factory=tuple)
    failure: Optional[ExecutionFailure] = None

    def __post_init__(self) -> None:
        if not isinstance(self.context, ExecutionContext):
            raise ValueError("context must be an ExecutionContext")
        status = (
            self.status
            if isinstance(self.status, WorkflowStatus)
            else WorkflowStatus(str(self.status))
        )
        steps = tuple(self.steps)
        artifacts = tuple(self.artifacts)
        events = tuple(self.events)

        has_failed_step = any(step.status is StepStatus.FAILED for step in steps)
        if status is WorkflowStatus.FAILED and self.failure is None and not has_failed_step:
            raise ValueError("failed workflow requires failure or failed step")

        object.__setattr__(self, "status", status)
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "events", events)

    @property
    def success(self) -> bool:
        return self.status is WorkflowStatus.SUCCEEDED

    @property
    def actions(self) -> Tuple[ActionResult, ...]:
        return tuple(
            step.action_result
            for step in self.steps
            if step.action_result is not None
        )

    @property
    def capabilities(self) -> Tuple[CapabilityResult, ...]:
        return tuple(
            step.capability_result
            for step in self.steps
            if step.capability_result is not None
        )

    def to_dict(self) -> Dict[str, Any]:
        serialized_events = []
        for event in self.events:
            if hasattr(event, "to_dict"):
                serialized_events.append(event.to_dict())
            elif isinstance(event, dict):
                serialized_events.append(dict(event))
            else:
                serialized_events.append({"value": str(event)})
        return {
            "context": self.context.to_dict(),
            "status": self.status.value,
            "success": self.success,
            "steps": [step.to_dict() for step in self.steps],
            "artifacts": [_serialize_artifact(item) for item in self.artifacts],
            "events": serialized_events,
            "failure": self.failure.to_dict() if self.failure is not None else None,
        }
