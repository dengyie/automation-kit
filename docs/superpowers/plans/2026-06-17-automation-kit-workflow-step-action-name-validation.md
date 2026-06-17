# Workflow Step Action Name Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject invalid action names in `WorkflowStep.action(...)` so workflow authors get direct feedback before runtime execution.

**Architecture:** Keep validation inside `examples.workflows`, next to the `WorkflowStep` helper. Add focused constructor-level tests first, then implement one small validation helper used by `WorkflowStep.action(...)`. Leave `automation_core`, adapters, and runner behavior unchanged.

**Tech Stack:** Python dataclasses, example workflow helpers, pytest.

---

### Task 1: Add Failing Action-Name Validation Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Add invalid action-name constructor tests**

Add these tests near the other `WorkflowStep` helper coverage:

```python
@pytest.mark.parametrize("name", ["", "   ", ".", ".."])
def test_workflow_step_action_rejects_invalid_name(name):
    with pytest.raises(ValueError, match="invalid workflow action name"):
        WorkflowStep.action(name)


@pytest.mark.parametrize("name", [None, 123])
def test_workflow_step_action_rejects_non_string_name(name):
    with pytest.raises(ValueError, match="invalid workflow action name"):
        WorkflowStep.action(name)


def test_workflow_step_action_allows_valid_name():
    step = WorkflowStep.action("open", url="https://example.test/damai")

    assert step.kind == "action"
    assert step.name == "open"
    assert step.parameters == {"url": "https://example.test/damai"}
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'action_rejects_invalid_name or action_rejects_non_string_name or action_allows_valid_name' --no-cov -q
```

Expected: the invalid-name tests fail because `WorkflowStep.action(...)` does
not currently validate the name.

### Task 2: Implement Constructor-Level Validation

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add a small action-name validator**

Add a local helper near `_validate_workflow_artifact_name(...)`:

```python
def _validate_workflow_action_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("invalid workflow action name")
    cleaned = name.replace("\\", "/").split("/")[-1].strip()
    if cleaned in {"", ".", ".."}:
        raise ValueError("invalid workflow action name")
    return name
```

- [ ] **Step 2: Use the validator in `WorkflowStep.action(...)`**

Update the constructor helper to validate before building the step:

```python
    @classmethod
    def action(cls, name: str, **parameters: object) -> "WorkflowStep":
        return cls(
            kind="action",
            name=_validate_workflow_action_name(name),
            parameters=parameters,
        )
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'action_rejects_invalid_name or action_rejects_non_string_name or action_allows_valid_name' --no-cov -q
```

Expected: the focused action-name tests pass.

- [ ] **Step 4: Run example regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Expected: existing example workflow behavior remains green.

### Task 3: Documentation, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the constructor boundary**

Add this note to the workflow-step documentation:

```markdown
`WorkflowStep.action(...)` rejects empty, traversal-like, or non-string action
names before a workflow run starts.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Workflow Step Action Name Validation` section to
`docs/development-log.md` with:

- focused red result,
- focused green result,
- example regression result,
- full-suite result,
- production review notes,
- confirmation that `automation_core` stays unchanged.

- [ ] **Step 3: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass, coverage remains above 80%, and `git diff --check`
has no output.

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
git add examples tests docs
git commit -m "fix: validate workflow step action names"
git push origin main
```
