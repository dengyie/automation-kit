# Runner Config Workflow Parameters Design

## Goal

Let runner configuration sources provide generic workflow parameters for custom
workflow factories.

## Problem

Custom workflows can already receive CLI parameters through repeated
`--param KEY=VALUE` flags. That works for local runs, but scheduled and
deployed automation apps often provide configuration through dictionaries or
environment variables.

The runner already supports environment-backed config for standard fields such
as `json`, `url`, and `workflow_factory`. Workflow parameters should use the
same runner config path without adding business-specific fields to
`automation_core`.

## Proposed Shape

Add `parameters` to `RunnerConfig`:

```python
RunnerConfig(parameters={"account": "test-user", "city": "shanghai"})
```

`load_runner_config(...)` should read:

- mapping values from dictionary config sources,
- JSON object strings from environment config sources.

Environment example:

```bash
AUTOMATION_RUNNER_PARAMETERS='{"account":"test-user","city":"shanghai"}'
```

CLI `--param KEY=VALUE` values should be merged over config parameters:

```text
config: {"city": "beijing", "account": "config-user"}
cli:    --param city=shanghai
final:  {"city": "shanghai", "account": "config-user"}
```

## Boundaries

- Keep parsing in `automation_runner.config` and merging in
  `automation_runner.cli`.
- Do not change `automation_core.config`.
- Do not introduce workflow-specific parameter names.
- Do not serialize raw `WorkflowOptions` as top-level report data.
- Reject malformed parameter config before loading live factories.

## Validation Rules

- Missing parameters default to `{}`.
- Dictionary config values must be string keys and string values.
- Environment string values must parse as a JSON object.
- JSON object keys and values must be strings.
- Invalid values raise a `ValueError` with a user-facing message.
- CLI `--param` values override config values by key.

## Testing Strategy

- Add runner config tests for dictionary parameters, JSON-string parameters,
  and invalid values.
- Add CLI tests proving config parameters reach custom workflow factories.
- Add CLI tests proving CLI `--param` overrides config parameters.
- Run focused runner tests, full suite, and production review scripts.
