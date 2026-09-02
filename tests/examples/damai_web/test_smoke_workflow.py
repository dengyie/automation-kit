import json
from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_runner.dry_run import DryRunSession
from automation_runner.reports import build_report_v2
from examples.damai_web import build_steps, create_workflow


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


def test_damai_web_steps_are_declared_in_business_order():
    steps = build_steps("https://example.test/damai")

    assert [(step.kind, step.name) for step in steps] == [
        ("action", "open"),
        ("artifact", "screenshot"),
    ]
    assert steps[0].parameters == {"url": "https://example.test/damai"}


def test_damai_web_workflow_runs_against_injected_session():
    session = FakeSession()
    workflow = create_workflow(
        session_factory=lambda: session,
        url="https://example.test/damai",
    )

    result = workflow.run()

    assert workflow.name == "damai-web-smoke"
    assert result.status.value == "succeeded"
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("open", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]
    assert [step.kind.value for step in result.steps] == ["action", "artifact"]
    assert [event["event_type"] for event in result.events] == [
        "workflow.start",
        "step.start",
        "action.end",
        "step.end",
        "step.start",
        "artifact",
        "step.end",
        "workflow.end",
    ]


def test_damai_web_workflow_reports_provider_failure_without_raw_text():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation refused by browser")

    session = FailingSession()
    workflow = create_workflow(
        session_factory=lambda: session,
        url="https://example.test/damai",
    )

    result = workflow.run()
    payload = json.dumps(build_report_v2(result).to_dict())

    assert result.status.value == "failed"
    assert result.failure.category.value == "provider"
    assert result.failure.code == "action_execution_failed"
    assert "navigation refused by browser" not in payload
    assert session.stopped is True


def test_damai_web_workflow_runs_against_dry_run_session():
    workflow = create_workflow(
        session_factory=lambda: DryRunSession("damai-web-smoke"),
        url="https://example.test/damai",
    )

    result = workflow.run()
    payload = build_report_v2(result).to_dict()

    assert result.status.value == "succeeded"
    assert payload["artifacts"][0]["path"] == (
        "artifacts/damai-web-smoke-dry-run/screenshot/home.png"
    )
