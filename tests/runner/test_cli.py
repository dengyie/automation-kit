import json
from pathlib import Path

from automation_runner.cli import main
from tests.runner import fixtures


def test_cli_lists_example_workflows_without_live_execution(capsys):
    exit_code = main(["examples", "--dry-run"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "damai-web-smoke" in captured.out
    assert "damai-android-smoke" in captured.out
    assert "dry-run" in captured.out


def test_pyproject_exposes_runner_script():
    content = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'automation-runner = "automation_runner.cli:main"' in content


def test_cli_runs_dry_workflow_without_live_flag(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["success"] is True
    assert report["live"] is False
    assert report["workflow_factory"] is None
    assert report["session"] == {
        "driver_name": "dry-run",
        "platform": "dry",
        "identifier": "damai-web-smoke-dry-run",
    }
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "artifact",
        "task.end",
    ]
    assert report["events"][0]["task_id"] == "damai-web-smoke-dry-run"
    assert report["events"][0]["payload"]["task_name"] == "damai-web-smoke"
    assert report["actions"] == [
        {"success": True, "message": "get"},
    ]
    assert fixtures.CREATED_SESSIONS == []


def test_cli_dry_workflow_does_not_load_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--factory",
            "missing.runner.module:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["live"] is False
    assert fixtures.CREATED_SESSIONS == []


def test_cli_requires_factory_for_live_workflow(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--factory" in captured.err


def test_cli_runs_live_damai_web_smoke_with_imported_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "success=True" in captured.out
    assert len(fixtures.CREATED_SESSIONS) == 1
    session = fixtures.CREATED_SESSIONS[0]
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("get", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]


def test_cli_requires_url_for_live_damai_web_smoke(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--url" in captured.err
    assert fixtures.CREATED_SESSIONS == []
    assert fixtures.IMPORT_ATTEMPTS == []


def test_cli_requires_app_id_for_live_damai_android_smoke(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-android-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--app-id" in captured.err
    assert fixtures.CREATED_SESSIONS == []
    assert fixtures.IMPORT_ATTEMPTS == []


def test_cli_validates_workflow_parameters_before_loading_factory(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "missing.runner.module:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--url" in captured.err


def test_cli_rejects_invalid_factory_import_path(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures.make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "module:object" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_missing_factory_object(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:missing_factory",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "could not load factory" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_runs_live_damai_android_smoke_with_imported_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-android-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--app-id",
            "cn.damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "success=True" in captured.out
    assert len(fixtures.CREATED_SESSIONS) == 1
    session = fixtures.CREATED_SESSIONS[0]
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("activate_app", {"app_id": "cn.damai"})]
    assert session.artifacts == [
        ("screenshot", "startup.png"),
        ("page_source", "startup.xml"),
    ]


def test_cli_can_emit_json_report_for_live_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] == "tests.runner.fixtures:make_session"
    assert report["success"] is True
    assert report["status"] == "succeeded"
    assert report["run_id"] == "cli-run"
    assert report["live"] is True
    assert isinstance(report["elapsed_seconds"], float)
    assert report["elapsed_seconds"] >= 0
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "artifact",
        "task.end",
    ]
    assert report["events"][0]["task_id"] == "cli-run"
    assert report["events"][0]["payload"]["task_name"] == "damai-web-smoke"
    assert report["events"][1]["payload"] == {
        "task_name": "damai-web-smoke",
        "task_id": "cli-run",
        "artifact_type": "screenshot",
        "path": "home.png",
    }
    assert report["events"][2]["payload"]["outcome"] == "succeeded"
    assert report["error"] is None
    assert report["session"] == {
        "driver_name": "fake-cli",
        "platform": "web",
        "identifier": "cli-run",
    }
    assert report["actions"] == [
        {"success": True, "message": "get"},
    ]
    assert report["artifacts"] == [
        {"artifact_type": "screenshot", "path": "home.png"},
    ]
    assert "data" not in report["actions"][0]


def test_cli_can_write_json_report_to_file(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == captured.out.strip()
    assert "damai-web-smoke" in captured.out


def test_cli_emits_json_report_when_workflow_fails(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "failed.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_failing_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report_path.read_text(encoding="utf-8") == captured.out.strip()
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] == "tests.runner.fixtures:make_failing_session"
    assert report["success"] is False
    assert report["status"] == "failed"
    assert report["run_id"] == "cli-run"
    assert report["live"] is True
    assert report["error"] == "RuntimeError: get failed"
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert report["events"][1]["payload"] == {
        "task_name": "damai-web-smoke",
        "task_id": "cli-run",
        "message": "get failed",
        "error_type": "RuntimeError",
    }
    assert report["events"][2]["payload"]["outcome"] == "failed"
    assert report["actions"] == []
    assert report["artifacts"] == []
    assert fixtures.CREATED_SESSIONS[0].stopped is True


def test_cli_creates_report_file_parent_directories(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "nested" / "reports" / "report.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    capsys.readouterr()

    assert exit_code == 0
    assert report_path.exists()


def test_cli_rejects_report_file_without_json(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--report-file",
            "report.json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--report-file requires --json" in captured.err
