from typing import Callable

from automation_core.drivers import DriverSession
from examples.workflows import ExampleWorkflow, ExampleWorkflowResult


def run_smoke_workflow(session: DriverSession, url: str) -> ExampleWorkflowResult:
    actions = []
    artifacts = []
    try:
        session.start()
        actions.append(session.execute_action("get", url=url))
        artifacts.append(session.capture_artifact("screenshot", "home.png"))
        success = all(action.success for action in actions)
        return ExampleWorkflowResult(
            session=session.info,
            success=success,
            actions=actions,
            artifacts=artifacts,
        )
    finally:
        session.stop()


def create_workflow(
    session_factory: Callable[[], DriverSession],
    url: str,
) -> ExampleWorkflow:
    return ExampleWorkflow(
        session_factory=session_factory,
        run_fn=lambda session: run_smoke_workflow(session, url=url),
    )
