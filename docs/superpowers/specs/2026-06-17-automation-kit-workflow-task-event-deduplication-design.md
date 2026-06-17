# Workflow Task Event Deduplication Design

## Goal

Avoid duplicate `task.start` and `task.end` events when an example workflow
already returns matching task events.

## Problem

`ExampleWorkflow.run(...)` always prepends one `task.start` event and appends
one `task.end` event around the caller-provided workflow result. This is fine
for built-in workflows that only return artifact or error events. But custom
workflows may also return their own structured task lifecycle events.

When a custom workflow already includes `task.start` or `task.end` for the same
task, the outer wrapper produces duplicates. That makes event streams noisy and
can confuse downstream consumers that expect a single lifecycle pair.

## Proposed Shape

- Keep automatic task event generation in `examples.workflows`.
- Preserve caller-provided events.
- Before adding the automatic outer `task.start` event, check whether
  `result.events` already contains a matching `task.start` event.
- Before adding the automatic outer `task.end` event, check whether
  `result.events` already contains a matching `task.end` event.
- Match lifecycle events by `event_type`, `task_id`, and the relevant payload
  fields.
- Keep the existing artifact and error event deduplication behavior unchanged.
- Keep `automation_core` unchanged and business-agnostic.

## Event Match Contract

A caller-provided `task.start` event matches when:

- `event_type == "task.start"`
- `task_id == session.info.identifier`
- `payload["task_name"] == self.name`

A caller-provided `task.end` event matches when:

- `event_type == "task.end"`
- `task_id == session.info.identifier`
- `payload["task_name"] == self.name`
- `payload["outcome"]` matches the final workflow outcome (`"succeeded"` or
  `"failed"`)

The outer wrapper still owns outcome selection; the match only prevents
duplicate emission when the workflow already supplied the same lifecycle event.

## Testing Strategy

- Add a regression test where a custom example workflow returns matching
  `task.start` and `task.end` events along with a normal result.
- Verify the final event sequence contains only one lifecycle pair.
- Keep existing built-in example workflow event tests green.
- Run the focused example workflow tests, the full suite, `git diff --check`,
  and production review scripts.
