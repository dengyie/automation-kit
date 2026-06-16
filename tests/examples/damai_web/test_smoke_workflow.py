from pathlib import Path

import pytest

from automation_core.actions import ActionBatchResult, ActionRequest
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.events import ArtifactEvent, ErrorEvent, RetryAttemptEvent
from examples.damai_web import create_workflow, run_smoke_workflow
from examples.workflows import (
    ExampleWorkflow,
    ExampleWorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(
            driver_name="fake-selenium",
            platform="web",
            identifier="web-run",
        )
        self.started = False
        self.stopped = False
        self.actions = []
        self.artifacts = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def execute_action(self, action_name, **kwargs):
        self.actions.append((action_name, kwargs))
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type, name):
        self.artifacts.append((artifact_type, name))
        return ArtifactHandle(artifact_type=artifact_type, path=Path(name))


def test_damai_web_smoke_workflow_opens_url_and_captures_screenshot():
    session = FakeSession()

    result = run_smoke_workflow(session, url="https://example.test/damai")

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert result.session == session.info
    assert result.actions[0].message == "open"
    assert result.batch_result is not None
    assert result.batch_result.results == result.actions
    assert result.batch_result.skipped == []
    assert session.actions == [("open", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]


def test_damai_web_smoke_workflow_factory_returns_runnable_workflow():
    session = FakeSession()
    workflow = create_workflow(session_factory=lambda: session, url="https://example.test/damai")

    result = workflow.run()

    assert workflow.name == "damai-web-smoke"
    assert result.success is True
    assert session.actions == [("open", {"url": "https://example.test/damai"})]
    assert result.batch_result is not None
    assert result.batch_result.success is True
    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "task.end",
    ]
    assert result.events[0].payload["task_name"] == "damai-web-smoke"
    assert result.events[-1].payload["outcome"] == "succeeded"


def test_damai_web_workflow_factory_returns_failure_result():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()
    workflow = create_workflow(session_factory=lambda: session, url="https://example.test/damai")

    result = workflow.run()

    assert result.success is False
    assert result.error is None
    assert [action.message for action in result.actions] == [
        "open failed: navigation failed",
    ]
    assert result.artifacts == []
    assert [event.event_type for event in result.events] == [
        "task.start",
        "task.end",
    ]
    assert result.events[-1].payload["outcome"] == "failed"
    assert session.stopped is True


def test_example_workflow_preserves_events_returned_by_run_function():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=True,
            actions=[],
            artifacts=[],
            events=[
                RetryAttemptEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    attempt=1,
                    elapsed=0.1,
                ).to_envelope()
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "retry.attempt",
        "task.end",
    ]


def test_example_workflow_emits_error_event_for_returned_failure_result():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=False,
            actions=[ActionResult(success=True, message="open")],
            artifacts=[
                ArtifactHandle(
                    artifact_type="screenshot",
                    path=Path("home.png"),
                )
            ],
            error="RuntimeError: screenshot failed",
        ),
    )

    result = workflow.run()

    assert result.success is False
    assert result.error == "RuntimeError: screenshot failed"
    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "error",
        "task.end",
    ]
    assert result.events[2].payload == {
        "task_name": "custom-workflow",
        "task_id": "web-run",
        "message": "screenshot failed",
        "error_type": "RuntimeError",
    }
    assert result.events[-1].payload["outcome"] == "failed"


def test_example_workflow_does_not_duplicate_returned_error_events():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=False,
            actions=[],
            artifacts=[],
            error="RuntimeError: screenshot failed",
            events=[
                ErrorEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    message="screenshot failed",
                    error_type="RuntimeError",
                ).to_envelope()
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "error",
        "task.end",
    ]


def test_example_workflow_does_not_duplicate_returned_artifact_events():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=True,
            actions=[],
            artifacts=[
                ArtifactHandle(
                    artifact_type="screenshot",
                    path=Path("home.png"),
                )
            ],
            events=[
                ArtifactEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    artifact_type="screenshot",
                    path="home.png",
                ).to_envelope()
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "task.end",
    ]


def test_example_workflow_preserves_batch_summary_returned_by_run_function():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=True,
            actions=[],
            artifacts=[],
            batch_result=ActionBatchResult(
                results=[ActionResult(success=True, message="open")],
                skipped=[ActionRequest(name="after")],
            ),
        ),
    )

    result = workflow.run()

    assert result.batch_result is not None
    assert result.batch_result.success is True
    assert [item.message for item in result.batch_result.results] == ["open"]


def test_run_workflow_steps_runs_actions_and_artifacts_in_order():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.artifact("screenshot", "home.png"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("page_source", "after-click.html"),
        ],
    )

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert [action.message for action in result.actions] == ["open", "click"]
    assert result.batch_result is not None
    assert result.batch_result.skipped == []
    assert session.actions == [
        ("open", {"url": "https://example.test/damai"}),
        ("click", {"selector": "#buy"}),
    ]
    assert session.artifacts == [
        ("screenshot", "home.png"),
        ("page_source", "after-click.html"),
    ]


def test_run_workflow_steps_preserves_prior_results_when_artifact_capture_fails():
    class ArtifactFailureSession(FakeSession):
        def capture_artifact(self, artifact_type, name):
            if name == "broken.png":
                raise RuntimeError("screenshot failed")
            return super().capture_artifact(artifact_type, name)

    session = ArtifactFailureSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.artifact("screenshot", "home.png"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("screenshot", "broken.png"),
        ],
    )

    assert result.success is False
    assert result.error == "RuntimeError: screenshot failed"
    assert [action.message for action in result.actions] == ["open", "click"]
    assert result.batch_result is not None
    assert [action.message for action in result.batch_result.results] == [
        "open",
        "click",
    ]
    assert [artifact.path for artifact in result.artifacts] == [Path("home.png")]
    assert session.artifacts == [("screenshot", "home.png")]
    assert session.stopped is True


def test_run_workflow_steps_stops_after_failed_action_batch():
    class FailedActionSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            self.actions.append((action_name, kwargs))
            return ActionResult(success=action_name != "open", message=action_name)

    session = FailedActionSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("screenshot", "should-not-run.png"),
        ],
    )

    assert result.success is False
    assert [action.message for action in result.actions] == ["open"]
    assert result.batch_result is not None
    assert [action.name for action in result.batch_result.skipped] == ["click"]
    assert result.artifacts == []
    assert session.artifacts == []
    assert session.stopped is True


def test_run_workflow_steps_allows_artifact_only_sequences():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.artifact("screenshot", "home.png"),
        ],
    )

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert result.actions == []
    assert result.batch_result is None
    assert session.actions == []
    assert session.artifacts == [("screenshot", "home.png")]


def test_damai_web_smoke_workflow_returns_failure_when_action_raises():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()

    result = run_smoke_workflow(session, url="https://example.test/damai")

    assert result.success is False
    assert result.error is None
    assert [action.message for action in result.actions] == [
        "open failed: navigation failed",
    ]
    assert result.artifacts == []
    assert session.started is True
    assert session.stopped is True
