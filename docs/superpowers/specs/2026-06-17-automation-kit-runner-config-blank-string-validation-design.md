# Runner Config Blank String Validation Design

## Goal

Make runner configuration reject whitespace-only string values for key runtime
fields so config-backed inputs match CLI expectations.

## Problem

`automation_runner.config._optional_string(...)` currently accepts any string
value, including blank strings such as `"   "` or `"\t"`.

That allows config like:

```python
{"factory": "   "}
{"workflow_factory": "   "}
{"url": "   "}
{"app_id": "   "}
```

to load successfully into `RunnerConfig`.

Those values are not meaningfully different from missing input, but they can
change control flow:

- a blank `factory` counts as present and may trigger factory loading,
- a blank `workflow_factory` counts as present and may bypass the usual
  "workflow or --workflow-factory is required" error,
- blank `url` or `app_id` can satisfy truthy/required checks inconsistently
  depending on the caller.

## Proposed Shape

- Keep validation in `automation_runner.config`, where config-backed runtime
  fields are parsed.
- Treat string values whose `strip()` result is empty as invalid for:
  - `factory`
  - `workflow_factory`
  - `url`
  - `app_id`
- Preserve existing error messages:
  - `config <key> expected string`
- Do not change boolean parsing.
- Do not change `automation_core`; this remains runner configuration behavior.

## Architecture

`_optional_string(...)` already centralizes optional runner string parsing.
Tightening it there keeps dictionary and environment-backed config behavior
consistent without changing CLI argument parsing, workflow factories, or report
serialization.

## Compatibility Notes

- Missing values still resolve to `None`.
- Non-empty strings remain unchanged.
- Only blank strings made of whitespace become invalid.

## Testing Strategy

- Add focused config tests for blank strings across `factory`,
  `workflow_factory`, `url`, and `app_id`.
- Add one CLI regression test proving blank config `url` still fails before
  workflow execution rather than being treated as a valid value.
- Run focused config/CLI tests first, then runner regression tests, then the
  full repository suite.
