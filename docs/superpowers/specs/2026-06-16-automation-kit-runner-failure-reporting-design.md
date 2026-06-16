# Runner Failure Reporting Design

## Goal

Make `automation_runner` emit a stable JSON report even when workflow
construction or session startup fails.

## Problem

The runner already serializes successful workflow results and workflow-run
failures. But if a session factory or workflow factory raises before
`workflow.run()` returns, `automation_runner.cli.main()` currently lets the
exception escape. That leaves live automation runs without a structured report
and forces callers to handle Python exceptions instead of a report contract.

## Proposed Shape

Keep the change in the runner layer:

- add a small helper that turns startup exceptions into an
  `ExampleWorkflowResult`,
- synthesize a minimal `SessionInfo` when a session never started,
- reuse `build_report(...)` so the JSON shape stays consistent,
- keep `--json` and `--report-file` behavior identical for both success and
  failure paths.

Use a stable fallback session identity when startup fails:

```python
SessionInfo(
    driver_name="unavailable",
    platform="unknown",
    identifier=f"{workflow_name}-failed-run",
)
```

The JSON report should still expose:

- `workflow`
- `success`
- `status`
- `run_id`
- `run_state`
- `live`
- `events`
- `session`
- `actions`
- `artifacts`
- `error`

For startup failures, `session` should be the fallback identity above, and the
report should carry a failure error message from the original exception.

## Boundaries

- Do not change `automation_core` for this slice.
- Do not introduce a second report model.
- Do not hide normal workflow exceptions from `ExampleWorkflow.run()`.
- Do not change existing successful-report output.

## Testing Strategy

- Add a CLI test proving live session factory failures still emit JSON and
  write the report file.
- Add a CLI test proving workflow factory failures also emit JSON.
- Keep existing successful and workflow-runtime failure tests green.
- Run the full suite and production review scripts before committing.
