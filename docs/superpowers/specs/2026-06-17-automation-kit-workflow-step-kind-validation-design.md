# Workflow Step Kind Validation Design

## Goal

Make `run_workflow_steps(...)` reject unsupported `WorkflowStep.kind` values
with a clear structured failure instead of letting them drift into the artifact
branch and fail indirectly.

## Problem

`WorkflowStep` is an example-layer authoring helper with two intended kinds:

- `action`
- `artifact`

But `run_workflow_steps(...)` currently checks only for `action` explicitly.
Any other `kind` value falls through the non-action path and is treated like an
artifact step.

That creates an unclear contract:

- authoring mistakes such as `WorkflowStep(kind="navigate", ...)` are not
  rejected directly,
- the resulting failure message depends on later artifact behavior,
- the failure can point at the wrong layer of the system.

For a toolkit meant to support easy composition of automation workflows, this
is a poor authoring boundary.

## Proposed Shape

- Keep `WorkflowStep` as the same lightweight dataclass helper.
- Keep the supported kinds limited to `action` and `artifact`.
- In `run_workflow_steps(...)`, when a step with any other `kind` is reached:
  - flush already queued action steps first,
  - preserve already completed actions and artifacts,
  - return a failed `ExampleWorkflowResult`,
  - set `error` to a typed message such as:
    `ValueError: unsupported workflow step kind: navigate`.
- Keep the session cleanup behavior in the existing `finally` block.
- Do not move this validation into `automation_core`.

## Architecture

This belongs in `examples.workflows`, not `automation_core`, because step kinds
are an example-layer authoring abstraction. Core runtime contracts should not
need to know about this helper's mini vocabulary.

Validation should happen inside the step execution loop, not as a full upfront
pre-scan, so evidence from already completed earlier steps is preserved.

## Compatibility Notes

- Existing `action` and `artifact` workflows stay unchanged.
- Existing action-batch failure behavior stays unchanged.
- Existing artifact-capture failure behavior stays unchanged.
- Unknown step kinds become explicit structured failures instead of indirect
  downstream errors.

## Testing Strategy

- Add a web example regression test with:
  - one successful action,
  - one successful artifact,
  - one unsupported step kind.
- Assert the failed result preserves the earlier action and artifact evidence,
  keeps `batch_result`, sets the typed error message, and stops the session.
- Run the focused example tests first, then the full repository suite.
