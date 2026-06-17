# Runner Config Param Key Validation Design

## Goal

Make runner configuration reject whitespace-only workflow parameter keys so
config-backed parameters follow the same authoring boundary as CLI `--param`
inputs.

## Problem

`automation_runner.config._optional_parameters(...)` currently accepts any
string key/value pair from dictionary config sources or environment-backed JSON
objects. That means these values are currently accepted:

```python
{"parameters": {"   ": "value"}}
{"parameters": {"\t": "value"}}
```

and:

```bash
AUTOMATION_RUNNER_PARAMETERS='{"   ":"value"}'
```

After the recent CLI fix, `--param "   =value"` is rejected, but the same blank
key can still enter through config sources. That leaves two runner input paths
with inconsistent validation.

## Proposed Shape

- Keep validation in `automation_runner.config`, where config-backed parameter
  objects are parsed.
- Reject parameter keys that are not strings.
- Reject parameter keys whose `strip()` value is empty.
- Preserve the existing user-facing error message:
  `config parameters expected string keys and values`.
- Preserve value behavior: values must still be strings, including empty string
  values.
- Do not normalize or trim valid keys in this slice.
- Do not change `automation_core`; this remains a runner configuration concern.

## Architecture

`load_runner_config(...)` already centralizes dictionary and environment-backed
runner parsing. Tightening `_optional_parameters(...)` there keeps validation
consistent across config sources without changing workflow factories, CLI merge
order, or report serialization.

## Compatibility Notes

- Config keys like `"account"` and `"city"` remain unchanged.
- Empty string values remain valid if workflows intentionally use them.
- JSON object parsing behavior remains unchanged.
- Only blank keys such as `"   "` and `"\t"` are newly rejected.

## Testing Strategy

- Add focused config tests for blank keys from dictionary and JSON-string
  config sources.
- Keep existing config parameter parsing tests unchanged.
- Run focused config tests first, then runner regression tests, then the full
  repository suite.
