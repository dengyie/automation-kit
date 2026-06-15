# Adding A Workflow

`automation-kit` is split so business logic stays out of `automation_core`.

## Package Boundaries

- `automation_core`: generic runtime primitives only.
- `automation_runner`: command-line execution, JSON reports, and report files.
- `adapters`: Selenium/Appium session wrappers and startup errors.
- `examples`: business-specific workflow composition.

## Workflow Shape

A workflow factory should return an object with `run()`:

```python
from examples.damai_web import create_workflow

workflow = create_workflow(
    session_factory=make_session,
    url="https://example.test/damai",
)
result = workflow.run()
```

The lower-level helper remains available when you want direct function calls:

```python
from examples.damai_web import run_smoke_workflow
```

## Runner Commands

Dry listing:

```bash
automation-runner examples --dry-run
```

Dry workflow run:

```bash
automation-runner run damai-web-smoke --json \
  --url https://example.test/damai
```

Live Damai web smoke run:

```bash
automation-runner run damai-web-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --url https://example.test/damai
```

Live Damai Android smoke run:

```bash
automation-runner run damai-android-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --app-id cn.damai
```

## Report Contract

JSON reports currently include:

- `workflow`
- `workflow_factory`
- `success`
- `status`
- `run_id`
- `live`
- `elapsed_seconds`
- `events`
- `session`
- `actions`
- `artifacts`
- `error`

`events` contains serialized `EventEnvelope` records. Example workflows emit:

- `task.start` when the workflow session starts executing.
- `artifact` for each captured artifact.
- `error` when workflow execution raises an exception.
- `task.end` with `outcome` set to `succeeded` or `failed`.

Artifacts stay generic and are written by the runner layer.

## Adapter Rules

- Keep Selenium/Appium startup concerns in `adapters`.
- Surface startup failures as `AdapterStartupError`.
- Do not move selectors, URLs, or business flow into `automation_core`.
- Keep default tests offline and deterministic.
