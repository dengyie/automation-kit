# Automation Kit Report Workflow Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe `workflow_context` summary to runner JSON reports.

**Architecture:** Keep report serialization in `automation_runner.reports`. Reuse the runner-layer `WorkflowContext` model and do not add report behavior to `automation_core`. Preserve existing top-level report fields for compatibility.

**Tech Stack:** Python dataclasses, pytest, existing `automation_runner` report and CLI code.

---

## Task 1: Serialize Workflow Context In Reports

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`

- [ ] **Step 1: Write failing report test**

Add a test that calls:

```python
from automation_runner.context import WorkflowContext

report = build_report(
    "custom",
    result,
    workflow_context=WorkflowContext(
        workflow_name="custom",
        live=True,
        workflow_factory="pkg:create",
        session_factory="pkg:session",
    ),
).to_dict()
```

Expected:

```python
assert report["workflow_context"] == {
    "workflow_name": "custom",
    "live": True,
    "workflow_factory": "pkg:create",
    "session_factory": "pkg:session",
}
```

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
```

Expected: fail because `build_report` has no `workflow_context` parameter.

- [ ] **Step 2: Implement report serialization**

Add `workflow_context: Dict[str, object]` to `RunnerReport` and serialize a
safe dictionary from `WorkflowContext`.

- [ ] **Step 3: Preserve default behavior**

When callers do not pass a context, derive one from existing report arguments:
`workflow`, `live`, `workflow_factory`, and `session_factory`.

- [ ] **Step 4: Verify report tests**

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
```

Expected: pass.

## Task 2: Wire CLI Context Into Reports

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add CLI assertion**

Extend the custom context workflow CLI test to assert:

```python
assert report["workflow_context"] == {
    "workflow_name": "tests.runner.fixtures:create_context_workflow",
    "live": True,
    "workflow_factory": "tests.runner.fixtures:create_context_workflow",
    "session_factory": "tests.runner.fixtures:make_session",
}
```

- [ ] **Step 2: Pass context to `build_report`**

Use the same context object created for custom workflow factories when building
the JSON report.

- [ ] **Step 3: Verify runner tests**

Run:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Expected: pass.

## Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document `workflow_context`**

Add `workflow_context` to the report contract and explain that raw
`WorkflowOptions` are not serialized.

- [ ] **Step 2: Run verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass.

- [ ] **Step 3: Run production review scripts**

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
git commit -m "feat: include workflow context in reports"
git push origin main
```
