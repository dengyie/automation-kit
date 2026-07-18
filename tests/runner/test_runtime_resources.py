import asyncio

from automation_core.drivers import ActionResult, SessionInfo
from automation_core.execution import WorkflowStatus
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep


class FailingSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
        self.stopped = 0

    def start(self):
        return None

    def stop(self):
        self.stopped += 1

    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=False, message="boom")


def test_runtime_closes_owned_session_after_action_failure():
    session = FailingSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        capability_executor=None,
        workflow_name="resource-smoke",
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.action("open", url="https://example.test")])
    )

    assert result.status is WorkflowStatus.FAILED
    assert session.stopped == 1
