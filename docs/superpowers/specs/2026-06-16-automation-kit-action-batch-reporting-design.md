# Action Batch Reporting Design

## Goal

Expose action batch execution summaries in runner reports without serializing
the full batch request object.

## Problem

`ActionExecutor.run_batch()` now returns an `ActionBatchResult`, but runner
reports still only know how to serialize flat action lists from
`ExampleWorkflowResult`. That means batch-level skipped actions and overall
batch success are not visible to external operators.

## Proposed Shape

Add an optional `batch_result` field to `ExampleWorkflowResult`:

```python
batch_result: Optional[ActionBatchResult] = None
```

Add an optional `action_batch` field to `RunnerReport`:

```python
action_batch: Optional[Dict[str, object]] = None
```

Serialize only the batch summary:

```json
{
  "action_batch": {
    "success": true,
    "results": [...],
    "skipped": [...]
  }
}
```

## Boundaries

- No raw `ActionBatch` object in reports.
- No changes to `automation_core.drivers`.
- No business-specific action names.
- Keep existing `actions` and `artifacts` fields unchanged for compatibility.

## Testing Strategy

- Unit tests for `ExampleWorkflowResult` carrying batch summaries.
- Unit tests for `build_report(... )` serializing `action_batch`.
- CLI tests for report output when a workflow returns a batch summary.
