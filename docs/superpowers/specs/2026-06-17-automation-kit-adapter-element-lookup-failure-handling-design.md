# Adapter Element Lookup Failure Handling Design

## Goal

Return failed `ActionResult` values when Selenium or Appium element actions
cannot resolve a target element.

## Problem

The adapter sessions already expose a dedicated `wait_for_element` alias that
retries lookup until success or timeout. But the direct element actions still do
this:

- `click` / `tap` resolve an element and then call `.click()`
- `type_text` resolves an element and then call `.clear()` / `.send_keys()`

If the driver raises while locating the element, the exception currently escapes
the adapter method. That means a routine missing-element case can crash the
workflow instead of producing a normal failed `ActionResult`. The result is
harder to report, harder to serialize, and less consistent with the rest of the
adapter contract.

## Proposed Shape

- Wrap element lookup in the direct element actions.
- Return the existing lookup-support failure message when the driver does not
  support `find_element`.
- Return a failed `ActionResult` when `find_element` raises during `click`,
  `tap`, or `type_text`.
- Keep `wait_for_element` retry semantics unchanged.
- Keep raw driver-method fallback behavior unchanged for non-aliased actions.

## Architecture

This belongs in the concrete adapter sessions because the lookup behavior is
adapter-specific and already lives there. The core driver contracts should stay
unchanged. The implementation should centralize lookup failure handling in a
small helper per adapter rather than duplicating `try/except` blocks across each
action.

## Testing Strategy

- Add Selenium adapter tests proving `click`, `type_text`, and `wait_for_element`
  with a missing lookup target behave as expected.
- Add Appium adapter tests proving `tap`, `type_text`, and `wait_for_element`
  with a missing lookup target behave as expected.
- Keep unsupported-action and timeout-path tests unchanged.
- Run focused adapter tests and the full suite.
