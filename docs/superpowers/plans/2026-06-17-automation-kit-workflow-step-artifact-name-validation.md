# Workflow Step Artifact Name Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject invalid artifact names in `WorkflowStep.artifact(...)` so workflow authors get direct feedback before runtime execution.

**Architecture:** Keep the validation inside `examples.workflows`, next to the `WorkflowStep` helper. Add focused constructor-level tests first, then implement one small validation helper reused by `WorkflowStep.artifact(...)`. Leave `automation_core`, adapters, and runner behavior unchanged.

**Tech Stack:** Python dataclasses, example workflow helpers, pytest.

---

### Task 1: Add Failing Artifact-Name Validation Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Add invalid artifact-name constructor tests**

Add these tests near the other `WorkflowStep` helper coverage:

```python
@pytest.mark.parametrize("name", ["", "   ", ".", ".."])
def test_workflow_step_artifact_rejects_invalid_name(name):
    with pytest.raises(ValueError, match="invalid workflow artifact name"):
        WorkflowStep.artifact("screenshot", name)


@pytest.mark.parametrize("name", [None, 123])
def test_workflow_step_artifact_rejects_non_string_name(name):
    with pytest.raises(ValueError, match="invalid workflow artifact name"):
        WorkflowStep.artifact("screenshot", name)


def test_workflow_step_artifact_allows_valid_name():
    step = WorkflowStep.artifact("screenshot", "home.png")

    assert step.kind == "artifact"
    assert step.name == "screenshot"
    assert step.parameters == {"name": "home.png"}
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'artifact_rejects_invalid_name or artifact_allows_valid_name' --no-cov -q
```

Expected: the invalid-name test fails because `WorkflowStep.artifact(...)` does
not currently validate the name.

### Task 2: Implement Constructor-Level Validation

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add a small artifact-name validator**

Add a local helper near the `WorkflowStep` dataclass:

```python
def _validate_workflow_artifact_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("invalid workflow artifact name")
    cleaned = name.replace("\\", "/").split("/")[-1].strip()
    if cleaned in {"", ".", ".."}:
        raise ValueError("invalid workflow artifact name")
    return name
```

- [ ] **Step 2: Use the validator in `WorkflowStep.artifact(...)`**

Update the constructor helper to validate before building the step:

```python
    @classmethod
    def artifact(cls, artifact_type: str, name: str) -> "WorkflowStep":
        return cls(
            kind="artifact",
            name=artifact_type,
            parameters={"name": _validate_workflow_artifact_name(name)},
        )
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'artifact_rejects_invalid_name or artifact_allows_valid_name' --no-cov -q
```

Expected: the focused artifact-name tests pass.

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

Add a short note that `WorkflowStep.artifact(...)` rejects invalid artifact
names such as empty or traversal-like values before runtime execution.

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Workflow Step Artifact Name Validation` section to
`docs/development-log.md` with:

- focused red and green results,
- example regression results,
- full-suite results,
- production review notes,
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
git add examples tests docs
git commit -m "fix: validate workflow step artifact names"
git push origin main
```
