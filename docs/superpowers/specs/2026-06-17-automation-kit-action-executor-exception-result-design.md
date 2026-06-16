# Action Executor Exception Result Design

## Goal

Make `ActionExecutor` convert ordinary session action exceptions into failed
`ActionResult` values so action batches keep their structured reporting
contract.

## Problem

`ActionExecutor.run(...)` currently calls:

```python
self.session.execute_action(action.name, **action.parameters)
```

If a concrete session raises an ordinary exception, the exception escapes the
core action executor. That means:

- `ActionBatchResult` is not returned,
- already executed action results can be lost by higher-level exception
  handlers,
- skipped actions are not recorded,
- workflow reports can be less honest about which step failed.

Recent adapter work makes Selenium and Appium aliases return failed
`ActionResult` values for expected lookup and execution failures, but
`ActionExecutor` is a generic boundary and should still protect batch reporting
from custom or future session implementations that raise `Exception`.

## Proposed Shape

- Keep the behavior in `automation_core.actions.ActionExecutor`.
- Wrap `session.execute_action(...)` in `ActionExecutor.run(...)`.
- Catch ordinary `Exception` and return:

```python
ActionResult(success=False, message="<action_name> failed: <exception>")
```

- Do not catch `KeyboardInterrupt`, `SystemExit`, or other `BaseException`
  subclasses.
- Keep successful action results unchanged.
- Keep `ActionBatchResult.success` and skipped-action behavior unchanged.
- Keep this generic and business-agnostic.

## Error Contract

For:

```python
ActionRequest(name="open")
```

and:

```python
RuntimeError("browser disconnected")
```

the executor returns:

```python
ActionResult(
    success=False,
    message="open failed: browser disconnected",
)
```

In a batch with `stop_on_failure=True`, later actions are recorded as skipped in
the existing `ActionBatchResult.skipped` field.

## Testing Strategy

- Add direct `ActionExecutor.run(...)` coverage for ordinary exceptions.
- Add `ActionExecutor.run_batch(...)` coverage proving:
  - prior successful action results are preserved,
  - the raised action becomes a failed `ActionResult`,
  - following actions are skipped by default.
- Add `KeyboardInterrupt` coverage proving interruption still propagates.
- Update example workflow failure expectations where lower-level helpers now
  return structured failed results instead of raising.
- Run focused action and example workflow tests, then the full suite.
