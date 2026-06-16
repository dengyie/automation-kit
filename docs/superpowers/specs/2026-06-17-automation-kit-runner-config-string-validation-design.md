# Runner Config String Validation Design

## Goal

Reject non-string runner configuration values for string fields at config-load
time.

## Problem

`load_runner_config(...)` currently reads optional string fields with
`str(value)`. That makes invalid dictionary-backed config look valid:

```python
DictConfigSource({"factory": 123})
```

becomes `"123"` and later fails as an import-path error. Similar issues can
hide bad `workflow_factory`, `url`, or `app_id` values until workflow selection
or execution. For scheduled automation apps, that pushes operator mistakes away
from the configuration boundary and makes failures harder to diagnose.

Environment-backed config still arrives as strings, so this affects primarily
dictionary/file-style sources and tests.

## Proposed Shape

- Keep missing optional string config values as `None`.
- Accept only real `str` values for:
  - `factory`
  - `workflow_factory`
  - `url`
  - `app_id`
- Raise `ValueError("config <key> expected string")` for non-string values.
- Keep bool and parameter validation unchanged.
- Keep CLI argument parsing unchanged; argparse already supplies strings for
  these fields.

## Architecture

The change belongs in `automation_runner.config` because these keys are runner
configuration fields, not core automation primitives. `automation_core.config`
should remain a generic source abstraction and should not learn runner-specific
field names.

## Testing Strategy

- Add runner config tests for non-string `factory`, `workflow_factory`, `url`,
  and `app_id` values.
- Add a CLI test proving invalid config is rejected before a live factory is
  loaded.
- Keep existing environment and CLI override tests passing.
- Run focused runner config/CLI tests, then the full suite.
