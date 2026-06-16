# Adapter Action Execution Failure Handling Design

## Goal

Return failed `ActionResult` values when Selenium or Appium adapter actions find
their target but the underlying driver or element operation raises.

## Problem

The adapters now normalize direct element lookup failures, but several common
execution failures still escape as raw driver exceptions:

- Selenium `open` calls `driver.get(...)`.
- Selenium `click` calls `element.click()`.
- Selenium `type_text` calls optional `element.clear()` and then
  `element.send_keys(...)`.
- Appium `launch_app` calls `driver.activate_app(...)`.
- Appium coordinate `tap` and `mobile:*` actions call
  `driver.execute_script(...)`.
- Appium element `tap` and `type_text` call element methods.
- Raw supported driver actions are still called directly.

For a workflow runner, these are expected automation failures rather than
process-level failures. Letting them escape makes JSON reports less reliable and
makes adapters inconsistent with their `ActionResult` contract.

## Proposed Shape

- Keep all handling inside concrete adapter sessions.
- Keep missing required parameter and unsupported-action behavior unchanged.
- Catch exceptions raised by aliased action execution and raw supported driver
  actions.
- Return `ActionResult(success=False, message="<action> failed: <exception>")`.
- Preserve successful action messages and `data` values.
- Do not change `wait_for_element` retry semantics.
- Do not change artifact capture in this slice.
- Do not change `automation_core`.

## Architecture

Add a small `_run_action(...)` helper to each adapter session. The helper accepts
the public action name and a zero-argument callable, runs it, and converts
exceptions into a failed `ActionResult`. Aliased actions can use it after
parameter validation and element lookup. Raw supported driver actions can use it
around `action(**kwargs)`.

This keeps adapter-specific exception normalization near existing adapter code
without adding driver-specific exception types to the core contract.

## Error Contract

Examples:

- Selenium `open` driver failure: `open failed: navigation failed`
- Selenium `click` element failure: `click failed: click intercepted`
- Selenium `type_text` clear failure: `type_text failed: clear failed`
- Selenium raw action failure: `refresh failed: browser closed`
- Appium `launch_app` driver failure: `launch_app failed: app unavailable`
- Appium coordinate `tap` script failure: `tap failed: gesture failed`
- Appium `mobile:*` script failure:
  `mobile: scrollGesture failed: scroll failed`
- Appium raw action failure: `activate_app failed: device offline`

## Testing Strategy

- Extend Selenium fake driver and element objects with configurable execution
  failures.
- Add focused Selenium tests for `open`, `click`, `type_text` clear,
  `type_text` send keys, and raw supported driver action failures.
- Extend Appium fake driver and element objects with configurable execution
  failures.
- Add focused Appium tests for `launch_app`, coordinate `tap`, element `tap`,
  `type_text` clear, `type_text` send keys, `mobile:*`, and raw supported driver
  action failures.
- Run focused adapter tests first, then the full test suite.
