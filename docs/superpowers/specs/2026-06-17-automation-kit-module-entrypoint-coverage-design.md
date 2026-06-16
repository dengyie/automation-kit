# Module Entrypoint Coverage Design

## Goal

Make the `python -m automation_runner` entrypoint directly testable while
preserving the existing CLI behavior.

## Problem

The runner package already supports module execution through
`automation_runner/__main__.py`, and a subprocess test proves the command works.
However, coverage reports show `automation_runner/__main__.py` at 0% because the
subprocess execution is outside the current coverage process. That leaves the
entrypoint wrapper easy to break without a direct unit signal.

## Proposed Shape

Add a tiny `run()` function in `automation_runner.__main__`:

```python
def run() -> int:
    return main()
```

Keep script execution as:

```python
if __name__ == "__main__":
    raise SystemExit(run())
```

## Boundaries

- Keep the behavior in `automation_runner`; do not move CLI entrypoint logic
  into `automation_core`.
- Do not change argument parsing or runner behavior.
- Do not introduce new runtime dependencies.
- Keep the existing subprocess module-entrypoint test.

## Testing Strategy

- Add a direct unit test proving `run()` delegates to `automation_runner.cli.main`.
- Add a direct script-path test proving `__main__` exits with the delegated
  status code.
- Keep the existing subprocess smoke test proving `python -m automation_runner`
  still executes.
