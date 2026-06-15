from pathlib import Path

import pytest

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from examples.damai_web import create_workflow, run_smoke_workflow


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
    assert result.actions[0].message == "get"
    assert session.actions == [("get", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]


def test_damai_web_smoke_workflow_factory_returns_runnable_workflow():
    session = FakeSession()
    workflow = create_workflow(session_factory=lambda: session, url="https://example.test/damai")

    result = workflow.run()

    assert result.success is True
    assert session.actions == [("get", {"url": "https://example.test/damai"})]


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
    assert session.stopped is True


def test_damai_web_smoke_workflow_stops_session_when_action_fails():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()

    with pytest.raises(RuntimeError, match="navigation failed"):
        run_smoke_workflow(session, url="https://example.test/damai")

    assert session.started is True
    assert session.stopped is True
