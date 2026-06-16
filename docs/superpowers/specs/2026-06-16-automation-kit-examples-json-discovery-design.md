# Examples JSON Discovery Design

## Goal

Make built-in example workflow discovery machine-readable.

## Problem

`automation-runner examples --dry-run` currently prints plain text workflow
names. That is easy for humans, but automation systems, scripts, and future
tooling need a stable JSON shape to discover built-in examples without parsing
free-form text.

The project already supports structured JSON for `automation-runner run`.
The examples listing should offer the same machine-readable option while
remaining deterministic and offline.

## Proposed Shape

Add `--json` to the `examples` subcommand:

```bash
automation-runner examples --json
```

Output:

```json
{
  "workflows": [
    {"name": "damai-android-smoke"},
    {"name": "damai-web-smoke"}
  ],
  "dry_run": false
}
```

With `--dry-run`, include `dry_run: true`:

```bash
automation-runner examples --dry-run --json
```

The plain text behavior remains unchanged when `--json` is not provided.

## Boundaries

- Keep behavior in `automation_runner.cli`.
- Only list built-in example workflows from `WORKFLOWS`.
- Do not scan arbitrary modules or load live session factories.
- Do not add business logic to `automation_core`.
- Keep output deterministic by sorting workflow names.

## Testing Strategy

- Add CLI tests for `examples --json`.
- Add CLI tests for `examples --dry-run --json`.
- Preserve existing plain text tests.
- Run focused CLI tests, full suite, and production review scripts.
