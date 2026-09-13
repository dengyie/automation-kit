from pathlib import Path

import pytest

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.execution import FailureCategory
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep


class FakeSession:
    def __init__(self, *, fail_on=None, capture_ok=True):
        self.info = SessionInfo(
            driver_name="fake", platform="web", identifier="fake-run"
        )
        self.fail_on = set(fail_on or ())
        self.capture_ok = capture_ok
        self.actions = []
        self.captures = []
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def execute_action(self, action_name, **kwargs):
        self.actions.append(action_name)
        if action_name in self.fail_on:
            return ActionResult(False, f"{action_name} failed")
        return ActionResult(True, action_name)

    def capture_artifact(self, artifact_type, name):
        self.captures.append((artifact_type, name))
        if not self.capture_ok:
            raise RuntimeError("capture boom")
        path = Path("artifacts") / artifact_type / name
        return ArtifactHandle(artifact_type=artifact_type, path=path)


def test_artifact_step_default_keeps_parameter_shape():
    step = WorkflowStep.artifact("screenshot", "home.png")

    assert step.parameters == {"name": "home.png"}


def test_artifact_step_capture_on_failure_is_recorded():
    step = WorkflowStep.artifact("screenshot", "fail.png", capture_on="failure")

    assert step.parameters == {"name": "fail.png", "capture_on": "failure"}


def test_artifact_step_rejects_unknown_capture_on():
    with pytest.raises(ValueError, match="capture_on"):
        WorkflowStep.artifact("screenshot", "x.png", capture_on="sometimes")


def test_always_artifacts_run_in_success_flow():
    session = FakeSession()
    runtime = WorkflowRuntime(session_factory=lambda: session)
    steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "always.png", capture_on="always"),
        WorkflowStep.artifact("screenshot", "onfail.png", capture_on="failure"),
    ]

    result = runtime.run(steps)

    assert result.status.value == "succeeded"
    assert session.captures == [("screenshot", "always.png")]
    # The declared failure capture stays visible as SKIPPED on the happy path.
    skipped = [step for step in result.steps if step.status.value == "skipped"]
    assert [step.step_name for step in skipped] == ["screenshot"]
    assert skipped[0].artifact_result.metadata == {
        "capture_on": "failure",
        "state": "skipped",
    }


def test_failure_triggers_capture_on_failure_artifacts():
    session = FakeSession(fail_on={"open"})
    runtime = WorkflowRuntime(session_factory=lambda: session)
    steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "always.png"),
        WorkflowStep.artifact("screenshot", "fail-1.png", capture_on="failure"),
        WorkflowStep.artifact("page_source", "fail-2.xml", capture_on="failure"),
    ]

    result = runtime.run(steps)

    assert result.status.value == "failed"
    assert result.failure.code == "action_failed"
    # The failing action is not retried; always-artifacts after it never run,
    # but both declared failure captures executed in declaration order while
    # the session was still alive.
    assert session.actions == ["open"]
    assert session.captures == [
        ("screenshot", "fail-1.png"),
        ("page_source", "fail-2.xml"),
    ]
    assert session.stopped is True

    capture_steps = [step for step in result.steps if "-onfailure-" in step.step_id]
    assert [step.step_name for step in capture_steps] == ["screenshot", "page_source"]
    assert all(step.status.value == "succeeded" for step in capture_steps)

    capture_events = [
        event
        for event in result.events
        if isinstance(event, dict)
        and event.get("payload", {}).get("capture_on") == "failure"
        and event.get("event_type") == "step.end"
    ]
    assert len(capture_events) == 2

    artifact_types = {a.artifact_type for a in result.artifacts}
    assert {"screenshot", "page_source"} <= artifact_types


def test_failed_capture_does_not_mask_original_failure():
    session = FakeSession(fail_on={"open"}, capture_ok=False)
    runtime = WorkflowRuntime(session_factory=lambda: session)
    steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "fail.png", capture_on="failure"),
    ]

    result = runtime.run(steps)

    assert result.status.value == "failed"
    assert result.failure.code == "action_failed"
    failed_capture = [step for step in result.steps if "-onfailure-" in step.step_id]
    assert len(failed_capture) == 1
    assert failed_capture[0].status.value == "failed"


def test_capability_failure_also_triggers_captures():
    session = FakeSession()
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        capability_executor=None,
    )
    request = _fake_capability_request()
    steps = [
        WorkflowStep.capability("solve", request=request),
        WorkflowStep.artifact("screenshot", "fail.png", capture_on="failure"),
    ]

    result = runtime.run(steps)

    assert result.status.value == "failed"
    assert session.captures == [("screenshot", "fail.png")]


def test_cancel_during_failure_capture_preserves_primary_failure():
    import asyncio

    class CancelDuringCaptureSession(FakeSession):
        def capture_artifact(self, artifact_type, name):
            self.captures.append((artifact_type, name))
            raise asyncio.CancelledError()

    session = CancelDuringCaptureSession()
    session.fail_on.add("open")
    runtime = WorkflowRuntime(session_factory=lambda: session)
    steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "fail.png", capture_on="failure"),
    ]

    result = runtime.run(steps)

    # The run is cancelled, but the primary failure is preserved (§8.3).
    assert result.status.value == "cancelled"
    assert result.failure is not None
    assert result.failure.code == "action_failed"
    cancelled_capture = [
        step for step in result.steps if "-onfailure-" in step.step_id
    ]
    assert len(cancelled_capture) == 1
    assert cancelled_capture[0].status.value == "cancelled"
    # No dangling step.start: the interrupted capture has a step.end event.
    ends = [
        event
        for event in result.events
        if isinstance(event, dict)
        and event.get("task_id") == "step-1-onfailure-1"
        and event.get("event_type") == "step.end"
    ]
    assert len(ends) == 1


def _fake_capability_request():
    from automation_core.capabilities import CapabilityRequest

    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters={},
    )


def test_cancelled_run_skips_failure_captures():
    import asyncio

    class CancellingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            self.actions.append(action_name)
            raise asyncio.CancelledError()

    session = CancellingSession()
    runtime = WorkflowRuntime(session_factory=lambda: session)
    steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "fail.png", capture_on="failure"),
    ]

    result = runtime.run(steps)

    assert result.status.value == "cancelled"
    assert session.captures == []
    assert all(
        "-onfailure-" not in step.step_id for step in result.steps
    )
