# Runner Param Validation Design

## Goal

Validate `automation-runner run --param` syntax before any workflow executes,
even when the selected workflow is a built-in example.

## Problem

`--param` is a generic runner option documented as `KEY=VALUE`, but the CLI
currently parses it only for custom workflow factories. A command such as:

```bash
automation-runner run damai-web-smoke --json \
  --url https://example.test/damai \
  --param missing-equals
```

can complete successfully because built-in workflows do not read custom
parameters. That makes operator mistakes difficult to see in scripts and CI.

## Proposed Shape

- Parse `--param` once for every `run` command before workflow execution.
- Keep passing parsed parameters only to custom workflow factories through
  `WorkflowOptions.parameters`.
- Keep built-in Damai examples unchanged; they continue to use dedicated
  `--url` and `--app-id` options.
- Return the existing CLI usage error message for invalid parameter syntax:
  `--param must use KEY=VALUE`.

## Architecture

The validation belongs in `automation_runner.cli` because `--param` is a runner
CLI contract. `automation_core` should not know about workflow parameters,
business workflows, or command-line parsing.

## Testing Strategy

- Add a red CLI test showing invalid `--param` fails for a built-in workflow
  before any session is created.
- Keep existing custom workflow parameter tests unchanged.
- Run focused CLI tests and the full suite.
