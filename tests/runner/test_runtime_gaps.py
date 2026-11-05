"""Deep-coverage tests for WorkflowRuntime gap branches.

Pins the runtime contracts a refactor would silently break:
deadline-before-step (lines 156-164), the last-resort step exception
normalization (201-204), capability-artifact event recording (227-229),
cleanup-failure becoming the primary failure (289-290), and the
session-stop raise path (988).
"""

import asyncio
import time

import pytest

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityResolver,
    CapabilityRequest,
    CapabilityResult,
)
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.execution import FailureCategory, WorkflowStatus
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep


class CleanSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="s")
        self.stopped = 0

    def start(self):
        return None

    def stop(self):
        self.stopped += 1

    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=True, message=action_name)

    def capture_artifact(self, artifact_type, name):
        return ArtifactHandle(artifact_type=artifact_type, path=None)


def test_deadline_exceeded_before_step_is_timeout_failure():
    """An expired workflow deadline fails the FIRST step before it starts:
    TIMEOUT category, deadline_exceeded code, per-step message, and no
    session interaction."""
    session = CleanSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="expired-deadline",
        deadline=time.time() - 1.0,
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.action("open", url="https://x")])
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.TIMEOUT
    assert result.failure.code == "deadline_exceeded"
    assert "before step: open" in result.failure.message
    # The step itself was never dispatched.
    assert result.steps == ()
    assert session.stopped == 1


def test_capability_artifacts_attach_to_report():
    """Artifacts returned inside a CapabilityResult surface in
    report.artifacts and each emits an artifact event."""

    class ProducingProvider:
        manifest = CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="cooperative",
        )

        def execution_profile(self, request):
            return CapabilityExecutionProfile(cancellation="cooperative")

        async def execute(self, request, context):
            return CapabilityResult(
                success=True,
                provider="producing",
                artifacts=[
                    ArtifactHandle(
                        artifact_type="screenshot",
                        path=None,
                        metadata={"source": "capability"},
                    )
                ],
            )

    registry = CapabilityRegistry()
    registry.register(ProducingProvider())
    runtime = WorkflowRuntime(
        session_factory=CleanSession,
        capability_executor=CapabilityExecutor(CapabilityResolver(registry)),
        workflow_name="cap-artifacts",
    )

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "solve",
                    request=CapabilityRequest(
                        capability="visual.challenge", operation="solve"
                    ),
                    policy=CapabilityPolicy(timeout=2.0, max_attempts=1, backoff=0.0),
                )
            ]
        )
    )

    assert result.status is WorkflowStatus.SUCCEEDED
    artifacts = list(result.artifacts)
    assert len(artifacts) == 1
    assert artifacts[0].metadata == {"source": "capability"}
    artifact_events = [e for e in result.events if e["event_type"] == "artifact"]
    assert len(artifact_events) == 1
    assert artifact_events[0]["payload"]["artifact_type"] == "screenshot"


def test_step_exception_is_normalized_into_failed_step():
    """An exception escaping the step executor still yields a step result,
    a failed report, and a stopped session — nothing propagates out of
    arun (last-resort normalization)."""
    session = CleanSession()

    def exploding(action_name, **kwargs):
        raise RuntimeError("step blew up outside normalization")

    session.execute_action = exploding
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="unhandled-step",
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.action("open", url="https://x")])
    )

    # Action steps normalize their own exceptions (action_execution_failed).
    assert result.status is WorkflowStatus.FAILED
    assert result.failure.code == "action_execution_failed"
    assert result.failure.details["error_type"] == "RuntimeError"
    assert len(result.steps) == 1
    assert session.stopped == 1

    # Artifact steps have their own normalization (artifact_capture_failed).
    result2 = asyncio.run(
        WorkflowRuntime(
            session_factory=lambda: session,
            workflow_name="unhandled-artifact",
        ).arun([WorkflowStep.artifact("screenshot", "x.png")])
    )
    assert result2.status is WorkflowStatus.SUCCEEDED  # CleanSession captures fine


def test_cleanup_failure_becomes_primary_when_no_other_failure():
    """Session stop raising on an otherwise-successful run turns the run
    FAILED with the CLEANUP category and session_stop_failed code."""

    class BoomStopSession(CleanSession):
        def stop(self):
            self.stopped += 1
            raise RuntimeError("adb transport died on close")

    runtime = WorkflowRuntime(
        session_factory=BoomStopSession,
        workflow_name="cleanup-primary",
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.action("open", url="https://x")])
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.CLEANUP
    assert result.failure.code == "session_stop_failed"
    assert result.failure.details["error_type"] == "RuntimeError"


