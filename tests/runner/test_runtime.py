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
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.execution import StepKind, StepStatus, WorkflowStatus
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
        self.started = 0
        self.stopped = 0
        self.actions = []

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def execute_action(self, action_name, **kwargs):
        self.actions.append((action_name, kwargs))
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type, name):
        return ArtifactHandle(artifact_type=artifact_type, path=name)


class FakeProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("web",),
        default_cancellation="cooperative",
    )

    def __init__(self):
        self.calls = 0

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        self.calls += 1
        if request.parameters.get("fail_once") and self.calls == 1:
            return CapabilityResult(
                success=False,
                provider="fake",
                error_code="temporary",
                retryable=True,
            )
        return CapabilityResult(
            success=True,
            provider="fake",
            data={"task_id": context.task_id, "run_id": context.run_id},
        )


def _runtime(provider=None, session=None):
    session = session or FakeSession()
    provider = provider or FakeProvider()
    registry = CapabilityRegistry()
    registry.register(provider)
    executor = CapabilityExecutor(CapabilityResolver(registry))
    return WorkflowRuntime(
        session_factory=lambda: session,
        capability_executor=executor,
        workflow_name="smoke",
    ), session, provider


def test_runtime_runs_action_and_capability_steps_with_shared_identity():
    runtime, session, provider = _runtime()

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.action("open", url="https://example.test"),
                WorkflowStep.capability(
                    "solve-captcha",
                    request=CapabilityRequest(
                        capability="visual.challenge",
                        operation="solve",
                        parameters={"challenge_type": "slider_captcha"},
                    ),
                    policy=CapabilityPolicy(timeout=1.0, max_attempts=1, backoff=0.0),
                ),
            ]
        )
    )

    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.success is True
    assert len(result.steps) == 2
    assert result.steps[0].kind is StepKind.ACTION
    assert result.steps[1].kind is StepKind.CAPABILITY
    assert result.steps[0].context.run_id == result.context.run_id
    assert result.steps[1].context.task_id is not None
    assert result.steps[1].capability_result.data["run_id"] == result.context.run_id
    assert session.started == 1
    assert session.stopped == 1
    assert provider.calls == 1


def test_runtime_retries_retryable_capability_failure_with_same_task_id():
    runtime, _, provider = _runtime()

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "solve-captcha",
                    request=CapabilityRequest(
                        capability="visual.challenge",
                        operation="solve",
                        parameters={"fail_once": True},
                    ),
                    policy=CapabilityPolicy(timeout=1.0, max_attempts=2, backoff=0.0),
                )
            ]
        )
    )

    assert result.success is True
    assert provider.calls == 2
    assert result.steps[0].attempts == 2
    assert result.steps[0].status is StepStatus.SUCCEEDED


def test_sync_run_rejects_nested_event_loop():
    runtime, _, _ = _runtime()

    async def nested():
        try:
            runtime.run([WorkflowStep.action("open", url="https://example.test")])
            return False
        except RuntimeError as exc:
            return "event loop" in str(exc).lower()

    assert asyncio.run(nested()) is True


def test_runtime_runs_artifact_step_and_records_lifecycle_events():
    runtime, session, _ = _runtime()

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.action("open", url="https://example.test"),
                WorkflowStep.artifact("screenshot", "home.png"),
            ]
        )
    )

    assert result.status is WorkflowStatus.SUCCEEDED
    assert len(result.steps) == 2
    assert result.steps[1].kind is StepKind.ARTIFACT
    assert result.artifacts[0].artifact_type == "screenshot"
    event_types = [event["event_type"] for event in result.events]
    assert event_types[0] == "workflow.start"
    assert "step.start" in event_types
    assert "step.end" in event_types
    assert event_types[-1] == "workflow.end"
    assert session.stopped == 1
