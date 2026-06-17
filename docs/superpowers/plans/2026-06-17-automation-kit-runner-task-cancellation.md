# Runner Task Cancellation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach `automation_runner` to preserve task cancellation as a distinct terminal state in workflow execution and JSON reports.

**Architecture:** Keep the cancellation signal in `automation_core.tasks.TaskCancelledError`, but let runner-layer code translate it into report status, run state, and CLI exit behavior. Update tests first so the new cancelled branch is explicit, then make the smallest runner/report changes necessary. Leave success/failure and startup-error paths unchanged.

**Tech Stack:** Python runner code, JSON report serialization, pytest, existing workflow/example fixtures.

---

### Task 1: Add Failing Runner Cancellation Coverage

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/fixtures.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`

- [ ] **Step 1: Add a cancelling workflow factory fixture**

Add this to `tests/runner/fixtures.py`:

```python
from automation_core.tasks import TaskCancelledError


def create_cancelled_workflow(session_factory):
    def run_fn(session):
        raise TaskCancelledError("user requested stop")

    return ExampleWorkflow(
        name="cancelled-workflow",
        session_factory=session_factory,
        run_fn=run_fn,
    )
```

- [ ] **Step 2: Add a CLI red test**

Add this test to `tests/runner/test_cli.py`:

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

    assert exit_code == 0
    assert report["workflow"] == "tests.runner.fixtures:create_cancelled_workflow"
    assert report["success"] is False
    assert report["status"] == "cancelled"
    assert report["run_state"]["status"] == "cancelled"
    assert report["run_state"]["outcome"] == "cancelled"
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "task.end",
    ]
    assert report["events"][-1]["payload"]["outcome"] == "cancelled"
```

- [ ] **Step 3: Add a report serialization test**

Add this test to `tests/runner/test_reports.py`:

```python
def test_build_report_serializes_cancelled_run_state():
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

    run_state = RunState(
        run_id="run-1",
        status=RunStatus.CANCELLED,
        started_at=1.25,
        finished_at=2.5,
        outcome="cancelled",
    )

    report = build_report("damai-web-smoke", result, run_state=run_state).to_dict()

    assert report["status"] == "failed"
    assert report["run_state"]["status"] == "cancelled"
    assert report["run_state"]["outcome"] == "cancelled"
```

- [ ] **Step 4: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py tests/runner/test_reports.py --no-cov -q
```

Expected: fail because cancellation is still reported as failure.

### Task 2: Implement Runner Cancellation Handling

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/runner.py` if needed

- [ ] **Step 1: Import and branch on `TaskCancelledError`**

In the runner/CLI code path, catch `automation_core.tasks.TaskCancelledError` separately from ordinary exceptions and map it to a cancelled terminal state.

- [ ] **Step 2: Extend the report state mapping**

Ensure `build_report(...)` can emit `status="cancelled"` when the run state is cancelled while leaving ordinary success/failure output intact.

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py tests/runner/test_reports.py --no-cov -q
```

Expected: pass.

### Task 3: Document And Ship

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document cancelled workflow reporting**

Update the workflow guide to note that cancelled runs are reported distinctly from failed runs.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Runner Task Cancellation` section to
`docs/development-log.md` with the red/green results, full verification,
review summary, and the note that `automation_core` remains business-agnostic.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_runner tests docs
git commit -m "fix: report cancelled workflows distinctly"
git push origin main
```
