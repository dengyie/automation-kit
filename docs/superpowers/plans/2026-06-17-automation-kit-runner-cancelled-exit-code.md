# Runner Cancelled Exit Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return a distinct CLI exit code for cancelled workflow runs while leaving report payloads and other runner error codes unchanged.

**Architecture:** Keep the change in `automation_runner.cli`. Add tests first for cancelled JSON and plain-text runs, then introduce a tiny helper that maps workflow result state to exit code. Leave `automation_core`, report schema, and startup/config error handling unchanged.

**Tech Stack:** Python CLI code, pytest, existing runner/example workflow fixtures.

---

### Task 1: Add Failing Cancelled Exit Code Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Tighten the existing cancelled JSON test**

Update the existing cancelled JSON report test so it expects a distinct
cancelled exit code:

```python
def test_cli_emits_json_report_when_workflow_is_cancelled(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_cancelled_workflow",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 130
    assert report["workflow"] == "tests.runner.fixtures:create_cancelled_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_cancelled_workflow"
    assert report["success"] is False
    assert report["status"] == "cancelled"
    assert report["run_state"]["status"] == "cancelled"
    assert report["run_state"]["outcome"] == "cancelled"
```

- [ ] **Step 2: Add a plain-text cancelled workflow regression test**

Add this test near the other workflow-execution exit-code tests:

```python
def test_cli_returns_cancelled_exit_code_without_json(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_cancelled_workflow",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 130
    assert captured.out == "tests.runner.fixtures:create_cancelled_workflow success=False\n"
    assert captured.err == ""
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_is_cancelled tests/runner/test_cli.py::test_cli_returns_cancelled_exit_code_without_json --no-cov -q
```

Expected: both tests fail because cancelled runs currently return exit code `1`.

### Task 2: Implement Cancelled Exit Code Mapping

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Add a small result-to-exit-code helper**

Add a helper near the existing report helpers:

```python
def _workflow_exit_code(result: ExampleWorkflowResult) -> int:
    if result.state == TaskState.CANCELLED:
        return 130
    return 0 if result.success else 1
```

- [ ] **Step 2: Reuse the helper in both run output paths**

Replace the duplicated return expressions at the end of the run command:

```python
            return _workflow_exit_code(result)
        else:
            print(f"{workflow_name} success={result.success}")
        return _workflow_exit_code(result)
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_is_cancelled tests/runner/test_cli.py::test_cli_returns_cancelled_exit_code_without_json --no-cov -q
```

Expected: `2 passed`.

- [ ] **Step 4: Run runner regression coverage**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Expected: the full CLI test module passes.

### Task 3: Documentation, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the cancelled exit-code contract**

Add a short note to the user-facing docs that cancelled runs:

- keep `success=false`,
- keep `status="cancelled"` in JSON reports,
- return CLI exit code `130`.

- [ ] **Step 2: Record the slice in the development log**

Append a `2026-06-17: Runner Cancelled Exit Code` section that records:

- the new cancelled exit code contract,
- focused red and green test results,
- full CLI and full-suite verification,
- production review results,
- confirmation that `automation_core` stays unchanged.

- [ ] **Step 3: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 4: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 5: Commit and push**

Run:

```bash
git add automation_runner tests README.md docs
git commit -m "fix: distinguish cancelled runner exit codes"
git push origin main
```
