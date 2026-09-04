import asyncio
import time
from pathlib import Path

import pytest

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
from automation_core.execution import ExecutionContext, FailureCategory, WorkflowStatus
from automation_runner.collector import ReportCollector
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import _RunClock, WorkflowRuntime
from automation_runner.steps import WorkflowStep


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def execute_action(self, action_name, **kwargs):
        raise ConnectionError("driver socket died mid-action")

    def capture_artifact(self, artifact_type, name):
        raise ConnectionError("device detached")


class RecordingSession(FakeSession):
    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=True, message=action_name)


class FlakyProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        default_cancellation="cooperative",
    )

    def __init__(self):
        self.calls = 0

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        self.calls += 1
        if self.calls == 1:
            return CapabilityResult(
                success=False,
                provider="flaky",
                error_code="temporary",
                retryable=True,
            )
        return CapabilityResult(success=True, provider="flaky")


class BlockingOcrProvider:
    """Simulates a thread-wrapped provider that cannot honor cancellation."""

    manifest = CapabilityManifest(
        name="visual.ocr",
        version="1.0.0",
        operations=("extract",),
        default_cancellation="unsupported",
    )

    def __init__(self, duration):
        self.duration = duration

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="unsupported", blocking=True)

    async def execute(self, request, context):
        await asyncio.sleep(self.duration)
        return CapabilityResult(success=True, provider="blocking-ocr")


class BadProfileProvider:
    manifest = CapabilityManifest(
        name="visual.bad",
        version="1.0.0",
        operations=("solve",),
    )

    def execution_profile(self, request):
        return {"cancellation": "cooperative"}

    async def execute(self, request, context):
        return CapabilityResult(success=True, provider="bad")


def _executor(provider):
    registry = CapabilityRegistry()
    registry.register(provider)
    return CapabilityExecutor(CapabilityResolver(registry))


def _request(**parameters):
    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters=dict(parameters),
    )


def test_action_exception_becomes_failed_step_and_report():
    session = FakeSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="boom",
    )

    result = asyncio.run(runtime.arun([WorkflowStep.action("open", url="https://x")]))

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.PROVIDER
    assert result.failure.code == "action_execution_failed"
    assert result.failure.details == {"error_type": "ConnectionError"}
    assert "driver socket died" not in str(result.to_dict())
    assert [event["event_type"] for event in result.events] == [
        "workflow.start",
        "step.start",
        "action.end",
        "step.end",
        "workflow.end",
    ]
    assert result.events[-1]["payload"]["status"] == "failed"
    assert session.stopped == 1


def test_artifact_exception_becomes_failed_step_and_report():
    session = FakeSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="boom-artifact",
    )

    result = asyncio.run(runtime.arun([WorkflowStep.artifact("screenshot", "x.png")]))

    assert result.status is WorkflowStatus.FAILED
    assert result.failure.code == "artifact_capture_failed"
    assert result.failure.category is FailureCategory.PROVIDER
    handle = result.steps[0].artifact_result
    assert isinstance(handle.path, Path)
    assert handle.path.parts[-3:] == (result.context.run_id, "screenshot", "x.png")
    assert not handle.path.exists()
    assert list(result.artifacts) == []
    assert session.stopped == 1


def test_unregistered_capability_is_a_resolution_failure_without_retry():
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=CapabilityExecutor(CapabilityResolver(CapabilityRegistry())),
        workflow_name="missing-capability",
    )

    result = asyncio.run(
        runtime.arun(
            [WorkflowStep.capability("solve", request=_request(), policy=CapabilityPolicy(max_attempts=3))]
        )
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure.category is FailureCategory.RESOLUTION
    assert result.failure.code == "CapabilityNotFoundError"
    assert result.steps[0].attempts == 0
    assert result.steps[0].capability_result.error_code == "CapabilityNotFoundError"


def test_unsupported_operation_is_a_resolution_failure():
    provider = FlakyProvider()
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="wrong-operation",
    )
    request = CapabilityRequest(capability="visual.challenge", operation="translate")

    result = asyncio.run(
        runtime.arun([WorkflowStep.capability("translate", request=request)])
    )

    assert result.failure.category is FailureCategory.RESOLUTION
    assert result.failure.code == "CapabilityOperationNotSupportedError"


