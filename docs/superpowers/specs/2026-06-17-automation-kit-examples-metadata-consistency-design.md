# Examples Metadata Consistency Design

## Goal

Make `automation-runner examples --json` fail with a clear CLI error when a
built-in workflow is registered without matching discovery metadata.

## Problem

Built-in workflow discovery now has two adjacent registries in
`automation_runner.cli`:

- `WORKFLOWS`
- `WORKFLOW_METADATA`

That keeps the change simple and avoids adding a registry abstraction too early.
The tradeoff is that a future built-in workflow can be added to `WORKFLOWS`
without a matching `WORKFLOW_METADATA` entry. Today that path would raise a
raw `KeyError` while building the JSON list, which is poor behavior for a
machine-facing discovery command.

## Proposed Shape

Keep metadata in `automation_runner.cli`, but validate metadata before
serializing the JSON workflow list.

If a workflow is missing metadata:

```text
missing workflow metadata: new-workflow
```

The command should:

- return exit code `2`,
- write the message to stderr,
- write no partial JSON to stdout.

Plain text `automation-runner examples` should remain unchanged and should not
require metadata, because that path only lists workflow names.

## Boundaries

- Keep the behavior in `automation_runner.cli`.
- Do not add a workflow registry model to `automation_core`.
- Do not scan packages or load live session factories.
- Do not change the successful JSON discovery shape.
- Keep the validation deterministic and based only on built-in registries.

## Testing Strategy

- Add a CLI regression test that temporarily registers an extra workflow
  without metadata.
- Verify `examples --json` returns code `2`, emits the clear message on stderr,
  and prints no stdout.
- Verify existing examples JSON tests still pass.
- Run full tests and production review scripts.
