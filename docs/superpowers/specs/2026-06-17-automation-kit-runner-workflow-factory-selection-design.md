# Runner Workflow Factory Selection Design

## Goal

Make `automation-runner run` choose exactly one workflow source: either a
built-in workflow name or a custom workflow factory.

## Problem

The runner supports both built-in workflow names and `--workflow-factory`, but
the current CLI path can accept both at the same time. In that ambiguous state,
the runner may execute the custom factory while reporting the built-in workflow
name as the workflow identifier. That makes scheduler logs and JSON reports
harder to trust.

Environment/config defaults add one more edge case: a configured
`workflow_factory` should not silently override an explicit positional workflow
provided on the command line. The existing documentation says CLI arguments take
precedence over environment values, so a positional workflow should disable the
configured custom factory unless `--workflow-factory` was also provided
explicitly.

## Proposed Shape

- Reject commands that provide both positional `workflow` and explicit
  `--workflow-factory`.
- When positional `workflow` is provided and `workflow_factory` comes only from
  config, run the positional built-in workflow and clear the configured custom
  workflow factory.
- Keep commands with only `--workflow-factory` unchanged.
- Keep commands with only config-provided `workflow_factory` unchanged.

## Architecture

The selection rule belongs in `automation_runner.cli` because it is a command
line precedence contract. `automation_core` should remain unaware of built-in
workflow names, custom factory import paths, or environment configuration.

## Testing Strategy

- Add a red CLI test proving explicit `workflow + --workflow-factory` is
  rejected before any session is created.
- Add a red CLI test proving a positional workflow overrides a config-provided
  workflow factory.
- Keep existing custom workflow and built-in workflow tests unchanged.
- Run focused CLI tests and the full suite.
