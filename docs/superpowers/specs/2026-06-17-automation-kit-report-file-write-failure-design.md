# Report File Write Failure Design

## Goal

Make `automation-runner run --json --report-file <path>` fail cleanly when
the report file cannot be written.

## Problem

The runner currently serializes a JSON report, prints it to stdout, and then
writes the same payload to `--report-file`. If the file write fails after
stdout has already been emitted, schedulers can observe a valid-looking report
followed by an unhandled traceback. That makes the CLI contract ambiguous: the
run may look reportable even though the requested durable report was never
created.

The failure is reachable when the report path parent is not a directory,
permissions deny directory creation, or the target path cannot be written.

## Proposed Shape

- Build the JSON payload exactly as today.
- When `--report-file` is provided, create parent directories and write the
  file before printing stdout.
- If report-file writing fails, return a clean CLI error with exit code `2`.
- Do not print partial JSON stdout when the requested report file cannot be
  written.
- Keep successful stdout/file payload parity byte-for-byte, including the final
  newline.

## Architecture

This remains a runner-layer concern in `automation_runner.cli`. The core
automation contracts should not know about CLI report destinations,
filesystem paths, or process exit codes.

Use a narrow helper around the existing report emission path rather than
changing report schemas or workflow execution. The helper should translate
`OSError` from directory creation or file writing into the existing CLI error
path.

## Testing Strategy

- Add a red CLI test using a report path whose parent component is an existing
  file.
- Assert the command exits with code `2`, writes no stdout JSON, emits a useful
  stderr message, and includes no traceback.
- Keep existing success and failure report-file parity tests passing.
- Run the focused CLI tests and the full suite.
