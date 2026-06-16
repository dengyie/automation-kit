# Report Workflow Context Design

## Goal

Expose runner workflow context in JSON reports so automation applications can
inspect what executed without parsing CLI arguments or logs.

## Problem

Custom workflows can receive `WorkflowContext` and `WorkflowOptions`, but JSON
reports still expose only top-level fields such as `workflow`,
`workflow_factory`, and `session_factory`. External orchestrators need a
single structured place to read runner metadata.

## Proposed Shape

Add a `workflow_context` object to `RunnerReport`:

```json
{
  "workflow_context": {
    "workflow_name": "tests.runner.fixtures:create_context_workflow",
    "live": true,
    "workflow_factory": "tests.runner.fixtures:create_context_workflow",
    "session_factory": "tests.runner.fixtures:make_session"
  }
}
```

The report keeps existing top-level fields for compatibility. This phase does
not add a raw `workflow_options` object because options may include business
or environment-specific values such as URLs, app IDs, and report paths.

## Data Flow

1. CLI builds the existing `WorkflowContext`.
2. CLI passes the context to `build_report`.
3. `build_report` serializes a safe workflow context dictionary.
4. If no explicit context is supplied, `build_report` derives one from the
   existing report arguments.

## Non-Goals

- No raw action data in reports.
- No raw workflow options in reports.
- No changes to `automation_core`.
- No removal of existing top-level report fields.

## Testing Strategy

- Add unit coverage for `build_report(..., workflow_context=...)`.
- Add CLI coverage proving custom workflow reports include
  `workflow_context`.
- Keep existing report fields unchanged.
