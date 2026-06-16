# Runner Report Schema Version Design

## Goal

Add an explicit schema version to runner JSON reports.

## Problem

`automation-runner run --json` emits structured reports consumed by scripts,
schedulers, and future automation tooling. The report shape has grown over
several slices with fields such as `workflow_context`, `run_state`, `events`,
`action_batch`, and safe artifact metadata.

Consumers currently have no stable version marker to distinguish this report
shape from future changes. That makes integrations more brittle as the
automation base evolves.

## Proposed Shape

Add a top-level field:

```json
{
  "schema_version": "1",
  "workflow": "damai-web-smoke"
}
```

Use a string value so future versions can use `"1.1"` or other semantic
markers without changing the field type.

## Boundaries

- Keep the field in `automation_runner.reports`.
- Do not change `automation_core`.
- Do not change workflow result models.
- Do not version event envelopes in this slice.
- Keep existing report fields intact and backward compatible except for the
  additive top-level field.

## Testing Strategy

- Add report unit coverage for `schema_version`.
- Add CLI JSON coverage proving emitted reports include the field.
- Run focused runner tests, full suite, and production review scripts.
