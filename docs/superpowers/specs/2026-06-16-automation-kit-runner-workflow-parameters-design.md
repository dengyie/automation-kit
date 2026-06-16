# Runner Workflow Parameters Design

## Goal

Allow custom workflow factories to receive generic runner parameters without
adding business-specific fields to `automation_core`.

## Problem

The runner can load a custom workflow factory and pass typed runner metadata
through `WorkflowContext` and `WorkflowOptions`, but custom workflows currently
only receive fixed options such as `url` and `app_id`. That is enough for the
initial Damai examples, but it is too narrow for a reusable automation base
where each website or Android app may need its own input names.

Adding more named fields to core or runner options for every business domain
would couple the base to specific applications. The runner needs a small,
business-agnostic parameter channel instead.

## Proposed Shape

Add a repeated CLI option:

```bash
automation-runner run --workflow-factory my_package.workflow:create_workflow \
  --json \
  --param account=test-user \
  --param city=shanghai
```

The runner parses each `KEY=VALUE` pair into a dictionary and exposes it as:

```python
options.parameters
```

The values remain strings. Workflow-specific parsing and validation belongs to
the workflow package, not to `automation_core` or `automation_runner`.

## Boundaries

- Keep the parameter feature in `automation_runner`.
- Do not add business fields to `automation_core`.
- Do not add a persisted workflow DSL.
- Do not serialize raw workflow parameters into top-level reports.
- Reject malformed parameters before loading live session factories.

## Validation Rules

- Accept repeated `--param KEY=VALUE` flags.
- Reject values without `=`.
- Reject empty keys.
- Preserve values containing additional `=` characters.
- Let later repeated keys override earlier values, matching common CLI config
  precedence behavior.

## Testing Strategy

- Add unit coverage for `WorkflowOptions.parameters` and `to_dict()`.
- Add CLI coverage proving custom workflow factories receive parsed
  parameters.
- Add CLI coverage proving malformed parameters fail before a live session
  factory is imported.
- Run focused runner tests, then the full suite and production review scripts.
