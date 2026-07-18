from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from automation_core.drivers import ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    ExecutionFailure,
    StepExecutionResult,
    WorkflowStatus,
)


_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "x5sec",
    "x5secdata",
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        safe = {}
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(term in lowered for term in _SENSITIVE_TERMS):
                safe[key] = "[redacted]"
            else:
                safe[key] = _redact(nested)
        return safe
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class ReportCollector:
    def __init__(self, context: ExecutionContext) -> None:
        self.context = context
        self._events: List[Dict[str, object]] = []
        self._event_ids = set()
        self._steps: List[StepExecutionResult] = []
        self._artifacts: List[ArtifactHandle] = []
        self._sequence = 0

    def record_event(self, event: Dict[str, object]) -> None:
        event_id = str(event.get("event_id") or uuid4().hex)
        if event_id in self._event_ids:
            return
        self._event_ids.add(event_id)
        self._sequence += 1
        payload = dict(event)
        payload["event_id"] = event_id
        payload["sequence"] = self._sequence
        payload["run_id"] = self.context.run_id
        if "task_id" not in payload:
            payload["task_id"] = self.context.task_id
        if "payload" in payload:
            payload["payload"] = _redact(payload["payload"])
        self._events.append(payload)

    def record_step(self, step: StepExecutionResult) -> None:
        self._steps.append(step)

    def attach_artifact(self, artifact: ArtifactHandle) -> None:
        self._artifacts.append(artifact)

    def finalize(
        self,
        *,
        status: WorkflowStatus,
        failure: Optional[ExecutionFailure] = None,
    ) -> Dict[str, object]:
        return {
            "schema_version": "2",
            "context": self.context.to_dict(),
            "status": status.value,
            "success": status is WorkflowStatus.SUCCEEDED,
            "steps": [step.to_dict() for step in self._steps],
            "events": list(self._events),
            "artifacts": [
                {
                    "artifact_type": artifact.artifact_type,
                    "path": str(artifact.path),
                    "metadata": _redact(dict(artifact.metadata)),
                }
                for artifact in self._artifacts
            ],
            "failure": failure.to_dict() if failure is not None else None,
            "providers": self._provider_summary(),
        }

    def _provider_summary(self) -> List[Dict[str, object]]:
        providers = []
        for step in self._steps:
            if step.capability_result is None:
                continue
            providers.append(
                {
                    "provider": step.capability_result.provider,
                    "step_id": step.step_id,
                    "success": step.capability_result.success,
                }
            )
        return providers
