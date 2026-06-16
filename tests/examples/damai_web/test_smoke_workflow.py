from pathlib import Path

import pytest

from automation_core.actions import ActionBatchResult, ActionRequest
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.events import RetryAttemptEvent
from examples.damai_web import create_workflow, run_smoke_workflow
from examples.workflows import ExampleWorkflow, ExampleWorkflowResult


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
    assert result.error == "RuntimeError: navigation failed"
    assert result.actions == []
    assert result.artifacts == []
    assert [event.event_type for event in result.events] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert result.events[1].payload["error_type"] == "RuntimeError"
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


def test_damai_web_smoke_workflow_stops_session_when_action_fails():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()

    with pytest.raises(RuntimeError, match="navigation failed"):
        run_smoke_workflow(session, url="https://example.test/damai")

    assert session.started is True
    assert session.stopped is True
