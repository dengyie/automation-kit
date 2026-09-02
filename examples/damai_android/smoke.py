from typing import Callable, List

from automation_core.drivers import DriverSession
from automation_runner.runtime import WorkflowRuntime
from automation_runner.workflows import ComposedWorkflow, WorkflowStep

SessionFactory = Callable[[], DriverSession]


def build_steps(app_id: str) -> List[WorkflowStep]:
    return [
        WorkflowStep.action("launch_app", app_id=app_id),
        WorkflowStep.artifact("screenshot", "startup.png"),
        WorkflowStep.artifact("page_source", "startup.xml"),
    ]


def create_workflow(session_factory: SessionFactory, app_id: str) -> ComposedWorkflow:
    runtime = WorkflowRuntime(
        session_factory=session_factory,
        workflow_name="damai-android-smoke",
    )
    return ComposedWorkflow(runtime, build_steps(app_id))
