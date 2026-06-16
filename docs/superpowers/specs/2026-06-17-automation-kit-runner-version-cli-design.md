# Runner Version CLI Design

## Goal

Expose the automation-kit package version through the runner command line.

## Problem

`automation-kit` already has a project version in `pyproject.toml` and
`automation_core.__version__`, but runner consumers cannot ask the installed
CLI which version they are invoking. This makes scheduler logs, CI scripts, and
packaged smoke checks less diagnosable.

## Proposed Shape

Add a top-level CLI flag:

```bash
automation-runner --version
python -m automation_runner --version
```

Expected output:

```text
automation-runner 0.1.0
```

## Architecture

- Keep version display in `automation_runner.cli`.
- Reuse the existing `automation_core.__version__` constant.
- Do not add packaging metadata reads or runtime dependencies.
- Do not change runner report `schema_version`.
- Do not touch `automation_core` beyond reading its version constant.

## Testing Strategy

- Add a direct CLI test for `main(["--version"])`.
- Add a module-entrypoint subprocess test for
  `python -m automation_runner --version`.
- Run full tests and production review before commit.
