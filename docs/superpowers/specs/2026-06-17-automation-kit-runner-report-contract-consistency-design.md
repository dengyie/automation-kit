# Runner Report Contract Consistency Design

## Goal

Tighten runner report contract consistency for schema version `"1"` so the
documented artifact/report contract matches the current emitted JSON report and
packaged schema without changing runtime report shape.

## Problem

The runner report contract now lives in several places:

- `automation_runner.reports.build_report(...)`
- `docs/report-schema-v1.json`
- `automation_runner/schemas/report-schema-v1.json`
- `docs/adding-a-workflow.md`
- `docs/artifacts.md`

Most of those sources already agree that artifact entries include:

- `artifact_type`
- `path`
- `metadata`

But `docs/artifacts.md` still says runner reports serialize only
`artifact_type` and `path`.

That mismatch is not just wording drift. It weakens the main purpose of the
report schema work:

- external consumers can read conflicting contract descriptions,
- future changes can accidentally preserve stale prose while tests stay green,
- operators may miss that metadata is intentionally present but redacted for
  sensitive keys.

## Proposed Shape

- Keep runner report schema version at `"1"`.
- Keep `automation_runner.reports.build_report(...)` runtime shape unchanged.
- Keep `automation_core` unchanged.
- Add tests that pin contract consistency across:
  - real sample report output,
  - documented report fields in `docs/adding-a-workflow.md`,
  - documented artifact report fields in `docs/artifacts.md`,
  - packaged schema parity with `docs/report-schema-v1.json`.
- Update `docs/artifacts.md` so its report attachment section matches the
  actual report contract:
  - artifact entries include `metadata`,
  - metadata stays generic and small,
  - report serialization redacts sensitive metadata keys.

## Architecture

This belongs in the runner documentation and report-schema test layer, not in
`automation_core`. The runtime serializer is already the source of truth for
emitted JSON. This slice makes the surrounding documentation and contract tests
strict enough that future drift becomes visible immediately.

## Compatibility Notes

- No top-level report keys change.
- No nested report fields change.
- No event payload structure changes.
- No artifact metadata behavior changes.
- Consumers already compatible with schema version `"1"` remain compatible.

## Testing Strategy

- Add a failing contract test that parses `docs/artifacts.md` and compares the
  documented artifact report fields with a real sample report artifact entry.
- Add a failing artifact-doc safety test for metadata/redaction wording if the
  current prose does not mention it.
- Keep existing schema parity and nested safe-field tests.
- Run focused report-schema tests first, then full runner tests, then the full
  repository suite.