def test_invalid_execution_profile_is_a_config_failure():
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(BadProfileProvider()),
        workflow_name="bad-profile",
    )
    request = CapabilityRequest(capability="visual.bad", operation="solve")

    result = asyncio.run(
        runtime.arun([WorkflowStep.capability("solve", request=request)])
    )

    assert result.failure.category is FailureCategory.CONFIG
    assert result.failure.code == "CapabilityProtocolError"


def test_unsupported_cancellation_is_not_hard_timeout():
    provider = BlockingOcrProvider(duration=0.15)
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="blocking-ocr",
    )

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "extract",
                    request=CapabilityRequest(capability="visual.ocr", operation="extract"),
                    policy=CapabilityPolicy(timeout=0.01, max_attempts=1),
                )
            ]
        )
    )

    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.steps[0].status.value == "succeeded"
    assert result.steps[0].duration_ms >= 100


def test_deadline_exceeded_before_attempt_is_reported():
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(FlakyProvider()),
        workflow_name="late",
    )
    root = ExecutionContext(
        run_id="run-1",
        task_id=None,
        workflow_name="late",
        deadline=time.time() - 1,
    )
    step_context = root.for_step("step-1")
    collector = ReportCollector(root)
    step = WorkflowStep.capability(
        "solve",
        request=_request(),
        policy=CapabilityPolicy(timeout=5.0, max_attempts=2),
    )

    result = asyncio.run(
        runtime._run_capability(step, step_context, collector, _RunClock())
    )

    assert result.error is not None
    assert result.error.category is FailureCategory.TIMEOUT
    assert result.error.code == "deadline_exceeded"
    assert result.attempts == 0


def test_retry_attempts_are_visible_as_events():
    provider = FlakyProvider()
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="retry-events",
    )

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "solve",
                    request=_request(),
                    policy=CapabilityPolicy(timeout=1.0, max_attempts=2, backoff=0.0),
                )
            ]
        )
    )

    assert result.status is WorkflowStatus.SUCCEEDED
    assert provider.calls == 2
    retry_events = [
        event for event in result.events if event["event_type"] == "retry.attempt"
    ]
    assert len(retry_events) == 1
    assert retry_events[0]["task_id"] == result.context.for_step("step-1").task_id
    assert retry_events[0]["payload"]["attempt"] == 1
    assert retry_events[0]["payload"]["error_code"] == "temporary"
    capability_ends = [
        event for event in result.events if event["event_type"] == "capability.end"
    ]
    assert len(capability_ends) == 1
    end_event = capability_ends[0]
    assert end_event["event_id"] == f"{result.context.run_id}:step-1:capability.end"
    assert end_event["task_id"] == "step-1"
    assert end_event["payload"] == {
        "step_name": "solve",
        "provider": "flaky",
        "success": True,
        "error_code": None,
    }


def test_retry_backoff_is_clamped_to_remaining_deadline():
    provider = FlakyProvider()
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="backoff-clamp",
    )
    root = ExecutionContext(
        run_id="run-backoff",
        task_id=None,
        workflow_name="backoff-clamp",
        deadline=time.time() + 0.1,
    )
    step_context = root.for_step("step-1")
    collector = ReportCollector(root)
    step = WorkflowStep.capability(
        "solve",
        request=_request(),
        policy=CapabilityPolicy(timeout=5.0, max_attempts=3, backoff=10.0),
    )

    started = time.monotonic()
    result = asyncio.run(
        runtime._run_capability(step, step_context, collector, _RunClock())
    )
    elapsed = time.monotonic() - started

    assert result.status.value == "failed"
    assert provider.calls == 1
    assert result.attempts == 1
    assert elapsed < 5
    assert result.error is not None
    assert result.error.category is FailureCategory.TIMEOUT
    assert result.error.code == "deadline_exceeded"


def test_backoff_after_deadline_expiry_skips_next_attempt():
    provider = FlakyProvider()
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="backoff-expired",
    )
    root = ExecutionContext(
        run_id="run-backoff-expired",
        task_id=None,
        workflow_name="backoff-expired",
        deadline=time.time() - 1,
    )
    step_context = root.for_step("step-1")
    collector = ReportCollector(root)
    step = WorkflowStep.capability(
        "solve",
        request=_request(),
        policy=CapabilityPolicy(timeout=5.0, max_attempts=3, backoff=0.0),
    )

    result = asyncio.run(
        runtime._run_capability(step, step_context, collector, _RunClock())
    )

    assert provider.calls == 0
    assert result.attempts == 0
    assert result.error is not None
    assert result.error.category is FailureCategory.TIMEOUT
    assert result.error.code == "deadline_exceeded"


