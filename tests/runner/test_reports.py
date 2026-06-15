from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_runner.reports import build_report
from examples.workflows import ExampleWorkflowResult


def test_build_report_serializes_safe_workflow_summary():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=True,
        actions=[
            ActionResult(
                success=True,
                message="get",
                data={"token": "do-not-serialize"},
            ),
        ],
        artifacts=[
            ArtifactHandle(
                artifact_type="screenshot",
                path=Path("artifacts/run-1/screenshot/home.png"),
            ),
        ],
    )

    report = build_report("damai-web-smoke", result).to_dict()

    assert report == {
        "workflow": "damai-web-smoke",
        "success": True,
        "session": {
            "driver_name": "fake",
            "platform": "web",
            "identifier": "run-1",
        },
        "actions": [
            {
                "success": True,
                "message": "get",
            },
        ],
        "artifacts": [
            {
                "artifact_type": "screenshot",
                "path": "artifacts/run-1/screenshot/home.png",
            },
        ],
    }
