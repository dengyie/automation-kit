# Adapter Wait For Element Design

## Goal

Give Selenium and Appium adapter sessions a small, business-agnostic waiting
primitive for element availability.

## Problem

Simple automation flows need a reliable way to wait for a target element before
continuing. Today the adapter sessions can click and type, but they do not
offer a dedicated wait operation, so callers have to hand-roll polling in each
workflow.

## Proposed Shape

Add an adapter-layer alias:

```bash
wait_for_element(selector=..., by=..., timeout=..., interval=...)
```

Behavior:

- Selenium defaults `by` to `"css selector"`.
- Appium defaults `by` to `"accessibility id"`.
- The session keeps retrying the lookup until the element is found or the
  timeout is reached.
- Success returns `ActionResult(success=True, message="wait_for_element")`.
- Timeout returns a failed `ActionResult` with a clear message.

## Architecture

- Keep the waiting logic in the concrete adapter sessions.
- Reuse `automation_core.retries.retry_until` for polling.
- Keep `automation_core` unchanged.
- Keep raw driver-method fallback behavior intact for unsupported actions.
- Do not import Selenium or Appium packages in default test paths.

## Boundaries

- No business selectors, URLs, or workflow rules in `automation_core`.
- No live browser or device dependency in default tests.
- No change to the shared `DriverSession` protocol.

## Testing Strategy

- Add fake driver tests that prove element lookup is retried and succeeds.
- Add timeout-path tests that prove a missing element returns failure.
- Keep Selenium and Appium adapter tests offline and deterministic.
