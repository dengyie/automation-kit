# Runner Startup Failure Events Design

## Goal

Make runner startup failure reports include the same structured event shape as
normal workflow failures.

## Problem

`automation_runner` now emits JSON reports when workflow construction or
session startup fails before a workflow returns. Those reports include `error`,
`status`, and a fallback `session`, but their `events` list is empty. That makes
startup failures harder for schedulers and operators to process because normal
workflow failures already emit:

- `task.start`
- `error`
- `task.end`

Startup failures should use the same event vocabulary.

## Proposed Shape

When the CLI converts an exception into a fallback `ExampleWorkflowResult`, add
three events:

```text
task.start
error
task.end
```

Use the fallback run id as the event `task_id`:

```python
f"{workflow_name}-failed-run"
```

The `error` event payload should include the original exception message and
type. The `task.end` event should set `outcome` to `failed`.

## Boundaries

- Keep this behavior in `automation_runner.cli`.
- Do not change normal `ExampleWorkflow.run()` event behavior.
- Do not change `automation_core.events`.
- Do not add retry or recovery behavior in this slice.
- Keep startup failure reports compatible with the existing JSON report schema.

## Testing Strategy

- Update session startup failure CLI tests to assert the three event types and
  error payload.
- Update custom workflow factory failure CLI tests to assert the same event
  shape.
- Run focused CLI tests, then full suite and production review scripts.
