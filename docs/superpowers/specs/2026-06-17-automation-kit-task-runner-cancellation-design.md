# Task Runner Cancellation Design

## Goal

Give `automation_core.tasks.TaskRunner` a first-class cancellation outcome
without turning task cancellation into a generic failure.

## Problem

`TaskLifecycle` and `RunState` already understand a cancelled terminal state,
but `TaskRunner.run(...)` only returns success or failure today. If a task wants
to stop work intentionally, it has no explicit core-level outcome to signal and
must look like a normal error.

That makes cancellation awkward for future workflow layers:

- a user-requested stop looks like an exception,
- report consumers cannot tell cancellation from failure,
- task events cannot distinguish cancelled endings from failed endings.

## Proposed Shape

- Add a small task-level cancellation exception:

  ```python
  class TaskCancelledError(RuntimeError):
      ...
  ```

- Extend `TaskResult` with an explicit terminal state field that can carry
  `succeeded`, `failed`, or `cancelled`.
- Update `TaskRunner.run(...)` so:
  - successful tasks still return a succeeded result,
  - ordinary exceptions still return a failed result with an `error`,
  - `TaskCancelledError` returns a cancelled result without an `error`,
  - `task.end` events use `outcome="cancelled"` for cancellation.
- Keep `KeyboardInterrupt` propagation unchanged.

## Architecture

The behavior belongs in `automation_core.tasks` because cancellation is a task
lifecycle concern, not a browser, Android, or runner concern. The task runner
should be the only place that translates a raised cancellation request into a
terminal task result.

## Testing Strategy

- Add a failing test that raises `TaskCancelledError` from a task callable.
- Assert the result is marked cancelled and does not include an error.
- Assert the emitted event sequence is `task.start` then `task.end`.
- Keep the existing success, failure, and `KeyboardInterrupt` tests passing.
