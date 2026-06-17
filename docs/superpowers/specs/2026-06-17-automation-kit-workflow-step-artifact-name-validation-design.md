# Workflow Step Artifact Name Validation Design

## Goal

Make `WorkflowStep.artifact(...)` reject obviously invalid artifact names at the
example authoring boundary instead of letting them slip into runtime execution.

## Problem

`WorkflowStep.artifact(...)` currently accepts any `name` string and stores it
as-is inside the step descriptor.

That means values such as:

- `""`
- `"   "`
- `"."`
- `".."` 

can be embedded in a workflow step without immediate feedback.

Later behavior then depends on the execution path:

- adapter-backed sessions may fail deeper in artifact path handling,
- simple fake sessions may appear to succeed,
- the workflow author gets feedback from the wrong layer.

For a reusable automation base, this weakens the authoring contract and makes
tests less representative of production behavior.

## Proposed Shape

- Keep `WorkflowStep` as a simple example-layer helper.
- Add a small artifact-name validator used only by
  `WorkflowStep.artifact(...)`.
- Reject non-string artifact names.
- Reject artifact names whose final trimmed path component is:
  - empty,
  - `.`,
  - `..`.
- Raise `ValueError("invalid workflow artifact name")` directly from the helper
  constructor.
- Do not add path normalization, renaming, or sanitization in this slice.
- Do not change `ArtifactStore` behavior; this is an earlier authoring-layer
  guard, not a replacement for storage validation.

## Architecture

This belongs in `examples.workflows` because `WorkflowStep` is an example-layer
authoring helper. `automation_core.artifacts` should keep protecting storage
paths independently, but workflow authors should get fast feedback before a run
starts.

The helper should stay small and local so the public authoring API remains
simple and the core package stays untouched.

## Compatibility Notes

- Valid artifact names like `home.png` and `after-click.html` remain unchanged.
- Existing artifact-store validation remains in place.
- Existing runtime artifact failure behavior remains unchanged.
- Invalid names are rejected earlier and more consistently across fake and real
  sessions.

## Testing Strategy

- Add focused tests for `WorkflowStep.artifact(...)` rejecting:
  - non-string names,
  - `""`
  - `"   "`
  - `"."`
  - `".."`
- Add one regression test proving valid names still construct normally.
- Run the focused web example tests first, then the full repository suite.
