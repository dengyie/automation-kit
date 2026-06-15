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


def test_cli_refuses_live_workflow_without_live_flag(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--live" in captured.err
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
