# Task Runner Cancellation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class cancellation outcome to `automation_core.tasks.TaskRunner` so tasks can stop intentionally without being treated as ordinary failures.

**Architecture:** Keep the change inside `automation_core.tasks`. Introduce a small task-level cancellation exception, extend `TaskResult` with an explicit terminal state, and map cancellation to a `task.end` event with `outcome="cancelled"`. Leave `KeyboardInterrupt` propagation unchanged and keep the rest of the task lifecycle business-agnostic.

**Tech Stack:** Python dataclasses, enums, typing, pytest, existing task lifecycle and event primitives.

---

### Task 1: Add Failing Cancellation Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/tasks/test_runner.py`

- [ ] **Step 1: Add a cancellation test**

Add this test near the existing task runner coverage:

```python
from automation_core.tasks import TaskCancelledError, TaskResult, TaskRunner


def test_task_runner_returns_cancelled_result_and_terminal_events():
    runner = TaskRunner(task_name="stop-now", task_id="task-1")

    def cancel():
        raise TaskCancelledError("user requested stop")

    result = runner.run(cancel)

    assert isinstance(result, TaskResult)
    assert result.success is False
    assert result.state.value == "cancelled"
    assert result.value is None
    assert result.error is None
    assert [event.event_type for event in result.events] == [
        "task.start",
        "task.end",
    ]
    assert result.events[-1].payload["outcome"] == "cancelled"
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/tasks/test_runner.py -q
```

Expected: fail because `TaskCancelledError` and cancelled task results do not exist yet.

### Task 2: Implement Cancellation In The Core Runner

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/tasks/runner.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/tasks/__init__.py`

- [ ] **Step 1: Add `TaskCancelledError` and terminal state tracking**

Implement:

```python
class TaskCancelledError(RuntimeError):
    """Raised when a task is cancelled intentionally."""
```

Extend `TaskResult`:

```python
from automation_core.tasks.lifecycle import TaskState


@dataclass(frozen=True)
class TaskResult(Generic[T]):
    task_id: str
    task_name: str
    state: TaskState
    success: bool
    value: Optional[T]
    error: Optional[str]
    events: List[EventEnvelope]
```

Map runner outcomes:

```python
        except TaskCancelledError:
            lifecycle.cancel()
            events.append(
                TaskEndEvent(
                    task_name=self.task_name,
                    task_id=self.task_id,
                    outcome="cancelled",
                ).to_envelope()
            )
            return TaskResult(
                task_id=self.task_id,
                task_name=self.task_name,
                state=TaskState.CANCELLED,
                success=False,
                value=None,
                error=None,
                events=events,
            )
```

Successful and failed paths should continue to return the same event order as today, with `state` set to `TaskState.SUCCEEDED` or `TaskState.FAILED`.

- [ ] **Step 2: Export the new exception**

Update `automation_core/tasks/__init__.py` so `TaskCancelledError` is part of the public task API.

- [ ] **Step 3: Run green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/tasks/test_runner.py tests/test_imports.py --no-cov -q
```

Expected: pass.

### Task 3: Document And Review

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document cancelled task endings**

Update the report contract note so it says task ends can be `succeeded`, `failed`, or `cancelled`, and mention that cancellation is raised as `automation_core.tasks.TaskCancelledError`.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Task Runner Cancellation` section to
`docs/development-log.md` with the red/green results, full verification,
review summary, and the note that `automation_core` stays business-agnostic.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_core tests docs
git commit -m "fix: add task runner cancellation"
git push origin main
```
