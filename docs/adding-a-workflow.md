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

## Creating A New Workflow

1. Put business-specific code under `examples/<domain>_<platform>/` or another
   package outside `automation_core`.
2. Accept an injected `session_factory` instead of constructing Selenium,
   Appium, or other live clients during import.
3. Start and stop the session inside the workflow helper with `try/finally`.
4. Return `ExampleWorkflowResult` with generic actions, artifacts, and optional
   structured events.
5. Expose `create_workflow(...)` so the runner can construct the workflow.
6. Add tests with fake sessions so default tests stay offline.

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

Artifacts stay generic. See `docs/artifacts.md` for storage layout, naming
rules, report attachment rules, and dry-run behavior.

## Artifact And Report Attachments

- Screenshots should use artifact type `screenshot`.
- HTML, XML, or mobile page dumps should use `page_source`.
- Structured UI dumps should use `ui_tree`.
- Traces and logs should use `trace` or `log`.
- JSON run reports should be written with `--report-file`.
- JSON reports should contain artifact paths only, not raw screenshot bytes,
  page source text, tokens, cookies, or action `data`.
- Dry workflows may return deterministic artifact paths without writing files.

## Adapter Rules

- Keep Selenium/Appium startup concerns in `adapters`.
- Surface startup failures as `AdapterStartupError`.
- Do not move selectors, URLs, or business flow into `automation_core`.
- Capture screenshots, page source, UI trees, traces, and logs as artifacts
  rather than embedding raw data in JSON reports.
- Keep default tests offline and deterministic.
