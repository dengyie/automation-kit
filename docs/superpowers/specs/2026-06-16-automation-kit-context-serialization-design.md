# Context Serialization Design

## Goal

Give runner context models stable dictionary serialization for reports,
orchestrators, and external automation applications.

## Problem

`WorkflowContext` and `WorkflowOptions` are typed dataclasses, but callers that
need structured data must currently know their fields and hand-build
dictionaries. That risks drift between reports, tests, and external consumers.

## Proposed Shape

Add `to_dict()` to both models:

```python
context.to_dict()
options.to_dict()
```

`WorkflowContext.to_dict()` is safe for reports. `WorkflowOptions.to_dict()` is
available for explicit consumers, but runner JSON reports should still avoid a
raw `workflow_options` object.

## Non-Goals

- No new CLI flags.
- No report-level `workflow_options` field.
- No changes to `automation_core`.
- No business-specific context fields.

## Testing Strategy

- Unit tests for `WorkflowContext.to_dict()`.
- Unit tests for `WorkflowOptions.to_dict()`.
- Report tests continue proving `workflow_context` serialization.
