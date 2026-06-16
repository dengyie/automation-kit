# Runner Failure Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CLI JSON/report-file output stable when workflow construction or session startup fails before a workflow returns a normal result.

**Architecture:** Keep failure reporting in `automation_runner.cli` and reuse `automation_runner.reports.build_report(...)`. Build an `ExampleWorkflowResult` with a synthetic `SessionInfo` only when no real session result exists. Leave `automation_core` and adapter contracts unchanged.

**Tech Stack:** Python dataclasses, pytest, existing runner CLI and report serialization.

---

## Task 1: Add Failing CLI Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/fixtures.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Add failing fixture helpers**

Add these helpers to `tests/runner/fixtures.py`:

```python
def raise_session_startup():
    raise RuntimeError("session startup failed")


def create_raising_workflow(session_factory):
    raise RuntimeError("workflow construction failed")
```

- [x] **Step 2: Add session startup failure JSON test**

Add this test to `tests/runner/test_cli.py`:

```python
def test_cli_emits_json_report_when_session_factory_fails(tmp_path, capsys):
    report_path = tmp_path / "startup-failed.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:raise_session_startup",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report_path.read_text(encoding="utf-8") == captured.out
    assert report["workflow"] == "damai-web-smoke"
    assert report["success"] is False
    assert report["status"] == "failed"
    assert report["run_id"] == "damai-web-smoke-failed-run"
    assert report["run_state"]["status"] == "failed"
    assert report["live"] is True
    assert report["session"] == {
        "driver_name": "unavailable",
        "platform": "unknown",
        "identifier": "damai-web-smoke-failed-run",
    }
    assert report["actions"] == []
    assert report["artifacts"] == []
    assert report["error"] == "RuntimeError: session startup failed"
```

- [x] **Step 3: Add workflow construction failure JSON test**

Add this test to `tests/runner/test_cli.py`:

```python
def test_cli_emits_json_report_when_custom_workflow_factory_fails(capsys):
    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_raising_workflow",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report["workflow"] == "tests.runner.fixtures:create_raising_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_raising_workflow"
    assert report["success"] is False
    assert report["run_id"] == "tests.runner.fixtures:create_raising_workflow-failed-run"
    assert report["error"] == "RuntimeError: workflow construction failed"
```

- [x] **Step 4: Run red verification**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Expected: tests fail because the exceptions still escape from CLI execution.

## Task 2: Implement CLI Failure Report Helper

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Add fallback result helper**

Add a helper that builds an `ExampleWorkflowResult`:

```python
def _failure_result(workflow_name: str, exc: Exception) -> ExampleWorkflowResult:
    return ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="unavailable",
            platform="unknown",
            identifier=f"{workflow_name}-failed-run",
        ),
        success=False,
        actions=[],
        artifacts=[],
        error=f"{type(exc).__name__}: {exc}",
    )
```

- [x] **Step 2: Add JSON/report emission helper**

Extract the existing report JSON emission into a helper that:

- accepts the report object,
- writes stdout,
- creates `--report-file` parents,
- writes the same payload to the file.

- [x] **Step 3: Catch runner execution exceptions**

Wrap `result = runner.run()` so exceptions become `_failure_result(...)` when
`config.emit_json` is true.

If `config.emit_json` is false, keep existing behavior simple and return an
error to stderr with exit code 1.

- [x] **Step 4: Preserve run state timing**

Build `RunState` from `result.session.identifier` after either successful
execution or fallback failure result. Mark it failed when `result.success` is
false.

- [x] **Step 5: Run green verification**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Expected: runner CLI tests pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document startup failure reports**

Document that JSON reports are emitted for startup failures when `--json` is
enabled, with `session.driver_name="unavailable"`.

- [x] **Step 2: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and diff check reports no whitespace errors.

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and no unresolved P0/P1/P2 findings remain.

- [ ] **Step 4: Commit and push**

```bash
git add automation_runner tests docs
git commit -m "feat: report runner startup failures"
git push origin main
```
