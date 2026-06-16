# Artifacts

Artifacts are debug evidence captured during automation runs. They must stay
business-agnostic so web and Android workflows can share the same report and
storage contract.

## Storage Layout

Use `ArtifactStore` to derive paths:

```text
<artifact-root>/<run-id>/<artifact-type>/<artifact-name>
```

Examples:

```text
artifacts/damai-web-smoke-dry-run/screenshot/home.png
artifacts/damai-android-smoke-dry-run/page_source/startup.xml
artifacts/run-42/ui_tree/startup.json
```

The default artifact root is `artifacts`. Tests may inject a temporary root.

## Naming Rules

- Use stable run IDs from `SessionInfo.identifier`.
- Use generic artifact types such as `screenshot`, `page_source`, `ui_tree`,
  `trace`, or `log`.
- Keep artifact names local to the artifact type, for example `home.png` or
  `startup.xml`.
- `run_id`, `artifact_type`, and artifact names are all treated as single path
  components. `ArtifactStore` strips directories, rejects empty, `.`, and `..`
  components, and normalizes spaces to `_`.

## Report Attachment

Workflow results expose artifacts as `ArtifactHandle` values. Runner reports
serialize only:

- `artifact_type`
- `path`

Raw bytes, page source text, image data, tokens, cookies, action `data`, and
skipped action parameters must not be embedded in JSON reports.

## Adapter Responsibilities

Adapters own how artifact bytes are captured:

- Selenium sessions may write screenshots, page source, and `ui_tree`
  snapshots when the driver exposes `page_source`.
- Appium sessions may write screenshots, page source, and `ui_tree`
  snapshots when the driver exposes `page_source`.
- Future adapters may add UI trees, traces, logs, or snapshots.

Adapters should still use the shared path contract above and should not put
business selectors, target URLs, package names, or credentials into
`automation_core`.

## Dry Runs

Dry-run sessions may return deterministic artifact paths without writing files.
This keeps the default CLI and tests offline while preserving the same report
shape as live workflows.
