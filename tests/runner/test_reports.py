from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.events import TaskStartEvent
from automation_core.state import RunState, RunStatus
from automation_runner.reports import build_report
from examples.workflows import ExampleWorkflowResult


def test_build_report_serializes_safe_workflow_summary():
    started_at = 1.5
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

    run_state = RunState(run_id="run-1", started_at=started_at)
    run_state.succeed(finished_at=2.5)

    report = build_report(
        "damai-web-smoke",
        result,
        run_state=run_state,
        live=True,
    ).to_dict()

    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] is None
    assert report["success"] is True
    assert report["status"] == "succeeded"
    assert report["run_id"] == "run-1"
    assert report["run_state"]["run_id"] == "run-1"
    assert report["run_state"]["status"] == "succeeded"
    assert report["run_state"]["started_at"] == started_at
    assert report["run_state"]["finished_at"] == 2.5
    assert report["run_state"]["outcome"] == "succeeded"
    assert report["live"] is True
    assert report["elapsed_seconds"] is None
    assert report["events"] == []
    assert report["session"] == {
        "driver_name": "fake",
        "platform": "web",
        "identifier": "run-1",
    }
    assert report["actions"] == [
        {
            "success": True,
            "message": "get",
        },
    ]
    assert report["artifacts"] == [
        {
            "artifact_type": "screenshot",
            "path": "artifacts/run-1/screenshot/home.png",
        },
    ]
    assert report["error"] is None


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
    assert report["run_state"]["status"] == "failed"
    assert report["run_state"]["outcome"] == "failed"
    assert report["events"] == []


def test_build_report_serializes_run_state():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=True,
        actions=[],
        artifacts=[],
    )

    run_state = RunState(
        run_id="run-1",
        status=RunStatus.SUCCEEDED,
        started_at=1.25,
        finished_at=2.5,
        outcome="ok",
    )

    report = build_report("damai-web-smoke", result, run_state=run_state).to_dict()

    assert report["run_state"] == {
        "run_id": "run-1",
        "status": "succeeded",
        "started_at": 1.25,
        "finished_at": 2.5,
        "outcome": "ok",
    }


def test_build_report_serializes_workflow_events():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=True,
        actions=[],
        artifacts=[],
        events=[
            TaskStartEvent(
                task_name="damai-web-smoke",
                task_id="run-1",
            ).to_envelope()
        ],
    )

    report = build_report("damai-web-smoke", result).to_dict()

    assert report["events"][0]["event_type"] == "task.start"
    assert report["events"][0]["task_id"] == "run-1"
    assert report["events"][0]["payload"] == {
        "task_name": "damai-web-smoke",
        "task_id": "run-1",
    }


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
