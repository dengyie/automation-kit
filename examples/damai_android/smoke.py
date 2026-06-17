from typing import Callable

from automation_core.drivers import DriverSession
from automation_runner.workflows import (
    ManagedWorkflow,
    WorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)


def run_smoke_workflow(session: DriverSession, app_id: str) -> WorkflowResult:
    return run_workflow_steps(
        session,
        [
            WorkflowStep.action("launch_app", app_id=app_id),
            WorkflowStep.artifact("screenshot", "startup.png"),
            WorkflowStep.artifact("page_source", "startup.xml"),
        ],
    )


def create_workflow(
    session_factory: Callable[[], DriverSession],
    app_id: str,
) -> ManagedWorkflow:
    return ManagedWorkflow(
        name="damai-android-smoke",
        session_factory=session_factory,
        run_fn=lambda session: run_smoke_workflow(session, app_id=app_id),
    )
