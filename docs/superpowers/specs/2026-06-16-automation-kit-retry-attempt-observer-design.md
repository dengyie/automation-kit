# Retry Attempt Observer Design

## Goal

Expose bounded retry attempt metadata through an optional callback so callers
can build structured events, logs, and reports without parsing retry internals.

## Problem

`retry_until(...)` already centralizes bounded retry behavior, but callers
cannot observe each attempt. That makes future recovery loops and debug reports
harder to explain: the final `RetryResult` says how many attempts happened, but
not what each attempt saw.

## Proposed Shape

Add a small immutable snapshot model:

```python
RetryAttemptSnapshot(
    attempt=1,
    elapsed=0.0,
    value="not-ready",
    exception=None,
    will_retry=True,
)
```

Add an optional callback argument:

```python
retry_until(..., on_attempt=callback)
```

The callback receives one snapshot after each attempt once retry continuation is
known. The callback is optional and existing callers keep working unchanged.

## Architecture

- Keep this in `automation_core.retries`; it is a generic runtime primitive.
- Do not import event models into the retry package.
- Let higher layers translate snapshots into `RetryAttemptEvent` or logs when
  they have task context.
- Keep interruption behavior unchanged: `KeyboardInterrupt` and `SystemExit`
  still propagate without callback handling.

## Boundaries

- No Selenium/Appium imports.
- No runner/report dependency from `automation_core.retries`.
- No business-specific task names, selectors, URLs, app IDs, or workflow data.
- No change to default retry boundaries.

## Testing Strategy

- Add focused retry tests for callback snapshots on predicate failure, retryable
  exception, and final success.
- Verify existing retry behavior remains compatible when no callback is passed.
- Run the full suite and production review scripts before commit.