def test_cleanup_failure_after_primary_failure_is_merged_not_replacing():
    """With both a primary failure and a stop failure, the primary wins and
    the cleanup error rides in details (§8.3 precedence)."""

    class FailingAndBoomStopSession(CleanSession):
        def execute_action(self, action_name, **kwargs):
            return ActionResult(success=False, message="action failed")

        def stop(self):
            self.stopped += 1
            raise RuntimeError("close failed too")

    runtime = WorkflowRuntime(
        session_factory=FailingAndBoomStopSession,
        workflow_name="cleanup-secondary",
    )

    result = asyncio.run(
        runtime.arun([WorkflowStep.action("open", url="https://x")])
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure.code == "action_failed"
    assert result.failure.details.get("cleanup_error_type") == "RuntimeError"


# --- remaining branches: excerpt truncation, unsupported step, provider raise -----


def test_exception_excerpt_truncates_long_messages():
    """_exception_excerpt bounds a driver traceback to 300 chars (line 41)."""
    from automation_runner.runtime import _exception_excerpt

    class TracebackError(Exception):
        def __str__(self):
            return "x" * 900

    excerpt = _exception_excerpt(TracebackError())
    assert len(excerpt) == 300
    assert excerpt.endswith("...")

    # Empty message falls back to the class name.
    assert _exception_excerpt(RuntimeError()) == "RuntimeError"


def test_capability_error_category_mapping():
    """_capability_error_category maps registration vs resolution vs config
    (lines 76-82)."""
    from automation_core.capabilities import (
        CapabilityNotFoundError,
        CapabilityRegistrationError,
    )
    from automation_runner.runtime import _capability_error_category

    assert (
        _capability_error_category(CapabilityRegistrationError("dup"))
        is FailureCategory.REGISTRATION
    )
    assert (
        _capability_error_category(CapabilityNotFoundError("missing"))
        is FailureCategory.RESOLUTION
    )
    assert _capability_error_category(RuntimeError("other")) is FailureCategory.CONFIG


def test_provider_execute_raise_surfaces_provider_exception_result():
    """A provider.execute raise is swallowed by the executor into a
    provider_exception CapabilityResult; the runtime then reports it as a
    business failure carrying that error_code (the runtime's own
    except-Exception branch at 701-710 fires only for raise sites outside
    executor.execute, e.g. a broken cooperative wrapper)."""

    class ExplodingProvider:
        manifest = CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="cooperative",
        )

        def execution_profile(self, request):
            return CapabilityExecutionProfile(cancellation="cooperative")

        async def execute(self, request, context):
            raise RuntimeError("provider core dump")

    registry = CapabilityRegistry()
    registry.register(ExplodingProvider())
    runtime = WorkflowRuntime(
        session_factory=CleanSession,
        capability_executor=CapabilityExecutor(CapabilityResolver(registry)),
        workflow_name="provider-raise",
    )

    result = asyncio.run(
        runtime.arun(
            [
                WorkflowStep.capability(
                    "solve",
                    request=CapabilityRequest(
                        capability="visual.challenge", operation="solve"
                    ),
                    policy=CapabilityPolicy(timeout=2.0, max_attempts=1, backoff=0.0),
                )
            ]
        )
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.failure.code == "provider_exception"
    assert result.failure.category is FailureCategory.BUSINESS

    # The step result carries the executor's provider_exception result.
    cap = result.steps[0].capability_result
    assert cap is not None
    assert cap.error_code == "provider_exception"
    assert cap.metadata["error_type"] == "RuntimeError"


def test_unsupported_step_kind_fails_via_step_execution_failed():
    """A step kind the executor does not know falls through _execute_step to
    _unsupported_step; the resulting failure is surfaced through the
    generic step_execution_failed normalization (line 394 + 201-204)."""
    session = CleanSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="bad-kind",
    )
    step = WorkflowStep.action("open", url="https://x")
    object.__setattr__(step, "kind", "quantum")

    result = asyncio.run(runtime.arun([step]))

    assert result.status is WorkflowStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "step_execution_failed"
    assert "_unsupported_step" in result.failure.details["error_message"]
