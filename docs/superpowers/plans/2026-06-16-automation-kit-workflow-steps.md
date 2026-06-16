# Workflow Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add example-layer workflow step primitives so website and Android examples can compose action and artifact steps without duplicating lifecycle code.

**Architecture:** Keep step composition in `examples.workflows`, because this is an authoring convenience for sample/business workflows rather than a core runtime contract. Reuse `automation_core.actions.ActionBatch` and `ActionExecutor` for action execution. Preserve existing `ExampleWorkflow` report and event behavior.

**Tech Stack:** Python dataclasses, pytest, existing fake sessions and driver contracts.

---

## Task 1: Add Failing Workflow Step Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [x] **Step 1: Add imports for the wished-for API**

Update the import from `examples.workflows` to include:

```python
from examples.workflows import (
    ExampleWorkflow,
    ExampleWorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)
```

- [x] **Step 2: Add a test for ordered actions and artifacts**

Add this test:

```python
def test_run_workflow_steps_runs_actions_and_artifacts_in_order():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.artifact("screenshot", "home.png"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("page_source", "after-click.html"),
        ],
    )

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert [action.message for action in result.actions] == ["open", "click"]
    assert result.batch_result is not None
    assert result.batch_result.skipped == []
    assert session.actions == [
        ("open", {"url": "https://example.test/damai"}),
        ("click", {"selector": "#buy"}),
    ]
    assert session.artifacts == [
        ("screenshot", "home.png"),
        ("page_source", "after-click.html"),
    ]
```

- [x] **Step 3: Add a test for stop-on-failure behavior**

Add this test:

```python
def test_run_workflow_steps_stops_after_failed_action_batch():
    class FailedActionSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            self.actions.append((action_name, kwargs))
            return ActionResult(success=action_name != "open", message=action_name)

    session = FailedActionSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url="https://example.test/damai"),
            WorkflowStep.action("click", selector="#buy"),
            WorkflowStep.artifact("screenshot", "should-not-run.png"),
        ],
    )

    assert result.success is False
    assert [action.message for action in result.actions] == ["open"]
    assert result.batch_result is not None
    assert [action.name for action in result.batch_result.skipped] == ["click"]
    assert result.artifacts == []
    assert session.artifacts == []
    assert session.stopped is True
```

- [x] **Step 4: Add a test for artifact-only behavior**

Add this test:

```python
def test_run_workflow_steps_allows_artifact_only_sequences():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [
            WorkflowStep.artifact("screenshot", "home.png"),
        ],
    )

    assert session.started is True
    assert session.stopped is True
    assert result.success is True
    assert result.actions == []
    assert result.batch_result is None
    assert session.actions == []
    assert session.artifacts == [("screenshot", "home.png")]
```

- [x] **Step 5: Run red verification**

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: fail because `WorkflowStep` and `run_workflow_steps` are not defined.

## Task 2: Implement Workflow Step Primitives

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`

- [x] **Step 1: Add step dataclass**

Add a frozen `WorkflowStep` dataclass with these fields:

```python
kind: str
name: str
parameters: Dict[str, object] = field(default_factory=dict)
```

Add class constructors:

```python
@classmethod
def action(cls, name: str, **parameters: object) -> "WorkflowStep":
    return cls(kind="action", name=name, parameters=parameters)

@classmethod
def artifact(cls, artifact_type: str, name: str) -> "WorkflowStep":
    return cls(kind="artifact", name=artifact_type, parameters={"name": name})
```

- [x] **Step 2: Add batch flushing helper**

Inside `run_workflow_steps`, collect contiguous action steps as
`ActionRequest` values and flush them through `ActionExecutor(session).run_batch(...)`
before capturing an artifact or returning.

- [x] **Step 3: Return composed result**

Return `ExampleWorkflowResult` with:

- `session=session.info`
- `success` based on all action results
- all executed `actions`
- captured `artifacts`
- latest/combined `batch_result`

For this slice, combine action results into one `ActionBatchResult` and append
skipped actions from the first failed batch.

- [x] **Step 4: Preserve cleanup and exception behavior**

Start the session before processing steps and stop it in `finally`. Do not
catch ordinary exceptions inside `run_workflow_steps`; `ExampleWorkflow.run()`
already converts exceptions into structured failure events.

- [x] **Step 5: Run green verification**

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: pass.

## Task 3: Move Built-In Smoke Workflows Onto Steps

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_web/smoke.py`
- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_android/smoke.py`
- Verify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`
- Verify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_android/test_smoke_workflow.py`

- [x] **Step 1: Update web smoke workflow**

Replace direct `ActionBatch` usage with:

```python
return run_workflow_steps(
    session,
    [
        WorkflowStep.action("open", url=url),
        WorkflowStep.artifact("screenshot", "home.png"),
    ],
)
```

- [x] **Step 2: Update Android smoke workflow**

Replace direct `ActionBatch` usage with:

```python
return run_workflow_steps(
    session,
    [
        WorkflowStep.action("launch_app", app_id=app_id),
        WorkflowStep.artifact("screenshot", "startup.png"),
        WorkflowStep.artifact("page_source", "startup.xml"),
    ],
)
```

- [x] **Step 3: Run focused example and CLI verification**

```bash
.venv/bin/python -m pytest tests/examples tests/runner/test_cli.py --no-cov -q
```

Expected: pass.

## Task 4: Docs, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document workflow steps**

Add a short section explaining `WorkflowStep.action(...)`,
`WorkflowStep.artifact(...)`, and `run_workflow_steps(...)` as example-layer
helpers.

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
git add examples tests docs
git commit -m "feat: add workflow step composition"
git push origin main
```
