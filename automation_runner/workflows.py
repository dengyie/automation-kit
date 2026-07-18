from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from automation_core.actions import (
    ActionBatch,
    ActionBatchResult,
    ActionExecutor,
    ActionRequest,
)
from automation_core.drivers import (
    ActionResult,
    ArtifactHandle,
    DriverSession,
    SessionInfo,
)
from automation_core.events import (
    ArtifactEvent,
    ErrorEvent,
    EventEnvelope,
    TaskEndEvent,
    TaskStartEvent,
)
from automation_core.tasks import TaskCancelledError
from automation_core.tasks.lifecycle import TaskState


from automation_runner.steps import WorkflowStep


@dataclass(frozen=True)
class WorkflowResult:
    session: SessionInfo
    success: bool
    actions: List[ActionResult]
    artifacts: List[ArtifactHandle]
    state: TaskState = TaskState.SUCCEEDED
    batch_result: Optional[ActionBatchResult] = None
    error: Optional[str] = None
    events: List[EventEnvelope] = field(default_factory=list)


def _format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _split_error(error: str) -> Tuple[str, str]:
    error_type, separator, message = error.partition(": ")
    if separator:
        return error_type, message
    return "Error", error


def _has_artifact_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    artifact: ArtifactHandle,
) -> bool:
    artifact_path = str(artifact.path)
    for event in events:
        if event.event_type != "artifact" or event.task_id != task_id:
            continue
        if event.payload.get("artifact_type") != artifact.artifact_type:
            continue
        if event.payload.get("path") == artifact_path:
            return True
    return False


def _has_task_start_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    task_name: str,
) -> bool:
    for event in events:
        if event.event_type != "task.start" or event.task_id != task_id:
            continue
        if event.payload.get("task_name") == task_name:
            return True
    return False


def _has_task_end_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    task_name: str,
    outcome: str,
) -> bool:
    for event in events:
        if event.event_type != "task.end" or event.task_id != task_id:
            continue
        if event.payload.get("task_name") != task_name:
            continue
        if event.payload.get("outcome") == outcome:
            return True
    return False


def run_workflow_steps(
    session: DriverSession,
    steps: List[WorkflowStep],
) -> WorkflowResult:
    actions = []
    artifacts = []
    skipped = []
    pending_actions = []
    ran_action_batch = False
    executor = ActionExecutor(session)

    def flush_actions() -> bool:
        nonlocal ran_action_batch
        if not pending_actions:
            return True
        ran_action_batch = True
        batch_result = executor.run_batch(ActionBatch(actions=list(pending_actions)))
        pending_actions.clear()
        actions.extend(batch_result.results)
        skipped.extend(batch_result.skipped)
        return batch_result.success

    def current_batch_result() -> Optional[ActionBatchResult]:
        if ran_action_batch:
            return ActionBatchResult(results=actions, skipped=skipped)
        return None

    try:
        session.start()
        for step in steps:
            if step.kind == "action":
                pending_actions.append(
                    ActionRequest(name=step.name, parameters=dict(step.parameters))
                )
                continue

            if step.kind != "artifact":
                if not flush_actions():
                    break
                return WorkflowResult(
                    session=session.info,
                    state=TaskState.FAILED,
                    success=False,
                    actions=actions,
                    artifacts=artifacts,
                    batch_result=current_batch_result(),
                    error=f"ValueError: unsupported workflow step kind: {step.kind}",
                )

            if not flush_actions():
                break
            try:
                artifact = session.capture_artifact(
                    step.name,
                    str(step.parameters["name"]),
                )
            except Exception as exc:
                return WorkflowResult(
                    session=session.info,
                    state=TaskState.FAILED,
                    success=False,
                    actions=actions,
                    artifacts=artifacts,
                    batch_result=current_batch_result(),
                    error=_format_error(exc),
                )
            artifacts.append(artifact)

        if not skipped:
            flush_actions()

        batch_result = current_batch_result()
        return WorkflowResult(
            session=session.info,
            state=(
                TaskState.SUCCEEDED
                if batch_result is None or batch_result.success
                else TaskState.FAILED
            ),
            success=(batch_result.success if batch_result is not None else True),
            actions=actions,
            artifacts=artifacts,
            batch_result=batch_result,
        )
    finally:
        session.stop()


@dataclass(frozen=True)
class ManagedWorkflow:
    name: str
    session_factory: Callable[[], DriverSession]
    run_fn: Callable[[DriverSession], WorkflowResult]

    def run(self) -> WorkflowResult:
        session = self.session_factory()
        outcome = "succeeded"
        events = []
        try:
            result = self.run_fn(session)
            events.extend(result.events)
            if not _has_task_start_event(
                result.events,
                task_id=session.info.identifier,
                task_name=self.name,
            ):
                events.insert(
                    0,
                    TaskStartEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                    ).to_envelope(),
                )
            for artifact in result.artifacts:
                if _has_artifact_event(
                    result.events,
                    task_id=session.info.identifier,
                    artifact=artifact,
                ):
                    continue
                events.append(
                    ArtifactEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        artifact_type=artifact.artifact_type,
                        path=str(artifact.path),
                    ).to_envelope()
                )
            has_error_event = any(
                event.event_type == "error" for event in result.events
            )
            if result.error is not None and not has_error_event:
                error_type, message = _split_error(result.error)
                events.append(
                    ErrorEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        message=message,
                        error_type=error_type,
                    ).to_envelope()
                )
            if result.state == TaskState.CANCELLED:
                outcome = "cancelled"
            else:
                outcome = "succeeded" if result.success else "failed"
            if not _has_task_end_event(
                result.events,
                task_id=session.info.identifier,
                task_name=self.name,
                outcome=outcome,
            ):
                events.append(
                    TaskEndEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        outcome=outcome,
                    ).to_envelope()
                )
            return WorkflowResult(
                session=result.session,
                state=result.state,
                success=result.success,
                actions=result.actions,
                artifacts=result.artifacts,
                batch_result=result.batch_result,
                error=result.error,
                events=events,
            )
        except TaskCancelledError:
            events = [
                TaskStartEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                ).to_envelope()
            ]
            events.append(
                TaskEndEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                    outcome="cancelled",
                ).to_envelope()
            )
            return WorkflowResult(
                session=session.info,
                state=TaskState.CANCELLED,
                success=False,
                actions=[],
                artifacts=[],
                batch_result=None,
                error=None,
                events=events,
            )
        except Exception as exc:
            events = [
                TaskStartEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                ).to_envelope()
            ]
            events.append(
                ErrorEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                    message=str(exc),
                    error_type=type(exc).__name__,
                ).to_envelope()
            )
            events.append(
                TaskEndEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                    outcome="failed",
                ).to_envelope()
            )
            return WorkflowResult(
                session=session.info,
                state=TaskState.FAILED,
                success=False,
                actions=[],
                artifacts=[],
                batch_result=None,
                error=_format_error(exc),
                events=events,
            )


# Legacy aliases kept for built-in examples and older tests.
ExampleWorkflow = ManagedWorkflow
ExampleWorkflowResult = WorkflowResult

__all__ = [
    "ManagedWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "run_workflow_steps",
    "ExampleWorkflow",
    "ExampleWorkflowResult",
]
