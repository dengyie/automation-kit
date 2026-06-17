# Runner Param Key Validation Design

## Goal

Make `automation-runner run --param KEY=VALUE` reject blank parameter keys even
when the input technically contains an equals sign.

## Problem

The CLI currently treats a parameter as valid when the raw key portion before
`=` is non-empty. That means values such as:

```bash
automation-runner run --workflow-factory my.workflow:create_workflow \
  --param "   =value"
```

produce an `options.parameters` dictionary with a whitespace-only key. Custom
workflow code then receives a parameter that is difficult to inspect, override,
or document.

The existing validation already rejects missing equals signs and empty raw
keys. It should also reject keys that become empty after trimming whitespace.

## Proposed Shape

- Keep validation in `automation_runner.cli`, where `--param` is parsed.
- Reject any `--param` whose key portion is empty after `strip()`.
- Preserve the existing error message: `--param must use KEY=VALUE`.
- Preserve value behavior, including empty values and values containing `=`.
- Do not normalize or trim valid keys in this slice.
- Do not change `automation_core`; workflow parameters are runner-layer CLI
  inputs.

## Architecture

`automation_runner.cli._parse_parameters(...)` already centralizes CLI
parameter parsing for both built-in and custom workflows. Tightening the key
predicate there gives all run modes the same behavior without touching workflow
factories, config sources, reports, or core runtime primitives.

## Compatibility Notes

- `--param account=test-user` remains unchanged.
- `--param token=a=b` remains unchanged because only the first `=` splits key
  from value.
- `--param empty=` remains valid; workflows may intentionally pass empty string
  values.
- Only blank keys such as `"=value"`, `"   =value"`, and `"\t=value"` are
  rejected.

## Testing Strategy

- Add focused CLI tests showing whitespace-only parameter keys fail before a
  workflow or session is created.
- Keep the existing tests for repeated parameters, values containing `=`, and
  CLI-over-config override behavior unchanged.
- Run focused CLI validation tests first, then runner regression tests, then the
  full repository suite.
