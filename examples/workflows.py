from dataclasses import dataclass, field
from typing import Callable, List, Optional

from automation_core.drivers import (
    ActionResult,
    ArtifactHandle,
    DriverSession,
    SessionInfo,
)
from automation_core.events import ArtifactEvent, ErrorEvent, EventEnvelope, TaskEndEvent, TaskStartEvent


@dataclass(frozen=True)
class ExampleWorkflowResult:
    session: SessionInfo
    success: bool
    actions: List[ActionResult]
    artifacts: List[ArtifactHandle]
    error: Optional[str] = None
    events: List[EventEnvelope] = field(default_factory=list)


@dataclass(frozen=True)
class ExampleWorkflow:
    name: str
    session_factory: Callable[[], DriverSession]
    run_fn: Callable[[DriverSession], ExampleWorkflowResult]

    def run(self) -> ExampleWorkflowResult:
        session = self.session_factory()
        events = [
            TaskStartEvent(
                task_name=self.name,
                task_id=session.info.identifier,
            ).to_envelope()
        ]
        try:
            result = self.run_fn(session)
            events.extend(result.events)
            events.extend(
                artifact_event.to_envelope()
                for artifact_event in (
                    ArtifactEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        artifact_type=artifact.artifact_type,
                        path=str(artifact.path),
                    )
                    for artifact in result.artifacts
                )
            )
            events.append(
                TaskEndEvent(
                    task_name=self.name,
                    task_id=session.info.identifier,
                    outcome="succeeded" if result.success else "failed",
                ).to_envelope()
            )
            return ExampleWorkflowResult(
                session=result.session,
                success=result.success,
                actions=result.actions,
                artifacts=result.artifacts,
                error=result.error,
                events=events,
            )
        except Exception as exc:
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
            return ExampleWorkflowResult(
                session=session.info,
                success=False,
                actions=[],
                artifacts=[],
                error=f"{type(exc).__name__}: {exc}",
                events=events,
            )
