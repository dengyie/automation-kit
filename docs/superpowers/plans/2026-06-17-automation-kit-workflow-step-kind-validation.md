# Workflow Step Kind Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject unsupported `WorkflowStep.kind` values with a clear structured failure while preserving evidence from already completed steps.

**Architecture:** Keep the validation in `examples.workflows`. Add one focused failing test first, then make the smallest change in `run_workflow_steps(...)` so unsupported kinds fail explicitly after flushing any already queued actions. Leave `automation_core`, adapters, and runner report schema unchanged.

**Tech Stack:** Python dataclasses, example workflow helpers, pytest.

---

### Task 1: Add A Failing Unknown-Step Regression Test

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Add the failing regression test**

Add this test near the other `run_workflow_steps(...)` tests:

```python
def test_run_workflow_steps_rejects_unknown_step_kind_and_preserves_prior_results():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.artifact("screenshot", "home.png"),
            WorkflowStep(kind="navigate", name="next"),
        ],
    )

    assert result.success is False
    assert result.error == "ValueError: unsupported workflow step kind: navigate"
    assert [action.message for action in result.actions] == ["open"]
    assert result.batch_result is not None
    assert [action.message for action in result.batch_result.results] == ["open"]
    assert [artifact.path for artifact in result.artifacts] == [Path("home.png")]
    assert session.actions == [("open", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]
    assert session.stopped is True
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_run_workflow_steps_rejects_unknown_step_kind_and_preserves_prior_results --no-cov -q
```

Expected: fail because unsupported step kinds are not currently rejected with a
direct structured error.

### Task 2: Implement Explicit Step-Kind Validation

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Reject unsupported step kinds inside the loop**

In `run_workflow_steps(...)`, after the `action` branch and before artifact
capture, add a small unsupported-kind branch:

```python
            if step.kind != "artifact":
                if not flush_actions():
                    break
                return ExampleWorkflowResult(
                    session=session.info,
                    state=TaskState.FAILED,
                    success=False,
                    actions=actions,
                    artifacts=artifacts,
                    batch_result=current_batch_result(),
                    error=f"ValueError: unsupported workflow step kind: {step.kind}",
                )
```

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_run_workflow_steps_rejects_unknown_step_kind_and_preserves_prior_results --no-cov -q
```

Expected: `1 passed`.

- [ ] **Step 3: Run example regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Expected: existing example workflow behavior stays green.

### Task 3: Documentation, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the boundary**

Add a short note to the workflow guide that unsupported `WorkflowStep.kind`
values fail explicitly in `run_workflow_steps(...)` rather than being treated
as artifact steps.

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Workflow Step Kind Validation` section to
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
git commit -m "fix: validate workflow step kinds"
git push origin main
```
