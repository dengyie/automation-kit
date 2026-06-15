from automation_core.drivers import DriverSession
from examples.workflows import ExampleWorkflowResult


def run_smoke_workflow(session: DriverSession, app_id: str) -> ExampleWorkflowResult:
    actions = []
    artifacts = []
    try:
        session.start()
        actions.append(session.execute_action("activate_app", app_id=app_id))
        artifacts.append(session.capture_artifact("screenshot", "startup.png"))
        artifacts.append(session.capture_artifact("page_source", "startup.xml"))
        success = all(action.success for action in actions)
        return ExampleWorkflowResult(
            session=session.info,
            success=success,
            actions=actions,
            artifacts=artifacts,
        )
    finally:
        session.stop()
