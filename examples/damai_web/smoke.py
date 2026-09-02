from typing import Callable, List

from automation_core.drivers import DriverSession
from automation_runner.runtime import WorkflowRuntime
from automation_runner.workflows import ComposedWorkflow, WorkflowStep

SessionFactory = Callable[[], DriverSession]


def build_steps(url: str) -> List[WorkflowStep]:
    return [
        WorkflowStep.action("open", url=url),
        WorkflowStep.artifact("screenshot", "home.png"),
    ]


def create_workflow(session_factory: SessionFactory, url: str) -> ComposedWorkflow:
    runtime = WorkflowRuntime(
        session_factory=session_factory,
        workflow_name="damai-web-smoke",
    )
    return ComposedWorkflow(runtime, build_steps(url))