def test_backoff_after_failed_attempt_does_not_run_provider_again_when_deadline_passed():
    class ImmediateFailureProvider:
        manifest = CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="cooperative",
        )

        def __init__(self):
            self.calls = 0

        def execution_profile(self, request):
            return CapabilityExecutionProfile(cancellation="cooperative")

        async def execute(self, request, context):
            self.calls += 1
            return CapabilityResult(
                success=False,
                provider="immediate-failure",
                error_code="temporary",
                retryable=True,
            )

    provider = ImmediateFailureProvider()
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        capability_executor=_executor(provider),
        workflow_name="backoff-expired-mid-retry",
    )
    step_context = ExecutionContext(
        run_id="run-mid",
        task_id=None,
        workflow_name="backoff-expired-mid-retry",
        deadline=time.time() + 30,
    ).for_step("step-1")
    collector = ReportCollector(step_context)
    step = WorkflowStep.capability(
        "solve",
        request=_request(),
        policy=CapabilityPolicy(timeout=5.0, max_attempts=2, backoff=0.05),
    )
    clock = _RunClock()

    async def scenario():
        first = await runtime._run_capability(step, step_context, collector, clock)
        assert first.error is not None
        assert first.attempts == 2
        assert provider.calls == 2
        # Simulate the workflow deadline expiring between retry attempts.
        expired = ExecutionContext(
            run_id=step_context.run_id,
            task_id=step_context.task_id,
            workflow_name=step_context.workflow_name,
            deadline=time.time() - 1,
        )
        return await runtime._run_capability(step, expired, collector, clock)

    result = asyncio.run(scenario())

    assert provider.calls == 2
    assert result.attempts == 0
    assert result.error is not None
    assert result.error.category is FailureCategory.TIMEOUT
    assert result.error.code == "deadline_exceeded"
    runtime = WorkflowRuntime(
        session_factory=lambda: RecordingSession(),
        workflow_name="meta",
        metadata={"live": True, "token": "leak"},
    )

    result = asyncio.run(runtime.arun([WorkflowStep.action("open")]))

    assert result.context.metadata["live"] is True
    assert result.context.metadata["token"] == "leak"
    serialized = result.to_dict()["context"]["metadata"]
    assert serialized["token"] == "[redacted]"
    assert serialized["live"] is True


def test_cancelled_artifact_step_reports_sanitized_deterministic_path():
    from pathlib import Path

    class CancelArtifactSession:
        info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")

        def start(self):
            return None

        def stop(self):
            return None

        def execute_action(self, action_name, **kwargs):
            return ActionResult(success=True, message=action_name)

        def capture_artifact(self, artifact_type, name):
            raise asyncio.CancelledError()

    runtime = WorkflowRuntime(
        session_factory=lambda: CancelArtifactSession(),
        workflow_name="cancel-artifact",
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.artifact("page_source", "run/../leak.xml")])
    )

    assert result.status is WorkflowStatus.CANCELLED
    handle = result.steps[0].artifact_result
    assert isinstance(handle.path, Path)
    assert all(part not in {"..", ""} for part in handle.path.parts)
    assert handle.path.parts[-1] == "leak.xml"
    assert list(result.artifacts) == []


def test_runtime_artifact_root_anchors_unwritten_paths():
    from pathlib import Path

    class CancelArtifactSession:
        info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")

        def start(self):
            return None

        def stop(self):
            return None

        def execute_action(self, action_name, **kwargs):
            return ActionResult(success=True, message=action_name)

        def capture_artifact(self, artifact_type, name):
            raise asyncio.CancelledError()

    runtime = WorkflowRuntime(
        session_factory=lambda: CancelArtifactSession(),
        workflow_name="rooted",
        artifact_root=Path("/srv/automation-artifacts"),
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.artifact("screenshot", "home.png")])
    )

    handle = result.steps[0].artifact_result
    assert handle.path.parts[:2] == ("/", "srv")
    assert handle.path.parts[-1] == "home.png"
    assert handle.path.parts[-3] == result.context.run_id
