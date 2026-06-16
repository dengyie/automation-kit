# Safe Action Batch Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make runner `action_batch` JSON output safe by omitting raw action result `data` and skipped action parameters.

**Architecture:** Keep full `ActionBatchResult.to_dict()` behavior in `automation_core.actions`, and add report-specific serialization in `automation_runner.reports`. Runner reports remain useful for operators while avoiding raw automation payloads.

**Tech Stack:** Python dataclasses, pytest, existing runner report tests.

---

## Task 1: Add Failing Report Safety Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`

- [x] **Step 1: Strengthen action_batch report test**

Update `test_build_report_serializes_action_batch_summary` so the batch result
contains raw data and skipped parameters:

```python
batch_result=ActionBatchResult(
    results=[
        ActionResult(
            success=True,
            message="get",
            data={"auth_token": "secret-token", "url": "https://example.test"},
        )
    ],
    skipped=[
        ActionRequest(
            name="after",
            parameters={"password": "secret", "selector": "#buy"},
        )
    ],
)
```

Assert the report-safe output is:

```python
assert report["action_batch"] == {
    "results": [
        {
            "success": True,
            "message": "get",
        },
    ],
    "skipped": [
        {
            "name": "after",
            "stop_on_failure": True,
        },
    ],
    "success": True,
}
```

- [x] **Step 2: Run red report test**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_action_batch_summary --no-cov -q
```

Expected: fail because runner reports currently include `data` and skipped
`parameters` in `action_batch`.

## Task 2: Add Runner-Safe Action Batch Serialization

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`

- [x] **Step 1: Replace direct `ActionBatchResult.to_dict()` usage**

Change `_serialize_action_batch(...)` to return:

```python
{
    "results": [
        {
            "success": result.success,
            "message": result.message,
        }
        for result in batch_result.results
    ],
    "skipped": [
        {
            "name": action.name,
            "stop_on_failure": action.stop_on_failure,
        }
        for action in batch_result.skipped
    ],
    "success": batch_result.success,
}
```

Keep returning `None` when `batch_result` is `None`.

- [x] **Step 2: Run green report test**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_action_batch_summary --no-cov -q
```

Expected: pass.

- [x] **Step 3: Run focused runner and action tests**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py tests/actions/test_action_models.py --no-cov -q
```

Expected: runner report tests pass and core action serialization tests remain
unchanged.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/artifacts.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document safe action_batch output**

Document that `action_batch` preserves executed/skipped status but omits raw
result `data` and skipped parameters.

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
git commit -m "fix: sanitize action batch reports"
git push origin main
```
