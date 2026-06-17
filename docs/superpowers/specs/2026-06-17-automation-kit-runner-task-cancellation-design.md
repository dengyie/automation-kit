# Runner Task Cancellation Design

## Goal

Propagate `automation_core.tasks.TaskCancelledError` through the runner so a
cancelled workflow is reported as cancelled instead of failed.

## Problem

`automation_core.tasks.TaskRunner` now returns an explicit cancelled task
result, but the runner layer still treats any non-successful workflow result as
`failed`. That means a task that was intentionally cancelled would still be
serialized and reported as a failure in JSON output and CLI exit handling.

## Proposed Shape

- Update `ExampleWorkflowResult` and runner report serialization to carry a
  cancellation terminal state.
- Update `automation_runner.cli` so workflow execution returns a cancelled
  report state when the workflow raises `TaskCancelledError`.
- Keep startup failures, ordinary exceptions, and existing success/failure
  behavior unchanged.
- Keep report schema compatibility by adding cancelled where status enums are
  already used.

## Architecture

The cancellation translation belongs in `automation_runner`, not in
`automation_core`, because it is report and CLI policy. Core task cancellation
remains a generic runtime primitive; the runner decides how to serialize and
exit on that terminal state.

## Testing Strategy

- Add a failing CLI/report test that raises `TaskCancelledError` from a
  workflow factory.
- Assert the JSON report uses `status="cancelled"` and the run state is
  cancelled.
- Keep success and failure tests passing.
- Run the full suite and production review after implementation.
