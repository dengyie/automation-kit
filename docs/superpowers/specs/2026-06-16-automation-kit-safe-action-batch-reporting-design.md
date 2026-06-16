# Safe Action Batch Reporting Design

## Goal

Keep runner JSON reports from exposing raw action result `data` or skipped
action parameters through the `action_batch` field.

## Problem

Runner reports already serialize the top-level `actions` list safely by
including only `success` and `message`. Project documentation also states that
JSON reports must not embed raw action `data`.

The newer `action_batch` field currently delegates to
`ActionBatchResult.to_dict()`. That core-level serialization includes
`ActionResult.data` and skipped `ActionRequest.parameters`. Those values can
contain URLs, coordinates, app inputs, tokens, cookies, or workflow-specific
values. This creates a report-contract mismatch and a possible secret leakage
path.

## Proposed Shape

Keep `automation_core.actions.ActionBatchResult.to_dict()` unchanged because it
is a generic core serialization helper. Add runner-side serialization for
`action_batch` that mirrors the report safety contract:

```json
{
  "results": [
    {
      "success": true,
      "message": "open"
    }
  ],
  "skipped": [
    {
      "name": "after",
      "stop_on_failure": true
    }
  ],
  "success": true
}
```

The runner report should omit:

- action result `data`
- skipped action `parameters`

## Boundaries

- Keep the change in `automation_runner.reports`.
- Do not change `automation_core.actions` behavior or tests.
- Do not redact in-place; build a report-safe dictionary.
- Do not remove the `action_batch` field itself.
- Keep `success`, `message`, skipped action `name`, and `stop_on_failure`.

## Testing Strategy

- Add a runner report test where executed result `data` contains a token-like
  value.
- Add a skipped action with sensitive parameters.
- Assert the report `action_batch` omits both raw fields.
- Run focused report tests, then full suite and production review scripts.
