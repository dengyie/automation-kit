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

    report = build_report("damai-web-smoke", result, live=True).to_dict()

    assert report == {
        "workflow": "damai-web-smoke",
        "workflow_factory": None,
        "success": True,
        "status": "succeeded",
        "run_id": "run-1",
        "live": True,
        "elapsed_seconds": None,
        "events": [],
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
        "error": None,
    }


def test_build_report_defaults_to_non_live():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=False,
        actions=[],
        artifacts=[],
    )

    report = build_report("damai-web-smoke", result).to_dict()

    assert report["live"] is False
    assert report["run_id"] == "run-1"
    assert report["status"] == "failed"
    assert report["events"] == []


def test_build_report_records_factory_elapsed_and_error_summary():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=False,
        actions=[],
        artifacts=[],
    )

    report = build_report(
        "damai-web-smoke",
        result,
        workflow_factory="tests.runner.fixtures:make_session",
        elapsed_seconds=0.25,
        error="workflow failed",
    ).to_dict()

    assert report["workflow_factory"] == "tests.runner.fixtures:make_session"
    assert report["elapsed_seconds"] == 0.25
    assert report["error"] == "workflow failed"
