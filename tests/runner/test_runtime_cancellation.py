import asyncio

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from automation_core.drivers import ActionResult, SessionInfo
from automation_core.execution import WorkflowStatus
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
        self.stopped = 0

    def start(self):
        return None

    def stop(self):
        self.stopped += 1

    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=True, message=action_name)


class SlowProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        default_cancellation="cooperative",
    )

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        await asyncio.sleep(10)
        return CapabilityResult(success=True, provider="slow")


def test_runtime_timeout_cancels_capability_and_closes_session():
    session = FakeSession()
    registry = CapabilityRegistry()
    registry.register(SlowProvider())
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        capability_executor=CapabilityExecutor(CapabilityResolver(registry)),
        workflow_name="timeout-smoke",
    )

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "solve-captcha",
                    request=CapabilityRequest(
                        capability="visual.challenge",
                        operation="solve",
                    ),
                    policy=CapabilityPolicy(timeout=0.05, max_attempts=1, backoff=0.0),
                )
            ]
        )
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.category.value == "timeout"
    assert session.stopped == 1
