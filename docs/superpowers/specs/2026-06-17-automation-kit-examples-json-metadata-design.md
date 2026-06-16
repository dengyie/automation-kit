# Examples JSON Metadata Design

## Goal

Expose lightweight built-in workflow metadata from `automation-runner examples
--json` so automation tooling can choose a web or Android example and know which
runner option it must provide.

## Problem

The examples JSON discovery command currently returns only workflow names:

```json
{
  "dry_run": false,
  "workflows": [
    {"name": "damai-android-smoke"},
    {"name": "damai-web-smoke"}
  ]
}
```

That is enough for display, but not enough for a scheduler, setup wizard, or
agent to determine whether a workflow targets a website or Android app, or
whether it needs `--url` or `--app-id`.

## Proposed Shape

Keep the existing top-level shape and add stable fields to each workflow entry:

```json
{
  "name": "damai-web-smoke",
  "description": "Open a web URL and capture a screenshot artifact.",
  "platform": "web",
  "required_options": ["url"],
  "supports_dry_run": true
}
```

For Android:

```json
{
  "name": "damai-android-smoke",
  "description": "Launch an Android app and capture startup artifacts.",
  "platform": "android",
  "required_options": ["app_id"],
  "supports_dry_run": true
}
```

## Boundaries

- Keep metadata in `automation_runner.cli` next to the built-in `WORKFLOWS`
  registry.
- Do not add workflow registry primitives to `automation_core`.
- Do not scan packages or import live adapter/session factories.
- Keep output deterministic by sorting workflow names.
- Preserve the top-level `dry_run` and `workflows` fields.
- Keep plain text `automation-runner examples` behavior unchanged.

## Testing Strategy

- Update the existing CLI examples JSON tests to assert the richer workflow
  entries.
- Keep the plain text discovery test to prove behavior remains unchanged.
- Run focused CLI tests, then the full suite.
- Run the production review scripts and manually check the boundary: no
  business metadata moved into `automation_core`.
