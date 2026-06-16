# Runner Startup Failure Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured `task.start`, `error`, and `task.end` events to runner startup failure JSON reports.

**Architecture:** Keep the change in `automation_runner.cli` by enriching the fallback `ExampleWorkflowResult` created when `runner.run()` raises. Reuse the existing `automation_core.events` event dataclasses so report serialization stays unchanged. Do not touch normal `ExampleWorkflow.run()` behavior.

**Tech Stack:** Python dataclasses, pytest, existing CLI/report tests.

---

## Task 1: Add Failing Event Assertions

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Assert session startup failure events**

Extend `test_cli_emits_json_report_when_session_factory_fails` with:

```python
assert [event["event_type"] for event in report["events"]] == [
    "task.start",
    "error",
    "task.end",
]
assert report["events"][0]["task_id"] == "damai-web-smoke-failed-run"
assert report["events"][1]["payload"] == {
    "task_name": "damai-web-smoke",
    "task_id": "damai-web-smoke-failed-run",
    "message": "session startup failed",
    "error_type": "RuntimeError",
}
assert report["events"][2]["payload"]["outcome"] == "failed"
```

- [x] **Step 2: Assert custom workflow construction failure events**

Extend `test_cli_emits_json_report_when_custom_workflow_factory_fails` with:

```python
assert [event["event_type"] for event in report["events"]] == [
    "task.start",
    "error",
    "task.end",
]
assert report["events"][1]["payload"] == {
    "task_name": "tests.runner.fixtures:create_raising_workflow",
    "task_id": "tests.runner.fixtures:create_raising_workflow-failed-run",
    "message": "workflow construction failed",
    "error_type": "RuntimeError",
}
```

- [x] **Step 3: Run red verification**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'session_factory_fails or custom_workflow_factory_fails' --no-cov -q
```

Expected: fail because startup failure reports currently have no events.

## Task 2: Add Fallback Failure Events

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Import existing event dataclasses**

Add imports for:

```python
from automation_core.events import ErrorEvent, TaskEndEvent, TaskStartEvent
```

- [x] **Step 2: Build events in `_failure_result(...)`**

Use the fallback run id once:

```python
task_id = f"{workflow_name}-failed-run"
```

Set `events` on the fallback result to:

```python
events=[
    TaskStartEvent(task_name=workflow_name, task_id=task_id).to_envelope(),
    ErrorEvent(
        task_name=workflow_name,
        task_id=task_id,
        message=str(exc),
        error_type=type(exc).__name__,
    ).to_envelope(),
    TaskEndEvent(
        task_name=workflow_name,
        task_id=task_id,
        outcome="failed",
    ).to_envelope(),
]
```

- [x] **Step 3: Run green verification**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'session_factory_fails or custom_workflow_factory_fails' --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document startup failure event shape**

Document that startup failure reports include `task.start`, `error`, and
`task.end` events when `--json` is enabled.

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
git commit -m "feat: add startup failure events"
git push origin main
```
