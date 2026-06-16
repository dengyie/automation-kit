# Report Event Payload Redaction Design

## Goal

Redact common sensitive fields inside runner report event payloads before they
are serialized to JSON.

## Problem

Runner reports already redact artifact metadata keys that contain terms such as
`token`, `secret`, `password`, `cookie`, or `authorization`. Event payloads are
also included in runner JSON reports, but today they are serialized directly:

```python
events=[envelope.to_dict() for envelope in result.events]
```

`EventEnvelope.payload` is intentionally extensible. Custom workflows and future
adapters may include diagnostic details in event payloads, and those details can
easily contain secrets by key name. Without report-level redaction, a workflow
can leak credentials into stdout, report files, logs, or CI artifacts.

## Proposed Shape

- Keep event models in `automation_core.events` unchanged.
- Keep redaction in `automation_runner.reports`, where report-safe serialization
  already lives.
- Reuse the existing sensitive key terms:
  - `authorization`
  - `cookie`
  - `password`
  - `secret`
  - `token`
- Redact matching keys in event payload dictionaries by replacing their values
  with `"[redacted]"`.
- Apply the same key-based redaction recursively through nested dictionaries and
  dictionaries inside lists.
- Preserve non-sensitive payload values and event envelope fields.
- Keep schema shape unchanged; event payload remains an extensible object.

## Error Contract

Given an event payload:

```python
{
    "task_name": "checkout",
    "auth_token": "secret-token",
    "details": {
        "cookie": "session=abc",
        "attempt": 1,
    },
}
```

the report event payload should become:

```python
{
    "task_name": "checkout",
    "auth_token": "[redacted]",
    "details": {
        "cookie": "[redacted]",
        "attempt": 1,
    },
}
```

## Testing Strategy

- Add report serialization coverage for sensitive event payload keys.
- Include nested dictionaries and dictionaries inside lists.
- Verify non-sensitive fields remain unchanged.
- Verify artifact metadata redaction still works.
- Run focused report tests and then the full suite.
