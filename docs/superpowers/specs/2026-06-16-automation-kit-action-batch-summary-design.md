# Action Batch Summary Design

## Goal

Give action batch execution an explicit summary object that records executed
actions, skipped actions, and overall success.

## Problem

`ActionExecutor.run_batch()` currently returns only a list of `ActionResult`
objects. Callers can infer whether execution stopped early by comparing list
lengths, but that is easy to get wrong and makes later workflow/report
integration awkward.

## Proposed Shape

Add an `ActionBatchResult` dataclass in `automation_core.actions`:

```python
@dataclass(frozen=True)
class ActionBatchResult:
    results: List[ActionResult]
    skipped: List[ActionRequest]

    @property
    def success(self) -> bool:
        return bool(self.results) and all(result.success for result in self.results)

    def to_dict(self) -> Dict[str, Any]:
        ...
```

Update `ActionExecutor.run_batch(...)` to return `ActionBatchResult`.

## Compatibility

- Keep `ActionExecutor.run(...)` unchanged.
- Keep `ActionRequest` and `ActionBatch` serialization unchanged.
- No changes to `automation_core.drivers`.
- No business-specific action names.

## Semantics

- `results` includes actions that were actually executed.
- `skipped` includes remaining actions not executed after a stop-on-failure
  failure.
- `success` is true only when at least one action ran and every executed action
  succeeded.
- Empty batches return `success=False`, `results=[]`, and `skipped=[]`.

## Testing Strategy

- Unit test successful batch summary.
- Unit test skipped actions after stop-on-failure.
- Unit test continue-after-failure with no skipped actions.
- Unit test empty batch summary.
- Unit test `to_dict()` serialization.
