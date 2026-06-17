# Workflow Task Event Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Avoid duplicate `task.start` and `task.end` events when a custom example workflow already returns matching lifecycle events.

**Architecture:** Keep the change in `examples.workflows`, where example workflow event assembly already lives. Add small matching helpers for task lifecycle events and use them before appending automatic outer lifecycle events. Do not change `automation_core`, report schemas, adapters, or runner CLI behavior.

**Tech Stack:** Python dataclasses, existing `EventEnvelope`/`TaskStartEvent`/`TaskEndEvent` models, pytest.

---

### Task 1: Add Failing Task Event Deduplication Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Import `TaskEndEvent`**

Update the event import:

```python
from automation_core.events import ArtifactEvent, ErrorEvent, RetryAttemptEvent, TaskEndEvent
```

- [ ] **Step 2: Add the regression test**

Add this test near the existing `ExampleWorkflow` event tests:

```python
def test_example_workflow_does_not_duplicate_returned_task_events():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=True,
            actions=[],
            artifacts=[],
            events=[
                TaskStartEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                ).to_envelope(),
                TaskEndEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    outcome="succeeded",
                ).to_envelope(),
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "task.end",
    ]
```

- [ ] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_task_events --no-cov -q
```

Expected: fail because `ExampleWorkflow.run(...)` currently adds duplicate outer lifecycle events.

### Task 2: Implement Task Event Deduplication

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add matching helpers**

Add these helpers near `_has_artifact_event(...)`:

```python
def _has_task_start_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    task_name: str,
) -> bool:
    for event in events:
        if event.event_type != "task.start" or event.task_id != task_id:
            continue
        if event.payload.get("task_name") == task_name:
            return True
    return False


def _has_task_end_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    task_name: str,
    outcome: str,
) -> bool:
    for event in events:
        if event.event_type != "task.end" or event.task_id != task_id:
            continue
        if event.payload.get("task_name") != task_name:
            continue
        if event.payload.get("outcome") == outcome:
            return True
    return False
```

- [ ] **Step 2: Skip duplicate automatic lifecycle events**

In `ExampleWorkflow.run(...)`, before appending the outer `task.start` event,
skip it when `_has_task_start_event(...)` returns `True`. Before appending the
outer `task.end` event, skip it when `_has_task_end_event(...)` returns `True`.

Use the final outcome string derived from `result.success`:

```python
outcome = "succeeded" if result.success else "failed"
```

- [ ] **Step 3: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_task_events tests/examples/damai_web/test_smoke_workflow.py::test_damai_web_smoke_workflow_factory_returns_runnable_workflow tests/examples/damai_android/test_smoke_workflow.py::test_damai_android_smoke_workflow_factory_returns_runnable_workflow --no-cov -q
```

Expected: all selected tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document task event deduplication**

Add this note near the event documentation:

```markdown
If a workflow result already includes matching `task.start` or `task.end`
events, `ExampleWorkflow` preserves them and does not add duplicate automatic
lifecycle events.
```

- [ ] **Step 2: Run full verification**

```bash
cd /Users/mango/project/codex/automation-kit
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

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Workflow Task Event Deduplication` section to
`docs/development-log.md` with red/green results, full verification,
production review summary, and the boundary note that `automation_core`
remains unchanged.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add examples tests docs
git commit -m "fix: deduplicate workflow task events"
git push origin main
```
