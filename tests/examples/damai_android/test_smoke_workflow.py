from pathlib import Path

import pytest

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from examples.damai_android import create_workflow, run_smoke_workflow


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(
            driver_name="fake-appium",
            platform="android",
            identifier="android-run",
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


def test_damai_android_smoke_workflow_starts_app_and_captures_artifacts():
    session = FakeSession()

    result = run_smoke_workflow(session, app_id="cn.damai")

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert result.session == session.info
    assert result.actions[0].message == "activate_app"
    assert session.actions == [("activate_app", {"app_id": "cn.damai"})]
    assert session.artifacts == [
        ("screenshot", "startup.png"),
        ("page_source", "startup.xml"),
    ]


def test_damai_android_smoke_workflow_factory_returns_runnable_workflow():
    session = FakeSession()
    workflow = create_workflow(session_factory=lambda: session, app_id="cn.damai")

    result = workflow.run()

    assert workflow.name == "damai-android-smoke"
    assert result.success is True
    assert session.actions == [("activate_app", {"app_id": "cn.damai"})]
    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "artifact",
        "task.end",
    ]
    assert result.events[0].payload["task_name"] == "damai-android-smoke"
    assert result.events[-1].payload["outcome"] == "succeeded"


def test_damai_android_workflow_factory_returns_failure_result():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("activation failed")

    session = FailingSession()
    workflow = create_workflow(session_factory=lambda: session, app_id="cn.damai")

    result = workflow.run()

    assert result.success is False
    assert result.error == "RuntimeError: activation failed"
    assert result.actions == []
    assert result.artifacts == []
    assert [event.event_type for event in result.events] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert result.events[1].payload["error_type"] == "RuntimeError"
    assert session.stopped is True


def test_damai_android_smoke_workflow_stops_session_when_action_fails():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("activation failed")

    session = FailingSession()

    with pytest.raises(RuntimeError, match="activation failed"):
        run_smoke_workflow(session, app_id="cn.damai")

    assert session.started is True
    assert session.stopped is True
