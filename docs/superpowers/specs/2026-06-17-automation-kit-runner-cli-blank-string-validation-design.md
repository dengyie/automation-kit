# Runner CLI Blank String Validation Design

## Goal

Make explicit CLI string arguments reject whitespace-only values so runner
command-line inputs match the stricter config-backed validation already in
place.

## Problem

`automation_runner.cli._merge_config(...)` currently copies CLI strings into
`RunnerConfig` with plain truthiness:

- `factory=args.factory or config.factory`
- `workflow_factory=args.workflow_factory or config.workflow_factory`
- `url=args.url or config.url`
- `app_id=args.app_id or config.app_id`

That means explicit CLI values like `"   "` survive as present strings once
they are passed directly to built-in workflow constructors or required-option
checks.

Examples of the current bad behavior:

- `automation-runner run damai-web-smoke --url "   " --json`
  succeeds instead of rejecting the missing URL.
- `automation-runner run damai-android-smoke --app-id "   " --json`
  succeeds instead of rejecting the missing app ID.
- `automation-runner run --workflow-factory "   " --json`
  fails later in import loading instead of at input validation time.
- `automation-runner run damai-web-smoke --live --factory "   " ...`
  fails later in import loading instead of at input validation time.

## Proposed Shape

- Keep the fix inside `automation_runner.cli`.
- Normalize explicit CLI string arguments for:
  - `factory`
  - `workflow_factory`
  - `url`
  - `app_id`
- Treat strings whose `strip()` result is empty as missing values for built-in
  required-field checks.
- Reject explicit blank `--factory` and `--workflow-factory` with the existing
  import-path error message:
  - `import path must use module:object`
- Preserve config-backed validation in `automation_runner.config`.
- Leave `automation_core` unchanged.

## Architecture

`automation_runner.cli` owns command-line argument semantics, so the CLI should
clean up explicit string arguments before required-option checks and factory
loading. A tiny helper for optional CLI strings keeps the change local and
avoids widening `RunnerConfig` or core interfaces.

## Compatibility Notes

- Missing CLI values still fall back to config values.
- Non-empty CLI strings remain unchanged.
- Whitespace-only CLI strings stop counting as valid runtime input.
- Config-backed strings keep their current error behavior in
  `automation_runner.config`.

## Testing Strategy

- Add CLI regression tests for blank `--url` on the built-in web workflow.
- Add CLI regression tests for blank `--app-id` on the built-in Android
  workflow.
- Add CLI regression tests for blank `--factory` and blank
  `--workflow-factory`.
- Run focused red checks first, then focused green checks, then all runner
  tests, then the full repository suite.
