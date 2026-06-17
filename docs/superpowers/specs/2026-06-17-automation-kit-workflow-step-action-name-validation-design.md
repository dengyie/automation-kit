# Workflow Step Action Name Validation Design

## Goal

Make `WorkflowStep.action(...)` reject obviously invalid action names at the
example authoring boundary before they become `ActionRequest` values.

## Problem

`WorkflowStep.action(...)` currently accepts any `name` value and stores it
directly in the step descriptor.

That allows values such as:

- `""`
- `"   "`
- `"."`
- `".."`
- `None`
- `123`

to be embedded in a workflow step without immediate feedback.

Later execution then turns those values into `ActionRequest` objects. Fake
sessions can accidentally accept them, while real adapters may fail deeper in
driver dispatch. That makes the workflow authoring contract weaker than the
artifact-step contract and pushes feedback to the wrong layer.

## Proposed Shape

- Keep `WorkflowStep` as an example-layer authoring helper.
- Add a small action-name validator used only by `WorkflowStep.action(...)`.
- Reject non-string action names.
- Reject action names whose final trimmed path component is:
  - empty,
  - `.`,
  - `..`.
- Raise `ValueError("invalid workflow action name")` directly from the helper
  constructor.
- Do not change `automation_core.actions.ActionRequest`; the core package stays
  generic and business-agnostic.
- Do not add a registry of valid action names in this slice. Adapter-specific
  action vocabularies still belong to adapters and workflow tests.

## Architecture

This belongs in `examples.workflows` because `WorkflowStep.action(...)` is an
example-layer authoring helper. `automation_core.actions` should continue to
represent generic action requests without knowing about workflow authoring
rules or specific web/mobile action vocabularies.

The helper should mirror the artifact-name guard closely enough that workflow
authors get consistent constructor-time feedback for invalid step names while
valid custom adapter actions remain possible.

## Compatibility Notes

- Valid action names like `open`, `click`, `tap`, and `wait_for_element` remain
  unchanged.
- Existing built-in Damai workflows continue to construct the same steps.
- Adapter-level handling of unknown but string action names remains unchanged.
- Invalid names are rejected earlier and consistently across fake and real
  sessions.

## Testing Strategy

- Add focused tests for `WorkflowStep.action(...)` rejecting:
  - non-string names,
  - `""`
  - `"   "`
  - `"."`
  - `".."`
- Add one regression test proving valid action names still construct normally
  and preserve parameters.
- Run the focused web example tests first, then both web and Android example
  workflow tests, then the full repository suite.
