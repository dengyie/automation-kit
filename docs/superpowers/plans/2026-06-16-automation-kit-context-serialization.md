# Automation Kit Context Serialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable dictionary serialization to runner context models.

**Architecture:** Keep serialization on the runner-side dataclasses. Reuse
`WorkflowContext.to_dict()` inside report serialization so the report contract
stays aligned with the typed model. Do not add raw workflow options to the
JSON report.

**Tech Stack:** Python dataclasses, pytest, existing `automation_runner`
context/report code.

---

## Task 1: Add Context Model Serialization

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/context.py`
- Test: `/Users/mango/project/codex/automation-kit/tests/runner/test_context.py`

- [ ] **Step 1: Write failing tests**

```python
def test_workflow_context_to_dict():
    context = WorkflowContext(
        workflow_name="custom",
        live=True,
        workflow_factory="pkg:create",
        session_factory="pkg:session",
    )

    assert context.to_dict() == {
        "workflow_name": "custom",
        "live": True,
        "workflow_factory": "pkg:create",
        "session_factory": "pkg:session",
    }


def test_workflow_options_to_dict():
    options = WorkflowOptions(
        url="https://example.test/damai",
        app_id="cn.damai",
        emit_json=True,
        report_file="reports/run.json",
    )

    assert options.to_dict() == {
        "url": "https://example.test/damai",
        "app_id": "cn.damai",
        "emit_json": True,
        "report_file": "reports/run.json",
    }
```

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: fail because the methods do not exist.

- [ ] **Step 2: Implement serialization**

Add `to_dict()` methods to both dataclasses using explicit dictionaries.

- [ ] **Step 3: Verify**

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: pass.

## Task 2: Reuse Context Serialization In Reports

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`

- [ ] **Step 1: Update report test**

Keep the existing `workflow_context` assertion and verify it comes from
`WorkflowContext.to_dict()`.

- [ ] **Step 2: Reuse serialization**

Call `workflow_context.to_dict()` in `build_report`.

- [ ] **Step 3: Verify**

Run:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Expected: pass.

## Task 3: Docs, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document serialization helpers**

Explain that `WorkflowContext.to_dict()` is report-safe and that raw workflow
options still are not serialized in reports.

- [ ] **Step 2: Run verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Commit and push**

```bash
git add automation_runner tests docs
git commit -m "feat: add context serialization helpers"
git push origin main
```
