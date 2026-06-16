# Workflow Artifact Failure Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve already executed workflow evidence when artifact capture fails, and emit a structured error event for returned failed workflow results.

**Architecture:** Keep the change in `examples.workflows`. `run_workflow_steps(...)` owns step sequencing and can preserve partial action/artifact evidence; `ExampleWorkflow.run(...)` owns task-level events and can add an `error` event when a returned result carries an error. `automation_core` remains unchanged.

**Tech Stack:** Python dataclasses, example workflow helpers, pytest.

---

### Task 1: Add Failing Workflow Artifact Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Add a direct artifact failure regression test**

Add this test near the other `run_workflow_steps(...)` tests:

```python
def test_run_workflow_steps_preserves_prior_results_when_artifact_capture_fails():
    class ArtifactFailureSession(FakeSession):
        def capture_artifact(self, artifact_type, name):
            if name == "broken.png":
                raise RuntimeError("screenshot failed")
            return super().capture_artifact(artifact_type, name)

    session = ArtifactFailureSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.artifact("screenshot", "home.png"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("screenshot", "broken.png"),
        ],
    )

    assert result.success is False
    assert result.error == "RuntimeError: screenshot failed"
    assert [action.message for action in result.actions] == ["open", "click"]
    assert result.batch_result is not None
    assert [action.message for action in result.batch_result.results] == [
        "open",
        "click",
    ]
    assert [artifact.path for artifact in result.artifacts] == [Path("home.png")]
    assert session.artifacts == [("screenshot", "home.png")]
    assert session.stopped is True
```

- [ ] **Step 2: Add an event regression test**

Add this test near the existing `ExampleWorkflow` event tests:

```python
def test_example_workflow_emits_error_event_for_returned_failure_result():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=False,
            actions=[ActionResult(success=True, message="open")],
            artifacts=[
                ArtifactHandle(
                    artifact_type="screenshot",
                    path=Path("home.png"),
                )
            ],
            error="RuntimeError: screenshot failed",
        ),
    )

    result = workflow.run()

    assert result.success is False
    assert result.error == "RuntimeError: screenshot failed"
    assert [event.event_type for event in result.events] == [
        "task.start",
        "artifact",
        "error",
        "task.end",
    ]
    assert result.events[2].payload == {
        "task_name": "custom-workflow",
        "task_id": "web-run",
        "message": "screenshot failed",
        "error_type": "RuntimeError",
    }
    assert result.events[-1].payload["outcome"] == "failed"
```

- [ ] **Step 3: Add an error-event deduplication regression test**

Add this test near the returned-failure event test:

```python
def test_example_workflow_does_not_duplicate_returned_error_events():
    session = FakeSession()
    workflow = ExampleWorkflow(
        name="custom-workflow",
        session_factory=lambda: session,
        run_fn=lambda current_session: ExampleWorkflowResult(
            session=current_session.info,
            success=False,
            actions=[],
            artifacts=[],
            error="RuntimeError: screenshot failed",
            events=[
                ErrorEvent(
                    task_name="custom-workflow",
                    task_id=current_session.info.identifier,
                    message="screenshot failed",
                    error_type="RuntimeError",
                ).to_envelope()
            ],
        ),
    )

    result = workflow.run()

    assert [event.event_type for event in result.events] == [
        "task.start",
        "error",
        "task.end",
    ]
```

- [ ] **Step 4: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: the new tests fail because artifact capture exceptions currently escape, returned failed results do not emit `error` events, and caller-provided `error` events are duplicated after Task 3 Step 1 is implemented without deduplication.

### Task 2: Preserve Partial Results On Artifact Failure

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add a typed error formatter**

Add this helper near the dataclasses:

```python
def _format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
```

- [ ] **Step 2: Add an error parser for event payloads**

Add this helper near `_format_error(...)`:

```python
def _split_error(error: str) -> tuple[str, str]:
    error_type, separator, message = error.partition(": ")
    if separator:
        return error_type, message
    return "Error", error
```

- [ ] **Step 3: Add a batch-result builder**

Add this local helper inside `run_workflow_steps(...)` after `flush_actions()`:

```python
    def current_batch_result() -> Optional[ActionBatchResult]:
        if ran_action_batch:
            return ActionBatchResult(results=actions, skipped=skipped)
        return None
```

- [ ] **Step 4: Catch artifact capture failures**

Replace the direct artifact append block:

```python
            artifacts.append(
                session.capture_artifact(
                    step.name,
                    str(step.parameters["name"]),
                )
            )
```

with:

```python
            try:
                artifact = session.capture_artifact(
                    step.name,
                    str(step.parameters["name"]),
                )
            except Exception as exc:
                return ExampleWorkflowResult(
                    session=session.info,
                    success=False,
                    actions=actions,
                    artifacts=artifacts,
                    batch_result=current_batch_result(),
                    error=_format_error(exc),
                )
            artifacts.append(artifact)
```

- [ ] **Step 5: Use the helper for normal batch results**

Replace the final `batch_result = ...` block with:

```python
        batch_result = current_batch_result()
```

- [ ] **Step 6: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: the direct artifact failure test passes; the event test may still fail until Task 3 is complete.

### Task 3: Emit Error Events For Returned Failed Results

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [ ] **Step 1: Add an error event when `result.error` is present**

In `ExampleWorkflow.run(...)`, after artifact events are extended and before
`TaskEndEvent(...)`, add:

```python
            has_error_event = any(
                event.event_type == "error" for event in result.events
            )
            if result.error is not None and not has_error_event:
                error_type, message = _split_error(result.error)
                events.append(
                    ErrorEvent(
                        task_name=self.name,
                        task_id=session.info.identifier,
                        message=message,
                        error_type=error_type,
                    ).to_envelope()
                )
```

- [ ] **Step 2: Reuse `_format_error(...)` in the exception fallback**

Replace:

```python
                error=f"{type(exc).__name__}: {exc}",
```

with:

```python
                error=_format_error(exc),
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: all web example workflow tests pass.

### Task 4: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document artifact failure reporting**

Add this note near the workflow step documentation:

```markdown
If an artifact step fails after earlier actions or artifacts completed,
`run_workflow_steps(...)` returns a failed result that preserves the evidence
captured before the failure.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: full tests pass and `git diff --check` emits no output.

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify Python stack review context.

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Workflow Artifact Failure Reporting` section to
`docs/development-log.md` with:

- red and green focused test results,
- full suite result,
- production review result,
- boundary note that `automation_core` remains unchanged.

- [ ] **Step 5: Commit and push**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
git add examples tests docs
git commit -m "fix: preserve workflow artifact failure evidence"
git push origin main
```
