import subprocess
import sys


def test_runner_module_entrypoint_executes_dry_run():
    result = subprocess.run(
        [sys.executable, "-m", "automation_runner", "examples", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "damai-web-smoke" in result.stdout
    assert "dry-run" in result.stdout
