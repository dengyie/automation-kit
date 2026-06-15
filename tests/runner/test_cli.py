from pathlib import Path

from automation_runner.cli import main


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
