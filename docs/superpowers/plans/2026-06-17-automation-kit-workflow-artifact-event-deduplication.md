# Workflow Artifact Event Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Avoid duplicate artifact events when a custom example workflow already returns an artifact event matching a returned artifact handle.

**Architecture:** Keep the change in `examples.workflows`, where example workflow event assembly already lives. Add a small matching helper that checks caller-provided events before appending automatic artifact events. Do not change `automation_core`, report schemas, adapters, or runner CLI behavior.

**Tech Stack:** Python dataclasses, existing `EventEnvelope`/`ArtifactEvent` models, pytest.

---

### Task 1: Add Failing Artifact Event Deduplication Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Import `ArtifactEvent`**

Update the event import:

```python
from automation_core.events import ArtifactEvent, ErrorEvent, RetryAttemptEvent
```

- [ ] **Step 2: Add the regression test**

Add this test near the existing `ExampleWorkflow` event tests:

```python
def test_example_workflow_does_not_duplicate_returned_artifact_events():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=True,
            actions=[],
            artifacts=[
                ArtifactHandle(
                    artifact_type="screenshot",
                    path=Path("home.png"),
                )
            ],
            events=[
                ArtifactEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    artifact_type="screenshot",
                    path="home.png",
                ).to_envelope()
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "task.end",
    ]
```

- [ ] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_artifact_events --no-cov -q
```

Expected: fail because `ExampleWorkflow.run(...)` appends a duplicate automatic artifact event.

### Task 2: Implement Artifact Event Deduplication

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add a matching helper**

Add this helper near `_split_error(...)`:

```python
def _has_artifact_event(
    events: List[EventEnvelope],
    *,
    task_id: str,
    artifact: ArtifactHandle,
) -> bool:
    artifact_path = str(artifact.path)
    for event in events:
        if event.event_type != "artifact" or event.task_id != task_id:
            continue
        if event.payload.get("artifact_type") != artifact.artifact_type:
            continue
        if event.payload.get("path") == artifact_path:
            return True
    return False
```

- [ ] **Step 2: Skip duplicate automatic artifact events**

Replace the automatic artifact event extension in `ExampleWorkflow.run(...)`
with a loop that appends only missing artifact events:

```python
            for artifact in result.artifacts:
                if _has_artifact_event(
                    result.events,
                    task_id=session.info.identifier,
                    artifact=artifact,
                ):
                    continue
                events.append(
                    ArtifactEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        artifact_type=artifact.artifact_type,
                        path=str(artifact.path),
                    ).to_envelope()
                )
```

- [ ] **Step 3: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_artifact_events tests/examples/damai_web/test_smoke_workflow.py::test_damai_web_smoke_workflow_factory_returns_runnable_workflow tests/examples/damai_android/test_smoke_workflow.py::test_damai_android_smoke_workflow_factory_returns_runnable_workflow --no-cov -q
```

Expected: all selected tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document artifact event deduplication**

Add this note near the event documentation:

```markdown
If a workflow result already includes an `artifact` event for a returned
artifact handle, `ExampleWorkflow` preserves that event and does not add a
duplicate automatic artifact event.
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

Append a `2026-06-17: Workflow Artifact Event Deduplication` section to
`docs/development-log.md` with red/green results, full verification,
production review summary, and the boundary note that `automation_core`
remains unchanged.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add examples tests docs
git commit -m "fix: deduplicate workflow artifact events"
git push origin main
```
