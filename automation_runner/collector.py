from typing import Any, Dict, List
from uuid import uuid4

from automation_core.drivers import ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    StepExecutionResult,
    WorkflowStatus,
)
from automation_core.redaction import redact


class ReportCollector:
    """Append-only, runtime-owned recorder for workflow lifecycle evidence.

    Events are deduplicated by ``event_id`` and receive a monotonic
    ``sequence`` plus the run identity of the owning context. The collector
    is the single writer of report events, steps and artifacts.
    """

    def __init__(self, context: ExecutionContext) -> None:
        self.context = context
        self._events: List[Dict[str, Any]] = []
        self._event_ids = set()
        self._steps: List[StepExecutionResult] = []
        self._artifacts: List[ArtifactHandle] = []
        self._sequence = 0

    def record_event(self, event: Dict[str, Any]) -> None:
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
            payload["payload"] = redact(payload["payload"])
        self._events.append(payload)

    def record_step(self, step: StepExecutionResult) -> None:
        self._steps.append(step)

    def attach_artifact(self, artifact: ArtifactHandle) -> None:
        self._artifacts.append(artifact)

    def steps(self) -> List[StepExecutionResult]:
        return list(self._steps)

    def artifacts(self) -> List[ArtifactHandle]:
        return list(self._artifacts)

    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def finalize(
        self,
        *,
        status: WorkflowStatus,
        failure: Optional[ExecutionFailure] = None,
    ) -> Dict[str, Any]:
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
                    "metadata": redact(dict(artifact.metadata)),
                }
                for artifact in self._artifacts
            ],
            "failure": failure.to_dict() if failure is not None else None,
            "providers": self._provider_summary(),
        }

    def _provider_summary(self) -> List[Dict[str, Any]]:
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
