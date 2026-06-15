from automation_core.drivers import DriverSession
from examples.workflows import ExampleWorkflowResult


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
