# Retry Snapshot Event Bridge Design

## Goal

Let callers convert retry attempt snapshots into structured retry attempt
events without coupling `automation_core.retries` to the event package.

## Problem

`retry_until(...)` can now expose `RetryAttemptSnapshot` objects, and
`automation_core.events` already has `RetryAttemptEvent`. Callers still need a
small, consistent bridge to translate the generic retry snapshot into a task
event when they have task context.

## Proposed Shape

Add an event-layer helper:

```python
retry_attempt_event_from_snapshot(
    task_name="checkout",
    task_id="task-1",
    snapshot=snapshot,
)
```

It returns a `RetryAttemptEvent` populated with `attempt` and `elapsed`.

## Architecture

- Keep the helper in `automation_core.events`.
- Allow `automation_core.events` to import the retry snapshot type.
- Keep `automation_core.retries` independent from `automation_core.events`.
- Keep event payload shape backward compatible by not changing
  `RetryAttemptEvent` required fields in this slice.

## Boundaries

- No runner/report imports.
- No Selenium/Appium imports.
- No business task names, selectors, URLs, app IDs, or workflow rules.
- No automatic event emission from `retry_until(...)`.

## Testing Strategy

- Add an event test proving the helper creates a `RetryAttemptEvent` from a
  `RetryAttemptSnapshot`.
- Add an import-boundary test proving `automation_core.retries.policy` still
  does not import `automation_core.events`.
- Run full tests and production review before commit.
