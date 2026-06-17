# Runner Cancelled Exit Code Design

## Goal

Give cancelled workflow runs a distinct CLI exit code so schedulers can
distinguish intentional cancellation from ordinary workflow failure even
without parsing JSON report payloads.

## Problem

`automation_runner.cli` already preserves cancellation in runtime and report
state:

- `ExampleWorkflowResult.state == TaskState.CANCELLED`
- `RunState.status == CANCELLED`
- report `status == "cancelled"`

But `automation-runner run ...` still returns exit code `1` for any
non-success result. That collapses cancelled and failed runs into the same
process-level contract.

For shell scripts, CI jobs, and schedulers, this means:

- JSON-aware consumers can distinguish cancelled runs,
- exit-code-only consumers cannot,
- the runner contract is less expressive than its own report contract.

## Proposed Shape

- Keep success exit code `0`.
- Keep workflow failure exit code `1`.
- Return exit code `130` for cancelled workflow results.
- Apply the cancelled exit code consistently for both:
  - `--json` report runs,
  - plain text summary runs.
- Do not change argument-validation or configuration errors; they still return
  exit code `2`.
- Do not change report schema or event payloads in this slice.

## Architecture

This is a runner CLI policy concern in `automation_runner.cli`.

`automation_core` should continue to model task and run cancellation, but it
should not know shell exit-code conventions. The CLI already translates runner
outcomes into process exit codes, so the new cancelled branch should stay
there.

Use a small helper so the exit-code mapping is defined once and reused by both
the JSON and plain-text run paths.

## Compatibility Notes

- Existing JSON reports remain unchanged.
- Existing failure exit code `1` remains unchanged.
- Existing CLI/config/schema validation exit code `2` remains unchanged.
- `success` remains `false` for cancelled runs for backward compatibility.

## Testing Strategy

- Update the existing cancelled JSON CLI test to expect exit code `130`.
- Add a plain-text cancelled workflow test to prove the same exit code is used
  when `--json` is not enabled.
- Run the focused cancelled CLI tests first, then the full runner and full
  repository test suites.
