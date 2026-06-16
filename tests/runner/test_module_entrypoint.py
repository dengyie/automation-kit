import subprocess
import sys
import runpy
from unittest.mock import Mock

import pytest

import automation_runner.__main__ as module_entrypoint
import automation_runner.cli as cli


def test_runner_module_entrypoint_executes_dry_run():
    result = subprocess.run(
        [sys.executable, "-m", "automation_runner", "examples", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "damai-web-smoke" in result.stdout
    assert "dry-run" in result.stdout


def test_module_entrypoint_run_delegates_to_cli_main(monkeypatch):
    fake_main = Mock(return_value=7)
    monkeypatch.setattr(module_entrypoint, "main", fake_main)

    assert module_entrypoint.run() == 7

    fake_main.assert_called_once_with()


def test_module_entrypoint_script_exits_with_delegated_code(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda: 4)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(module_entrypoint.__file__, run_name="__main__")

    assert exc_info.value.code == 4
