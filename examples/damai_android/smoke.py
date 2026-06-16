from typing import Callable

from automation_core.actions import ActionBatch, ActionExecutor, ActionRequest
from automation_core.drivers import DriverSession
from examples.workflows import ExampleWorkflow, ExampleWorkflowResult


def run_smoke_workflow(session: DriverSession, app_id: str) -> ExampleWorkflowResult:
    artifacts = []
    try:
        session.start()
        batch_result = ActionExecutor(session).run_batch(
            ActionBatch(
                actions=[
                    ActionRequest(name="launch_app", parameters={"app_id": app_id}),
                ]
            )
        )
        artifacts.append(session.capture_artifact("screenshot", "startup.png"))
        artifacts.append(session.capture_artifact("page_source", "startup.xml"))
        return ExampleWorkflowResult(
            session=session.info,
            success=batch_result.success,
            actions=batch_result.results,
            artifacts=artifacts,
            batch_result=batch_result,
        )
    finally:
        session.stop()


def create_workflow(
    session_factory: Callable[[], DriverSession],
    app_id: str,
) -> ExampleWorkflow:
    return ExampleWorkflow(
        name="damai-android-smoke",
        session_factory=session_factory,
        run_fn=lambda session: run_smoke_workflow(session, app_id=app_id),
    )
