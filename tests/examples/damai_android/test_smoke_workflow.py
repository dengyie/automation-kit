from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.execution import FailureCategory
from examples.damai_android import build_steps, create_workflow


class FakeAppiumSession:
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
        return ActionResult(success=True, message=action_name)

    def capture_artifact(self, artifact_type, name):
        self.artifacts.append((artifact_type, name))
        return ArtifactHandle(artifact_type=artifact_type, path=Path(name))


def test_damai_android_steps_declare_app_launch_and_artifacts():
    steps = build_steps("cn.damai")

    assert [(step.kind, step.name) for step in steps] == [
        ("action", "launch_app"),
        ("artifact", "screenshot"),
        ("artifact", "page_source"),
    ]
    assert steps[0].parameters == {"app_id": "cn.damai"}


def test_damai_android_workflow_runs_against_injected_session():
    session = FakeAppiumSession()
    workflow = create_workflow(session_factory=lambda: session, app_id="cn.damai")

    result = workflow.run()

    assert workflow.name == "damai-android-smoke"
    assert result.status.value == "succeeded"
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("launch_app", {"app_id": "cn.damai"})]
    assert session.artifacts == [
        ("screenshot", "startup.png"),
        ("page_source", "startup.xml"),
    ]
    assert list(result.artifacts)[0].artifact_type == "screenshot"


def test_damai_android_workflow_reports_provider_failure():
    class FailingSession(FakeAppiumSession):
        def execute_action(self, action_name, **kwargs):
            raise ConnectionError("device offline")

    session = FailingSession()
    workflow = create_workflow(session_factory=lambda: session, app_id="cn.damai")

    result = workflow.run()

    assert result.status.value == "failed"
    assert result.failure.category is FailureCategory.PROVIDER
    assert result.failure.details == {"error_type": "ConnectionError"}
    assert session.stopped is True
