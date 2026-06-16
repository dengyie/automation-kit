from typing import Callable

from automation_core.drivers import DriverSession
from examples.workflows import (
    ExampleWorkflow,
    ExampleWorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)


def run_smoke_workflow(session: DriverSession, url: str) -> ExampleWorkflowResult:
    return run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url=url),
            WorkflowStep.artifact("screenshot", "home.png"),
        ],
    )


def create_workflow(
    session_factory: Callable[[], DriverSession],
    url: str,
) -> ExampleWorkflow:
    return ExampleWorkflow(
        name="damai-web-smoke",
        session_factory=session_factory,
        run_fn=lambda session: run_smoke_workflow(session, url=url),
    )
