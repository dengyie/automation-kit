# Action Executor Exception Result Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ActionExecutor` convert ordinary session action exceptions into failed `ActionResult` values while preserving interruption behavior.

**Architecture:** Keep the change in `automation_core.actions.models`. `ActionExecutor.run(...)` is the generic boundary around `DriverSession.execute_action(...)`, so it can normalize ordinary action exceptions without adding adapter or business-specific logic. Existing `ActionBatchResult` skipped-action behavior remains the batch-level reporting contract.

**Tech Stack:** Python core action models, pytest fake sessions, example workflow tests.

---

### Task 1: Add Failing Core Action Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/actions/test_action_models.py`

- [ ] **Step 1: Extend the fake session with exception paths**

Update `FakeSession.execute_action(...)`:

```python
    def execute_action(self, action_name, **kwargs):
        self.calls.append((action_name, kwargs))
        if action_name == "explode":
            raise RuntimeError("driver disconnected")
        if action_name == "interrupt":
            raise KeyboardInterrupt()
        if action_name == "fail":
            return ActionResult(success=False, message="failed")
        return ActionResult(success=True, message=action_name, data=kwargs)
```

- [ ] **Step 2: Add direct exception normalization coverage**

Add this test near the direct executor test:

```python
def test_action_executor_returns_failed_result_when_session_action_raises():
    session = FakeSession()
    executor = ActionExecutor(session)

    result = executor.run(ActionRequest(name="explode"))

    assert result.success is False
    assert result.message == "explode failed: driver disconnected"
    assert session.calls == [("explode", {})]
```

- [ ] **Step 3: Add batch exception normalization coverage**

Add this test near batch failure tests:

```python
def test_action_executor_batch_stops_after_session_action_exception():
    session = FakeSession()
    executor = ActionExecutor(session)
    batch = ActionBatch(
        actions=[
            ActionRequest(name="get"),
            ActionRequest(name="explode"),
            ActionRequest(name="after"),
        ]
    )

    result = executor.run_batch(batch)

    assert [item.success for item in result.results] == [True, False]
    assert [item.message for item in result.results] == [
        "get",
        "explode failed: driver disconnected",
    ]
    assert [item.name for item in result.skipped] == ["after"]
    assert session.calls == [("get", {}), ("explode", {})]
```

- [ ] **Step 4: Add interruption propagation coverage**

Add this test near the direct executor tests:

```python
def test_action_executor_does_not_catch_keyboard_interrupt():
    session = FakeSession()
    executor = ActionExecutor(session)

    with pytest.raises(KeyboardInterrupt):
        executor.run(ActionRequest(name="interrupt"))
```

- [ ] **Step 5: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/actions/test_action_models.py --no-cov -q
```

Expected: the new ordinary-exception tests fail because `ActionExecutor.run(...)` still lets `RuntimeError` escape; the `KeyboardInterrupt` test already passes.

### Task 2: Update Example Workflow Failure Expectations

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_android/test_smoke_workflow.py`

- [ ] **Step 1: Update web lower-level helper expectation**

Replace:

```python
def test_damai_web_smoke_workflow_stops_session_when_action_fails():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()

    with pytest.raises(RuntimeError, match="navigation failed"):
        run_smoke_workflow(session, url="https://example.test/damai")

    assert session.started is True
    assert session.stopped is True
```

with:

```python
def test_damai_web_smoke_workflow_returns_failure_when_action_raises():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("navigation failed")

    session = FailingSession()

    result = run_smoke_workflow(session, url="https://example.test/damai")

    assert result.success is False
    assert result.error is None
    assert [action.message for action in result.actions] == [
        "open failed: navigation failed",
    ]
    assert result.artifacts == []
    assert session.started is True
    assert session.stopped is True
```

- [ ] **Step 2: Update Android lower-level helper expectation**

Replace:

```python
def test_damai_android_smoke_workflow_stops_session_when_action_fails():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("activation failed")

    session = FailingSession()

    with pytest.raises(RuntimeError, match="activation failed"):
        run_smoke_workflow(session, app_id="cn.damai")

    assert session.started is True
    assert session.stopped is True
```

with:

```python
def test_damai_android_smoke_workflow_returns_failure_when_action_raises():
    class FailingSession(FakeSession):
        def execute_action(self, action_name, **kwargs):
            raise RuntimeError("activation failed")

    session = FailingSession()

    result = run_smoke_workflow(session, app_id="cn.damai")

    assert result.success is False
    assert result.error is None
    assert [action.message for action in result.actions] == [
        "launch_app failed: activation failed",
    ]
    assert result.artifacts == []
    assert session.started is True
    assert session.stopped is True
```

- [ ] **Step 3: Run focused red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/actions/test_action_models.py tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Expected: ordinary-exception tests still fail until implementation is added.

### Task 3: Implement ActionExecutor Exception Results

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/actions/models.py`

- [ ] **Step 1: Wrap session action execution**

Replace:

```python
    def run(self, action: ActionRequest) -> ActionResult:
        return self.session.execute_action(action.name, **action.parameters)
```

with:

```python
    def run(self, action: ActionRequest) -> ActionResult:
        try:
            return self.session.execute_action(action.name, **action.parameters)
        except Exception as exc:
            return ActionResult(False, f"{action.name} failed: {exc}")
```

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/actions/test_action_models.py tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Expected: all focused tests pass.

### Task 4: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document action exception normalization**

Add this note near the action batch description:

```markdown
`ActionExecutor` converts ordinary `execute_action(...)` exceptions into failed
`ActionResult` values so batches can still report executed and skipped actions.
Interruption exceptions such as `KeyboardInterrupt` are not swallowed.
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

Append a `2026-06-17: Action Executor Exception Results` section to
`docs/development-log.md` with:

- red and green focused test results,
- full suite result,
- production review result,
- boundary note that `automation_core` remains business-agnostic.

- [ ] **Step 5: Commit and push**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_core tests docs
git commit -m "fix: normalize action executor exceptions"
git push origin main
```
