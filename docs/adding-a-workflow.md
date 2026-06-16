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

## Workflow Steps

Example workflows can use `WorkflowStep` helpers to keep simple action and
artifact sequences compact:

```python
from examples.workflows import WorkflowStep, run_workflow_steps


def run_smoke_workflow(session, url):
    return run_workflow_steps(
        session,
        [
            WorkflowStep.action("open", url=url),
            WorkflowStep.artifact("screenshot", "home.png"),
        ],
    )
```

`WorkflowStep` is an example-layer authoring helper. It is not a persisted DSL,
and it does not move URLs, selectors, package names, or business flow into
`automation_core`.

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

Machine-readable built-in example discovery:

```bash
automation-runner examples --json
automation-runner examples --dry-run --json
```

The JSON discovery output lists built-in examples only and does not load live
browser or device sessions.

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

Custom workflow factory run:

```bash
automation-runner run --workflow-factory my_package.workflow:create_workflow \
  --json \
  --param account=test-user \
  --param city=shanghai
```

Runner defaults can also come from environment variables:

```bash
AUTOMATION_RUNNER_JSON=true \
AUTOMATION_RUNNER_URL=https://example.test/damai \
automation-runner run damai-web-smoke
```

Custom workflow parameters can also come from config. Environment values use a
JSON object string:

```bash
AUTOMATION_RUNNER_JSON=true \
AUTOMATION_RUNNER_WORKFLOW_FACTORY=my_package.workflow:create_workflow \
AUTOMATION_RUNNER_PARAMETERS='{"account":"config-user","city":"beijing"}' \
automation-runner run
```

Repeated CLI `--param KEY=VALUE` flags override matching config parameter keys.

Supported runner environment keys are:

- `AUTOMATION_RUNNER_LIVE`
- `AUTOMATION_RUNNER_JSON`
- `AUTOMATION_RUNNER_WORKFLOW_FACTORY`
- `AUTOMATION_RUNNER_FACTORY`
- `AUTOMATION_RUNNER_URL`
- `AUTOMATION_RUNNER_APP_ID`
- `AUTOMATION_RUNNER_PARAMETERS`

CLI arguments take precedence over environment values.

Custom workflow factories may use either of these signatures:

```python
def create_workflow(session_factory):
    ...


def create_workflow(session_factory, context, options):
    ...
```

`context` carries runner metadata such as workflow name and live mode.
`options` carries runner inputs such as `url`, `app_id`, `emit_json`, and
`report_file`. Custom workflows can also read repeated `--param KEY=VALUE`
inputs from `options.parameters`. Parameter values stay as strings; workflow
packages own their own parsing, required-field checks, and secret handling.

Built-in Damai examples still use `--url` or `--app-id`; custom workflows own
their own parameters outside `automation_core`.

Adapter sessions also expose a small common action vocabulary:

- Selenium: `open`, `click`, `type_text`
- Appium: `launch_app`, `tap`, `type_text`

These aliases stay in the adapter layer. Raw driver methods remain available
for framework-specific behavior.

For multi-step workflows, `automation_core.actions.ActionExecutor` can execute
an `ActionBatch` and returns an `ActionBatchResult`. The batch result separates
executed `results` from `skipped` actions when a `stop_on_failure` action fails.
This keeps workflow reports honest about which actions actually ran.

Built-in Damai smoke workflows use that batch path for their first action and
still return the flat `actions` list for compatibility. Their reports now carry
`action_batch` as the serialized batch summary, which makes dry-run and live-run
output line up with the same execution model. Runner reports omit raw action
result `data` and skipped action `parameters` from `action_batch`.

When `--json` is enabled, runner startup failures also emit a JSON report. In
that case the runner uses a fallback session identity with
`driver_name="unavailable"` and `platform="unknown"` so schedulers and scripts
still get a structured failure payload. Startup failure reports also include
`task.start`, `error`, and `task.end` events.

## Report Contract

JSON reports currently include:

- `schema_version`
- `workflow`
- `workflow_factory`
- `session_factory`
- `workflow_context`
- `success`
- `status`
- `run_id`
- `live`
- `elapsed_seconds`
- `events`
- `session`
- `actions`
- `action_batch`
- `artifacts`
- `error`

Each artifact entry contains:

- `artifact_type`
- `path`
- `metadata`

`schema_version` records the top-level runner JSON report contract version.
It is report metadata and does not version workflow result models or event
envelopes.

`events` contains serialized `EventEnvelope` records. Example workflows emit:

`workflow` records the workflow identifier that was executed. For built-in
examples it is the workflow name; for custom factory runs it is the custom
factory import path.

`workflow_factory` records the workflow factory import path when a custom
workflow factory is used. `session_factory` records the live session factory
import path when the runner is using a live adapter factory.

`workflow_context` is a safe summary of runner metadata. It mirrors the typed
context passed to custom factories and intentionally stays separate from raw
workflow options.

`WorkflowContext.to_dict()` is the report-safe serialization helper. The
runner does not serialize raw `WorkflowOptions` as a top-level report object.

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
  page source text, tokens, cookies, action `data`, or skipped action
  parameters.
- Artifact metadata should stay generic and small, such as source component,
  capture mode, or content kind.
- Report serialization redacts common sensitive metadata keys containing terms
  such as `token`, `secret`, `password`, `cookie`, or `authorization`.
- Dry workflows may return deterministic artifact paths without writing files.

## Adapter Rules

- Keep Selenium/Appium startup concerns in `adapters`.
- Surface startup failures as `AdapterStartupError`.
- Do not move selectors, URLs, or business flow into `automation_core`.
- Capture screenshots, page source, UI trees, traces, and logs as artifacts
  rather than embedding raw data in JSON reports.
- Keep default tests offline and deterministic.
