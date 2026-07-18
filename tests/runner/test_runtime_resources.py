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


def test_runtime_start_failure_does_not_run_steps():
    class BoomStart:
        def __init__(self):
            self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
            self.stopped = 0

        def start(self):
            raise RuntimeError("start failed")

        def stop(self):
            self.stopped += 1

        def execute_action(self, action_name, **kwargs):
            raise AssertionError("steps should not run")

    session = BoomStart()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        capability_executor=None,
        workflow_name="start-smoke",
    )

    result = asyncio.run(runtime.arun([WorkflowStep.action("open", url="https://example.test")]))

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "session_start_failed"
    assert session.stopped == 1
    assert result.steps == ()


def test_runtime_stop_failure_is_secondary_and_preserves_primary_failure():
    class BoomStop:
        def __init__(self):
            self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")

        def start(self):
            return None

        def stop(self):
            raise RuntimeError("stop failed")

        def execute_action(self, action_name, **kwargs):
            return ActionResult(success=False, message="boom")

    runtime = WorkflowRuntime(
        session_factory=BoomStop,
        capability_executor=None,
        workflow_name="stop-smoke",
    )

    result = asyncio.run(runtime.arun([WorkflowStep.action("open", url="https://example.test")]))

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "action_failed"
    assert result.failure.details.get("cleanup_error_type") == "RuntimeError"
