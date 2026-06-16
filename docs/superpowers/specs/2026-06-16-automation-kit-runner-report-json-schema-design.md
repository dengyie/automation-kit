# Runner Report JSON Schema Design

## Goal

Add a machine-readable JSON Schema document for runner report schema version
`"1"`.

## Problem

Runner JSON reports now include a top-level `schema_version`, but consumers
still need to infer the full report shape from prose documentation and tests.
That makes external schedulers, scripts, and future automation tooling more
fragile when the report contract evolves.

## Proposed Shape

Add:

```text
docs/report-schema-v1.json
```

The schema should describe the current top-level runner report fields:

- `schema_version`
- `workflow`
- `workflow_factory`
- `session_factory`
- `workflow_context`
- `success`
- `status`
- `run_id`
- `run_state`
- `live`
- `elapsed_seconds`
- `events`
- `session`
- `actions`
- `action_batch`
- `artifacts`
- `error`

The schema is documentation and compatibility metadata. It should not add a
runtime validation dependency or change report emission.

## Boundaries

- Keep the schema under `docs`.
- Keep report construction in `automation_runner.reports` unchanged.
- Do not add a JSON Schema runtime dependency.
- Do not change `automation_core`.
- Do not version event envelope payloads in this slice.
- Allow event payloads and artifact metadata to remain extensible objects.

## Testing Strategy

- Add a test that loads `docs/report-schema-v1.json`.
- Compare schema top-level `required` and `properties` keys with a real
  `build_report(...).to_dict()` payload.
- Assert the schema fixes `schema_version` to `"1"`.
- Assert important nested sections such as `session`, `run_state`, `actions`,
  `artifacts`, and `action_batch` document the safe report fields.
