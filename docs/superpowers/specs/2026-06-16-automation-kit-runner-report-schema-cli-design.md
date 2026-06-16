# Runner Report Schema CLI Design

## Goal

Expose runner report schema version `"1"` through the installed runner layer so
automation tools can discover the contract without reading repository docs.

## Problem

`docs/report-schema-v1.json` documents the current runner report contract, but
the schema is only available as a repository documentation file. A packaged
consumer or scheduler that invokes `automation-runner` should be able to fetch
the matching report schema directly from the runner surface.

## Proposed Shape

Add a runner subcommand:

```bash
automation-runner report-schema --version 1
```

It should print the JSON schema to stdout and return exit code `0`.

Unsupported versions should fail before printing a schema:

```bash
automation-runner report-schema --version 2
```

Expected stderr:

```text
unsupported report schema version: 2
```

Expected exit code: `2`.

## Architecture

- Add a small `automation_runner.schemas` package.
- Store `report-schema-v1.json` as package data inside that package.
- Add `load_report_schema(version: str = "1") -> Dict[str, object]`.
- Keep `docs/report-schema-v1.json` as the documented copy and test that it
  matches the package resource.
- Keep schema handling in `automation_runner`; do not change `automation_core`.
- Do not add a JSON Schema validation dependency.

## Boundaries

- No business-specific workflow, selector, URL, app ID, or adapter knowledge.
- No runtime validation of reports in this slice.
- No change to report emission or report schema version value.
- No change to event envelope or workflow result models.

## Testing Strategy

- Add schema loader tests proving version `"1"` loads and unsupported versions
  raise a clear `ValueError`.
- Add parity coverage proving the package schema equals
  `docs/report-schema-v1.json`.
- Add CLI tests for successful JSON output and unsupported version errors.
- Run full tests and production code quality review scripts before commit.
