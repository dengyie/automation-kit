# Artifact Path Component Sanitization Design

## Goal

Keep every `ArtifactStore` path inside the configured artifact root, even when
callers pass path-like `run_id`, `artifact_type`, or artifact names.

## Problem

`ArtifactStore.build_path(...)` currently sanitizes only the artifact `name`.
The generated layout is:

```text
<artifact-root>/<run-id>/<artifact-type>/<artifact-name>
```

Because `run_id` and `artifact_type` are joined directly, a caller can pass
values such as `../outside` or `../../trace` and produce paths outside the
intended namespace. In normal adapter usage `run_id` comes from
`SessionInfo.identifier` and `artifact_type` comes from workflow code, but both
are still boundary inputs for a reusable automation base.

This is a generic storage-contract concern, not a Damai or Dianping workflow
concern.

## Proposed Shape

- Treat `run_id`, `artifact_type`, and artifact `name` as path components.
- Strip directory prefixes from path-like values by taking the final segment.
- Reject empty, `.`, and `..` components.
- Normalize spaces to `_` for all three components.
- Preserve the existing artifact name behavior so current callers keep working.
- Keep `ArtifactRecord.name` as the original caller-provided artifact name for
  metadata/debugging compatibility; only the stored path uses sanitized
  components.

## Architecture

The behavior belongs in `automation_core.artifacts.store` because it defines the
business-agnostic artifact storage contract shared by Selenium, Appium, dry
runs, and future adapters.

Adapters should continue to delegate path construction to `ArtifactStore`.
Runner reports and report schemas should remain unchanged because they already
serialize the resulting artifact path.

## Testing Strategy

- Add artifact store tests proving path-like `run_id` and `artifact_type` values
  do not escape the root and are normalized to their final component.
- Add tests proving invalid `run_id` and `artifact_type` values raise
  `ValueError` with field-specific messages.
- Keep the existing artifact name normalization and metadata tests passing.
- Run focused artifact tests and the full suite.
