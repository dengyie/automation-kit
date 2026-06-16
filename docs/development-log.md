# Development Log

## 2026-06-16: Repository Bootstrap And Retry Core

### Completed

- Created `automation-kit` as a new sibling repository.
- Initialized Git and pushed to `github.com/dengyie/automation-kit`.
- Added Python package metadata and pytest coverage configuration.
- Added `automation_core` package skeleton.
- Added `automation_core.retries` with:
  - `RetryPolicy`
  - `RetryResult`
  - `retry_until`
- Enforced bounded retry behavior by requiring `max_attempts` or
  `max_duration`.
- Ensured retry helpers do not swallow `KeyboardInterrupt` or `SystemExit`.
- Added tests for import behavior and retry behavior.

### Verification

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
11 passed
Total coverage: 90.79%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `automation_core` has no Damai or Dianping business imports.
- retry behavior is bounded.
- retry implementation catches `Exception`, not `BaseException`.
- default tests require no browser, Appium, ADB, Android device, or network.

### Next Phase

Proceed to task lifecycle and structured events:

- `automation_core.tasks`
- `automation_core.events`
- tests for lifecycle transitions and serializable event payloads

## 2026-06-16: Task Lifecycle And Structured Events

### Completed

- Added `automation_core.tasks` with:
  - `TaskState`
  - `TaskLifecycle`
  - `TaskTransitionError`
- Added validation for invalid initial and next task states.
- Added `automation_core.events` with:
  - stable `EventType` values
  - `EventEnvelope`
  - task start/end events
  - retry attempt events
  - error events
  - artifact events
- Added `to_envelope()` conversion for structured event payloads.
- Added `automation_core.state` with:
  - `RunStatus`
  - `RunState`
- Added unit tests for task lifecycle transitions, event serialization, event
  type stability, and run state defaults.

### Verification

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
28 passed
Total coverage: 95.91%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `automation_core` and tests have no Damai or Dianping business coupling.
- `automation_core` and tests have no Selenium/Appium/WebDriver dependency.
- event types are stable and serialized through envelopes.
- task lifecycle rejects invalid transitions and invalid state inputs.

### Next Phase

Proceed to driver contracts and artifacts:

- `automation_core.drivers`
- `automation_core.artifacts`
- tests proving driver contracts do not import concrete browser/mobile drivers

## 2026-06-16: Driver Contracts And Artifacts

### Completed

- Added `automation_core.drivers` with:
  - `SessionInfo`
  - `ActionResult`
  - `ArtifactHandle`
  - `DriverSession`
  - `DriverSessionFactory`
- Added runtime-checkable protocol contracts for future browser and Android
  adapters.
- Added `automation_core.artifacts` with:
  - `ArtifactRecord`
  - `ArtifactStore`
- Added namespaced artifact path building by run ID and artifact type.
- Added artifact name normalization and rejection of invalid names such as
  `..`.
- Added metadata dictionary and stable JSON serialization for artifacts.
- Added tests for driver protocol compatibility and artifact store behavior.

### Verification

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
38 passed
Total coverage: 94.74%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `automation_core.drivers` imports no Selenium, Appium, WebDriver, browser, or
  Android libraries.
- driver contracts are pure standard-library protocols and data classes.
- artifact paths are namespaced by run ID and artifact type.
- artifact names reject invalid traversal-like values.
- default tests require no browser, Appium, ADB, Android device, or network.

### Next Phase

Proceed to thin adapter and example shells:

- `adapters/selenium`
- `adapters/appium`
- `examples/damai_web`
- `examples/damai_android`

## 2026-06-16: Thin Adapter And Example Shells

### Completed

- Added adapter shell packages:
  - `adapters`
  - `adapters.selenium`
  - `adapters.appium`
- Added example shell packages:
  - `examples`
  - `examples.damai_web`
  - `examples.damai_android`
- Added README boundary docs for:
  - `examples/damai_web`
  - `examples/damai_android`
- Added structure tests proving:
  - `automation_core` contains no business or concrete driver terms.
  - example README files exist.
  - adapter and example shell packages import successfully.

### Verification

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
41 passed
Total coverage: 94.74%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- Phase 4 added only adapter/example shells and boundary docs.
- No business workflow was migrated into `automation_core`.
- No concrete browser/mobile driver dependency was added to `automation_core`.
- The shell packages can be imported by default tests.

### Next Phase

The roadmap-defined basic usable state is now reached. The next development
step should create the first real adapter implementation behind the existing
driver contracts, starting with either a Selenium browser adapter or an Appium
Android adapter.

## 2026-06-16: Selenium Adapter

### Completed

- Added `adapters.selenium.SeleniumSession`.
- Added `adapters.selenium.SeleniumSessionFactory`.
- Kept Selenium as an optional adapter dependency by injecting a driver factory
  instead of importing Selenium in default code paths.
- Implemented driver lifecycle methods:
  - `start()`
  - `stop()`
  - `execute_action()`
  - `capture_artifact()`
- Reused `ArtifactStore` for screenshot artifact paths so adapter artifacts use
  the same path sanitization and namespacing rules as core artifacts.
- Added fake-driver tests so default verification does not require a real
  browser or Selenium package.

### Verification

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
48 passed
Total coverage: 94.74%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Review follow-up found and fixed one issue:

- `SeleniumSession.capture_artifact()` initially built paths directly. It now
  delegates to `ArtifactStore`, preserving artifact path sanitization and
  invalid-name rejection.

Follow-up inspection confirmed:

- `automation_core` still has no Selenium/Appium/WebDriver dependency.
- Selenium-specific code is confined to `adapters.selenium`.
- default tests still require no browser, Appium, ADB, Android device, or
  network.

### Next Phase

Proceed to the Appium adapter with the same constraints:

- optional dependency through injected factories,
- no live device in default tests,
- artifacts routed through `ArtifactStore`,
- no business workflow in the adapter.

## 2026-06-16: Appium Adapter

### Completed

- Added `adapters.appium.AppiumSession`.
- Added `adapters.appium.AppiumSessionFactory`.
- Kept Appium optional by injecting a driver factory instead of importing
  Appium in default code paths.
- Implemented driver lifecycle methods:
  - `start()`
  - `stop()`
  - `execute_action()`
  - `capture_artifact()`
- Routed adapter artifacts through `ArtifactStore` for the same sanitization
  and namespacing rules used by core artifacts.
- Added fake-driver tests for supported driver actions, `mobile:*` script
  execution, screenshot capture, page source capture, invalid artifact names,
  shutdown, and factory creation.
- Added test-package `__init__.py` files under `tests/adapters` so Selenium and
  Appium test modules can coexist without pytest import-name collisions.
- Expanded Poetry packaging to include `adapters`, so installed distributions
  ship the new adapter modules instead of only `automation_core`.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
57 passed
Total coverage: 94.74%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection found and fixed two issues:

- `tests/adapters/appium/test_session.py` and
  `tests/adapters/selenium/test_session.py` collided because pytest imported
  them as the same top-level module name. Added package markers under
  `tests/adapters` to isolate the modules.
- `pyproject.toml` initially packaged only `automation_core`, which would have
  omitted adapter modules from installed distributions. Added `adapters` to
  the Poetry package list.

Follow-up inspection confirmed:

- `automation_core` remains business-agnostic.
- Appium-specific code stays confined to `adapters.appium`.
- Default tests still require no browser, Appium, ADB, Android device, or
  network.

### Next Phase

Proceed to a first usable example workflow layer and any thin platform-specific
entrypoints, keeping business rules outside `automation_core`.

## 2026-06-16: Example Smoke Workflows

### Completed

- Added shared `ExampleWorkflowResult` for example-layer workflow output.
- Added `examples.damai_web.run_smoke_workflow(session, url)`.
- Added `examples.damai_android.run_smoke_workflow(session, app_id)`.
- Kept both workflows thin:
  - session is injected,
  - driver actions go through `DriverSession`,
  - artifacts go through the session contract,
  - `stop()` runs in `finally`.
- Added fake-session tests for web and Android smoke workflows, including
  session cleanup when driver actions fail.
- Updated example README files to describe smoke workflow scope.
- Expanded Poetry packaging to include `examples`, so installed distributions
  ship the documented example entrypoints.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
61 passed
Total coverage: 94.74%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- smoke workflows live under `examples`, not `automation_core`.
- `automation_core` remains business-agnostic and driver-agnostic.
- default tests still require no browser, Appium, ADB, Android device, or
  network.

### Next Phase

Proceed to a minimal CLI or Python runner facade that can execute example
workflows from injected factories without making live-system access the default.

## 2026-06-16: Minimal Runner Facade

### Completed

- Added `automation_runner.WorkflowRunner`.
- Runner accepts either a callable session factory or a `DriverSessionFactory`
  protocol object with `.create()`.
- Added `automation_runner.cli.main` with an `examples --dry-run` command that
  only lists example workflows and a dry-run notice.
- Added `automation_runner.__main__` so the package can be executed with
  `python -m automation_runner`.
- Registered an `automation-runner` Poetry script.
- Added tests for:
  - lazy session creation,
  - `DriverSessionFactory` compatibility,
  - CLI dry-run output,
  - Poetry script registration,
  - module entrypoint execution.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
66 passed
Total coverage: 92.57%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- runner behavior lives outside `automation_core`.
- the CLI defaults to dry-run listing, not live browser or device execution.
- the runner works with existing `DriverSessionFactory` adapters and lazy
  callables.

### Next Phase

Proceed to a thin command-line pathway for wiring real example factories into
the runner, if needed, while keeping live execution opt-in.

## 2026-06-16: Live CLI Wiring

### Completed

- Added `automation-runner run <workflow>` for example smoke workflows.
- Kept live execution explicitly opt-in with `--live`.
- Required `--factory module:object` before any live session factory is loaded.
- Added import-path loading for session factories.
- Wired CLI execution through `WorkflowRunner`.
- Added workflow-specific parameters:
  - `--url` for `damai-web-smoke`
  - `--app-id` for `damai-android-smoke`
- Preserved the existing `examples --dry-run` listing behavior.
- Added tests proving:
  - live execution is refused without `--live`,
  - live execution requires `--factory`,
  - workflow-specific parameters are validated before factory loading,
  - web and Android smoke workflows can run through imported fake factories.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
73 passed
Total coverage: 92.77%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- live execution requires an explicit `--live` flag.
- missing workflow-specific parameters fail before importing the factory.
- imported factories are only used by the runner layer, not `automation_core`.
- default tests still require no browser, Appium, ADB, Android device, or
  network.

### Next Phase

Proceed to structured runner output or run reports so command-line execution can
emit machine-readable results and artifact references.

## 2026-06-16: Structured Runner Output

### Completed

- Added `automation_runner.reports.RunnerReport`.
- Added `automation_runner.reports.build_report()` to serialize safe workflow
  summaries.
- Added `automation-runner run ... --json` for machine-readable output.
- Kept the default human-readable summary unchanged when `--json` is absent.
- Preserved the live execution guard rails:
  - `--live` required,
  - `--factory` required,
  - workflow-specific args validated before factory import.
- Added tests covering:
  - JSON output shape,
  - report serialization without leaking raw action data,
  - runner report helper behavior.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
75 passed
Total coverage: 93.12%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- JSON output stays in the runner layer, not `automation_core`.
- default behavior remains non-live unless explicitly opted in.
- structured output only includes summary fields and artifact paths, not raw
  action payloads.

### Next Phase

Proceed to any final runner/report polish only if it serves command-line
automation use cases; otherwise move on to the next roadmap phase.

## 2026-06-16: Runner Report File Output

### Completed

- Added `automation-runner run ... --report-file <path>`.
- Required `--json` when `--report-file` is used so saved reports always match
  the structured output contract.
- Wrote the same JSON payload to stdout and the report file.
- Created report parent directories automatically.
- Added tests covering:
  - report file writing,
  - parent directory creation,
  - rejecting `--report-file` without `--json`.

### Verification

Command:

```bash
./.venv/bin/python -m pytest -q
```

Result:

```text
78 passed
Total coverage: 93.37%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Review follow-up found and fixed one issue:

- `--report-file nested/report.json` initially failed when parent directories
  did not exist. The CLI now creates parent directories before writing.

Follow-up inspection confirmed:

- report file output remains in the runner layer.
- saved reports use the same payload as `--json` stdout.
- default and non-live behavior remain unchanged.

### Next Phase

Move to the next roadmap phase: configuration contracts or opt-in integration
fixtures, while keeping live browser/device access outside default tests.

## 2026-06-16: Generic Config Sources

### Completed

- Added `automation_core.config` with:
  - `ConfigError`
  - `ConfigSource`
  - `ConfigValue`
  - `DictConfigSource`
  - `EnvConfigSource`
- Added `EnvConfigSource` to read logical config keys from prefixed environment
  mappings or plain dictionaries.
- Preserved logical keys in returned `ConfigValue` objects while resolving
  prefix-based environment names.
- Copied config input mappings on construction so later external mutations do
  not affect source behavior.
- Reused the existing type validation path for dictionary and environment
  values.
- Added tests for:
  - typed config values,
  - dictionary required/default values,
  - environment required/default values,
  - prefixed and unprefixed environment lookup,
  - wrong-type rejection,
  - immutable input mappings.
- Added the basic usable skeleton implementation plan under
  `docs/superpowers/plans/`.

### Verification

Focused config tests:

```bash
.venv/bin/python -m pytest tests/config --no-cov -q
```

Result:

```text
14 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
92 passed
Total coverage: 93.62%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- config sources remain standard-library only.
- `automation_core.config` has no Damai, Dianping, Selenium, Appium, browser,
  Android, ticketing, order, or review coupling.
- env config values reuse the same type validation contract as dictionary
  config values.
- default tests require no browser, Appium, ADB, Android device, or network.

Review follow-up improved test coverage by adding explicit cases for:

- unprefixed environment lookup,
- wrong-type environment value rejection.

### Next Phase

Proceed to stabilize the runner contract and workflow authoring API:

- invalid factory string handling,
- missing factory object handling,
- stable JSON/report output,
- dry workflow authoring documentation.

## 2026-06-16: Runner Factory Error Handling

### Completed

- Wrapped runner factory import/lookup failures in a user-facing CLI error.
- Kept workflow-parameter validation ahead of factory loading so missing
  `--url` or `--app-id` still reports the correct argument error.
- Added tests for:
  - invalid `module:object` import paths,
  - missing factory objects on an importable module.

### Verification

Focused runner CLI tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Result:

```text
15 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
94 passed
Total coverage: 94.20%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the CLI still validates workflow-specific required arguments before factory
  loading,
- invalid factory paths now fail with a readable error instead of an unhandled
  exception,
- this behavior stays in the runner layer and does not leak into
  `automation_core`.

### Next Phase

Proceed to the workflow authoring API and its documentation.

## 2026-06-16: Example Workflow Authoring API

### Completed

- Added `examples.workflows.ExampleWorkflow` as a minimal runnable workflow
  object.
- Added `create_workflow(session_factory, url)` for Damai web examples.
- Added `create_workflow(session_factory, app_id)` for Damai Android examples.
- Kept the existing `run_smoke_workflow(...)` functions unchanged so direct
  functional invocation still works.
- Exported the new workflow factories from the example package `__init__.py`
  files.
- Updated README files to document:
  - the example workflow shape,
  - the runner dry-run command,
  - the authoring API for web and Android examples.
- Added tests proving:
  - the workflow factories return runnable objects,
  - the factories import cleanly without live browser/device dependencies,
  - the previous smoke workflow behavior still works.

### Verification

Example and import tests:

```bash
.venv/bin/python -m pytest tests/examples tests/test_imports.py --no-cov -q
```

Result:

```text
8 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
97 passed
Total coverage: 94.20%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the new workflow authoring API stays outside `automation_core`,
- example modules still keep Damai-specific concerns out of the core,
- direct run helpers remain available for tests and other local callers,
- default tests stay offline and deterministic.

The authoring object type was tightened from an unstructured object to
`DriverSession`-typed callables to keep the API boundary explicit.

### Next Phase

Proceed to any remaining runner/report polish or adapter shell work needed to
keep the repo aligned with the development plan.

## 2026-06-16: Adapter Startup Error Boundaries

### Completed

- Added `adapters.AdapterStartupError` as a shared adapter-layer startup error.
- Wrapped Selenium driver factory construction failures in
  `SeleniumSessionFactory.create()`.
- Wrapped Appium driver factory construction failures in
  `AppiumSessionFactory.create()`.
- Kept the adapter session implementations unchanged after construction so
  runtime driver behavior is still owned by the concrete session classes.
- Added tests proving:
  - adapter factories still create sessions normally,
  - driver factory failures surface as `AdapterStartupError`,
  - default tests do not need Selenium or Appium installed.

### Verification

Adapter tests:

```bash
.venv/bin/python -m pytest tests/adapters --no-cov -q
```

Result:

```text
18 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
99 passed
Total coverage: 94.20%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the new error stays in the adapter layer and does not leak into
  `automation_core`,
- factory startup failures now return a readable, testable adapter error,
- the try/except scope is limited to session creation and does not mask runtime
  action failures inside the session objects.

### Next Phase

Proceed to any remaining runner/report or adapter polish only if it advances
the documented basic usable state.

## 2026-06-16: Runner Report Metadata And Workflow Docs

### Completed

- Expanded `RunnerReport` with:
  - `workflow_factory`
  - `status`
  - `run_id`
  - `live`
  - `elapsed_seconds`
  - `events`
  - `error`
- Kept action serialization safe by continuing to omit raw action `data`.
- Passed the CLI factory import path and elapsed run time into JSON reports.
- Added report tests for:
  - live flag serialization,
  - non-live defaults,
  - failed status,
  - factory path,
  - elapsed seconds,
  - error summary field.
- Added `docs/adding-a-workflow.md` with:
  - package boundaries,
  - workflow factory shape,
  - dry-run and live-run commands,
  - report fields,
  - adapter rules.
- Linked the workflow guide from `README.md`.

### Verification

Runner tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
21 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
101 passed
Total coverage: 94.34%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`.

Follow-up inspection confirmed:

- report changes stay in `automation_runner`,
- raw action data remains excluded from reports,
- the workflow guide explicitly keeps business logic out of `automation_core`,
- default tests still require no browser, Appium, ADB, Android device, or
  network.

### Next Phase

Proceed to final verification against the basic usable skeleton plan.

## 2026-06-16: Runner Failure Reports

### Completed

- Switched `automation_runner.cli` to run example workflow objects created by
  `create_workflow(...)` instead of calling the smoke helpers directly.
- Added `ExampleWorkflowResult.error` for structured failure summaries.
- Made `ExampleWorkflow.run()` convert workflow exceptions into failed results
  while still allowing non-`Exception` interruptions to propagate.
- Made JSON/report-file output include failed workflow reports with:
  - `success: false`
  - `status: failed`
  - `run_id`
  - `workflow_factory`
  - `error`
- Returned exit code `1` for failed workflow results.
- Added tests proving:
  - example workflow objects return failed results when actions fail,
  - CLI emits and writes JSON failure reports,
  - failed workflow sessions still stop through the smoke workflow `finally`
    blocks.

### Verification

Focused examples and runner tests:

```bash
.venv/bin/python -m pytest tests/examples tests/runner --no-cov -q
```

Result:

```text
30 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
104 passed
Total coverage: 94.36%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- failure-report behavior stays in examples and `automation_runner`, not
  `automation_core`,
- raw action data remains excluded from reports,
- workflow failures now produce machine-readable diagnostics,
- default tests remain offline and deterministic.

### Next Phase

Proceed to final basic-usable-state verification and identify the next
development roadmap slice.

## 2026-06-16: Basic Dry Workflow Execution

### Completed

- Added `automation_runner.dry_run.DryRunSession` for offline workflow runs.
- Allowed `automation-runner run` to execute without `--live` using the dry-run
  session and the same example workflow composition path.
- Kept live runs on the explicit `--live` path with `--factory` still required.
- Preserved dry-run report output as JSON with:
  - `live: false`
  - synthetic dry-run session metadata
  - workflow actions and artifact paths
- Added tests proving:
  - dry-run execution works without a live factory,
  - dry-run ignores invalid factory import paths,
  - live execution remains explicit and unchanged.
- Updated README and workflow guide examples to show the dry-run command.

### Verification

Runner tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
23 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
105 passed
Total coverage: 94.61%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the dry-run path stays in the runner layer,
- live factory loading still only happens on explicit live runs,
- default tests remain offline and deterministic,
- workflow reports stay machine-readable.

### Next Phase

Proceed to the next development slice after validating whether additional
report/event polish is required.

## 2026-06-16: Structured Workflow Events In Reports

### Completed

- Added stable workflow names to the Damai web and Android example workflow
  factories.
- Made `ExampleWorkflow.run()` preserve workflow-provided events and emit
  structured events for:
  - workflow start,
  - captured artifacts,
  - workflow exceptions,
  - workflow completion outcome.
- Made `RunnerReport.events` serialize workflow event envelopes instead of
  always returning an empty list.
- Added report and CLI tests proving successful and failed runs include the
  expected event sequence and payloads.
- Updated the workflow guide to document report event semantics.

### Verification

Focused examples and runner tests:

```bash
.venv/bin/python -m pytest tests/examples tests/runner -q
```

Result:

```text
32 passed
Coverage failure: total of 48.92 is less than fail-under=80.00
```

The focused tests passed; the coverage failure is expected when running only
this subset without disabling the repository-wide coverage threshold.

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
107 passed
Total coverage: 94.61%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- report event serialization stays in `automation_runner`,
- event creation uses generic `automation_core.events` primitives,
- workflow-provided events are preserved,
- failure reports include an `error` event and failed `task.end` outcome,
- default tests remain offline and deterministic.

### Next Phase

Commit and push the event-report slice, then continue with the next basic
usable skeleton phase.

## 2026-06-16: Basic Usable Skeleton Verification

### Completed

- Audited the basic usable skeleton plan against the current repository.
- Updated the plan status to reflect that the earlier phases are now
  implemented and verified.
- Tightened the CLI report-file contract so `--report-file` writes the exact
  JSON line emitted to stdout, including the trailing newline.
- Added tests covering byte-for-byte report-file/stdout parity for success and
  failure JSON reports.
- Re-ran the documented dry workflow and report-file commands.

### Verification

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
107 passed
Total coverage: 94.61%
Required coverage: 80%
```

Boundary test without coverage threshold:

```bash
.venv/bin/python -m pytest tests/structure/test_boundaries.py --no-cov -q
```

Result:

```text
3 passed
```

Dry workflow listing:

```bash
.venv/bin/python -m automation_runner examples --dry-run
```

Result:

```text
damai-android-smoke
damai-web-smoke
dry-run: no live browser, Appium, ADB, or device session started
```

Dry workflow JSON run:

```bash
.venv/bin/python -m automation_runner run damai-web-smoke --json \
  --url https://example.test/damai
```

Result:

```text
success=true, live=false, status=succeeded, workflow=damai-web-smoke
```

Report-file parity:

```bash
.venv/bin/python -m automation_runner run damai-web-smoke --json \
  --report-file /tmp/automation-kit-report-check.json \
  --url https://example.test/damai \
  >/tmp/automation-kit-report-check.stdout
cmp -s /tmp/automation-kit-report-check.json \
  /tmp/automation-kit-report-check.stdout
```

Result:

```text
ok
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- report-file newline handling is confined to `automation_runner.cli`,
- success and failure report-file parity are covered by runner tests,
- the basic usable skeleton plan no longer contains stale implementation
  status,
- default tests remain offline and deterministic.

The helper's suggested `python3 -m unittest discover` is not the authoritative
test command for this pytest/Poetry project; the project verification command
is `.venv/bin/python -m pytest -q`.

### Next Phase

Commit and push the skeleton verification slice, then start the next roadmap
slice on top of the verified baseline.

## 2026-06-16: Artifact Guide And Snapshot Support

### Completed

- Added `docs/artifacts.md` to define artifact storage layout, naming rules,
  report attachment rules, adapter responsibilities, and dry-run behavior.
- Linked the artifact guide from `README.md` and `docs/adding-a-workflow.md`.
- Clarified that screenshots, page source, UI trees, traces, and logs belong
  in artifact storage rather than in JSON reports.
- Added Selenium adapter support for `page_source` and `ui_tree` text
  artifacts when the driver exposes `page_source`.
- Added Appium adapter support for `ui_tree` text artifacts alongside existing
  screenshot and page-source support.
- Added a namespace regression test for artifact paths to preserve
  `<run-id>/<artifact-type>/<artifact-name>` structure.

### Verification

Adapter and artifact tests:

```bash
.venv/bin/python -m pytest tests/adapters tests/artifacts --no-cov -q
```

Result:

```text
25 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
111 passed
Total coverage: 94.61%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- artifact conventions are documented outside `automation_core`,
- report guidance continues to exclude raw artifact bytes and action `data`,
- the new path test fixes the run/type/name namespace convention,
- default tests remain offline and deterministic.

### Next Phase

Commit and push the artifact-guidance slice, then continue with the next
roadmap slice.

## 2026-06-16: Workflow Extension Documentation Closure

### Completed

- Expanded `docs/adding-a-workflow.md` with concrete steps for creating a new
  workflow package outside `automation_core`.
- Documented artifact and report attachment conventions directly in the
  workflow guide.
- Updated the basic usable skeleton plan status to point at `docs/artifacts.md`
  for screenshots, page dumps, UI dumps, traces, logs, and JSON reports.
- Removed duplicate Selenium screenshot wording from `docs/artifacts.md`.

### Verification

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
111 passed
Total coverage: 94.61%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- workflow extension steps keep business code outside `automation_core`,
- artifact/report attachment guidance matches the current report contract,
- JSON reports continue to exclude raw artifact bytes, tokens, cookies, and
  action `data`,
- default tests remain offline and deterministic.

### Next Phase

Commit and push this documentation-closure slice, then continue with the next
roadmap slice.

## 2026-06-16: Generic Action Primitives

### Completed

- Added `automation_core.actions` with:
  - `ActionRequest`
  - `ActionBatch`
  - `ActionExecutor`
- Kept actions business-agnostic and driver-backed through the existing
  `DriverSession.execute_action(...)` contract.
- Added stable dictionary serialization for action requests and batches.
- Added batch execution with `stop_on_failure` defaulting to fail-fast and an
  opt-out for continuing after failed actions.
- Added import coverage for the new core actions package.
- Updated README runtime primitive list to include action requests and batches.

### Verification

Focused action tests:

```bash
.venv/bin/python -m pytest tests/actions tests/test_imports.py --no-cov -q
```

Result:

```text
9 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
118 passed
Total coverage: 94.94%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- action primitives stay business-agnostic in `automation_core`,
- `ActionExecutor` is only a thin bridge over `DriverSession.execute_action`,
- batch fail-fast behavior is explicit and covered by tests,
- default tests remain offline and deterministic.

### Next Phase

Commit and push the action-primitives slice, then continue with the next
roadmap slice.

## 2026-06-16: Element Contract Primitives

### Completed

- Added `automation_core.drivers.ElementHandle` as a runtime-checkable
  protocol for UI element interactions.
- Added `automation_core.drivers.ElementLookupSession` to model driver
  sessions that can resolve elements by selector.
- Kept the new element contracts business-agnostic and separate from concrete
  Selenium/Appium adapter behavior.
- Added tests proving fake element and lookup sessions satisfy the new
  contracts.
- Extended import coverage so the new contracts are part of the package API.

### Verification

Focused driver/import/boundary tests:

```bash
.venv/bin/python -m pytest tests/drivers tests/test_imports.py tests/structure/test_boundaries.py --no-cov -q
```

Result:

```text
17 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
122 passed
Total coverage: 94.27%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the new element contracts stay in `automation_core.drivers`,
- runtime-checkable protocols keep the boundary explicit without coupling to
  concrete Selenium/Appium implementations,
- tests cover both the new protocol shapes and the import surface,
- default tests remain offline and deterministic.

### Next Phase

Commit and push the element-contract slice, then continue with the next
roadmap slice.

## 2026-06-16: Deterministic Task Runner

### Completed

- Added `automation_core.tasks.TaskRunner` for deterministic callable task
  execution.
- Added `automation_core.tasks.TaskResult` with:
  - task ID,
  - task name,
  - success flag,
  - returned value,
  - error summary,
  - structured event envelopes.
- Wired task execution to existing lifecycle and event primitives:
  - `task.start`,
  - `error`,
  - `task.end`.
- Kept interruption behavior safe by not swallowing `KeyboardInterrupt`.
- Added task runner import coverage and focused unit tests for success,
  failure, and interruption behavior.
- Updated README runtime primitive list to include the deterministic task
  runner.

### Verification

Focused task tests:

```bash
.venv/bin/python -m pytest tests/tasks tests/test_imports.py --no-cov -q
```

Result:

```text
15 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
126 passed
Total coverage: 94.54%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- task runner behavior stays in `automation_core.tasks`,
- task execution emits structured events without depending on adapters or
  business workflows,
- task failures return machine-readable results while `KeyboardInterrupt`
  still propagates,
- default tests remain offline and deterministic.

### Next Phase

Commit and push the task-runner slice, then continue with the next roadmap
slice.

## 2026-06-16: Run State Transitions

### Completed

- Added lifecycle helpers to `automation_core.state.RunState`:
  - `start()`,
  - `succeed()`,
  - `fail()`,
  - `cancel()`.
- `start()` now refreshes `started_at` when a run enters the running state.
- Terminal helpers now set `finished_at` and default outcomes.
- Added tests for running, successful, failed, and cancelled run states.
- Added import coverage for `RunState` and `RunStatus`.
- Updated README runtime primitive list to include run state.

### Verification

Focused state tests:

```bash
.venv/bin/python -m pytest tests/state tests/test_imports.py --no-cov -q
```

Result:

```text
10 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
129 passed
Total coverage: 94.68%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- run state transitions stay inside `automation_core.state`.
- `start()` refreshes `started_at` when execution begins.
- terminal helpers set `finished_at` and default outcomes.
- tests cover running, succeeded, failed, cancelled, and import behavior.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the run-state slice, then continue with the next roadmap
slice.

## 2026-06-16: Run State Report Integration

### Completed

- Connected `automation_core.state.RunState` into the CLI runner flow.
- CLI now records run lifecycle timestamps and terminal outcomes during
  execution.
- Runner reports now include a structured `run_state` payload alongside the
  existing status summary.
- Added tests covering serialized run state in reports and CLI JSON output for
  success and failure paths.

### Verification

Focused state and runner tests:

```bash
.venv/bin/python -m pytest tests/state tests/runner --no-cov -q
```

Result:

```text
29 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
130 passed
Total coverage: 94.89%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `RunState` remains in `automation_core.state` and stays business-agnostic.
- runner reports serialize a terminal `run_state` instead of a stale pending
  state.
- top-level `run_id` and `run_state.run_id` both use the session run
  identifier.
- elapsed duration still uses `time.monotonic()` while run lifecycle
  timestamps use wall-clock time.
- success and failure JSON paths both cover `run_state` output.

### Next Phase

Commit and push the report integration slice, then continue with the next
roadmap slice.

## 2026-06-16: Artifact Metadata In Reports

### Completed

- Added generic metadata support to `automation_core.drivers.ArtifactHandle`.
- Runner reports now serialize artifact metadata together with artifact type
  and path.
- Report serialization redacts common sensitive artifact metadata keys.
- Selenium and Appium adapter sessions pass artifact-record metadata through
  returned artifact handles.
- Updated workflow documentation to include the artifact metadata report
  contract.
- Added tests for artifact-handle metadata, report serialization, sensitive
  metadata redaction, and CLI JSON artifact output.

### Verification

Focused driver, runner, adapter, and artifact tests:

```bash
.venv/bin/python -m pytest tests/drivers tests/runner tests/adapters tests/artifacts --no-cov -q
```

Result:

```text
61 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
132 passed
Total coverage: 95.02%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- artifact metadata remains a generic `Dict[str, str]` on the driver contract.
- report serialization redacts common sensitive metadata keys before JSON
  output.
- report serialization still omits action `data`.
- Selenium and Appium adapters only pass through generic artifact-record
  metadata.
- `automation_core` remains business-agnostic and structure tests pass.

### Next Phase

Commit and push the artifact metadata slice, then continue with the next
roadmap slice.

## 2026-06-16: Runner Environment Configuration

### Completed

- Added `automation_runner.config.RunnerConfig`.
- Added runner config loading from generic `ConfigSource` values.
- CLI `run` can now read defaults from `AUTOMATION_RUNNER_*` environment
  variables.
- CLI arguments take precedence over configured defaults.
- Config validation is limited to the `run` command so `examples --dry-run`
  remains independent of run-specific environment values.
- Updated README and workflow docs with supported runner environment keys.
- Added tests for config defaults, live/dry runs from config, argument
  precedence, report-file output, and invalid boolean values.

### Verification

Focused runner and config tests:

```bash
.venv/bin/python -m pytest tests/runner tests/config --no-cov -q
```

Result:

```text
50 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
142 passed
Total coverage: 95.10%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- runner environment configuration stays in `automation_runner`, not
  `automation_core`.
- live execution still requires an explicit live setting and a session factory.
- CLI arguments take precedence over configured defaults.
- `examples --dry-run` does not validate or depend on run-specific
  configuration.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the runner environment configuration slice, then continue with
the next roadmap slice.

## 2026-06-16: Custom Workflow Factory Loading

### Completed

- Added `--workflow-factory module:object` support to `automation-runner run`.
- Added `AUTOMATION_RUNNER_WORKFLOW_FACTORY` config support.
- Custom workflow factories receive the same injected `session_factory` as
  built-in workflows.
- Built-in Damai smoke workflows keep their existing `--url` and `--app-id`
  behavior.
- Updated README and workflow docs with custom workflow factory commands.
- Added tests for custom workflow factory dry runs, config-sourced workflow
  factories, missing factory errors, and required workflow selection.

### Verification

Focused runner tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
40 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
146 passed
Total coverage: 95.30%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- custom workflow loading stays in `automation_runner` and does not add
  business logic to `automation_core`.
- live execution still requires the explicit live path and a session factory.
- built-in Damai workflow parameter validation remains unchanged.
- custom workflow factories receive only the injected `session_factory`.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the custom workflow factory slice, then continue with the next
roadmap slice.

## 2026-06-16: Runner Report Factory Field Split

### Completed

- Split runner report factory metadata into:
  - `workflow_factory` for custom workflow factory import paths.
  - `session_factory` for live session factory import paths.
- Kept built-in Damai workflow behavior unchanged.
- Updated CLI report construction to preserve both fields independently.
- Updated runner tests to assert the distinct report contract for dry, live,
  success, and failure paths.
- Updated workflow docs to describe the two factory fields separately.

### Verification

Focused runner tests:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Result:

```text
40 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
146 passed
Total coverage: 95.30%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `workflow_factory` and `session_factory` now have distinct meanings.
- live execution still requires an explicit live path and factory import.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the report metadata refinement slice, then continue with the
next roadmap slice.

## 2026-06-16: Workflow Context For Custom Factories

### Completed

- Added `automation_runner.context.WorkflowContext`.
- Added `automation_runner.context.WorkflowOptions`.
- Exported both context models from `automation_runner`.
- Added custom workflow factory support for:
  - legacy `create_workflow(session_factory)`.
  - typed `create_workflow(session_factory, context, options)`.
  - keyword-extensible `create_workflow(session_factory, **kwargs)`.
- Kept built-in Damai workflow signatures unchanged.
- Added design and implementation plan docs under `docs/superpowers/`.
- Updated README and workflow extension docs with supported custom factory
  signatures.
- Added tests for context model values and custom factory context/options
  delivery.

### Verification

Focused runner tests:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Result:

```text
44 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
150 passed
Total coverage: 94.97%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- workflow context and options stay in `automation_runner`, not
  `automation_core`.
- default tests remain offline and deterministic.
- existing one-argument custom workflow factories still work.
- keyword-extensible custom workflow factories receive context and options.
- report serialization still omits raw action `data`.

### Next Phase

Commit and push the workflow context slice, then continue with the next roadmap
slice.

## 2026-06-16: Workflow Context In Reports

### Completed

- Added `workflow_context` to runner JSON reports.
- Reused `automation_runner.context.WorkflowContext` as the report source.
- Kept top-level `workflow`, `workflow_factory`, `session_factory`, and
  `live` fields for compatibility.
- Avoided serializing raw `WorkflowOptions` values into reports.
- Updated README, workflow docs, design docs, and implementation plan docs.
- Added report tests for explicit workflow context serialization.

### Verification

Focused runner tests:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Result:

```text
45 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
151 passed
Total coverage: 94.99%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- report context serialization stays in `automation_runner`, not
  `automation_core`.
- reports still omit raw action `data`.
- raw workflow options are not serialized as a report object.
- existing top-level report fields remain present.

### Next Phase

Commit and push the workflow-context report slice, then continue with the next
roadmap slice.

## 2026-06-16: Context Serialization Helpers

### Completed

- Added `WorkflowContext.to_dict()`.
- Added `WorkflowOptions.to_dict()`.
- Updated runner report serialization to reuse `WorkflowContext.to_dict()`.
- Added design and implementation plan docs for context serialization.
- Updated workflow docs to describe report-safe context serialization.
- Added unit tests for both serialization helpers.

### Verification

Focused runner tests:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Result:

```text
47 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
153 passed
Total coverage: 95.02%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- context serialization stays in `automation_runner`.
- reports reuse the same `WorkflowContext` serialization contract.
- raw `WorkflowOptions` still are not added to JSON reports.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the context serialization slice, then continue with the next
roadmap slice.

## 2026-06-16: Adapter Action Aliases

### Completed

- Added adapter-layer action aliases for common workflow operations:
  - Selenium: `open`, `click`, `type_text`
  - Appium: `tap`, `type_text`
- Kept the aliases inside `adapters` so `automation_core` stays business
  agnostic.
- Preserved raw driver-method fallback behavior for framework-specific use
  cases.
- Added focused adapter tests for:
  - Selenium URL loading, element clicks, and text entry
  - Appium coordinate taps, element taps, and text entry
  - missing-parameter failures for the new aliases
- Updated workflow docs to describe the adapter action vocabulary.

### Verification

Focused adapter tests:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Result:

```text
16 passed
17 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
163 passed
Total coverage: 95.02%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- adapter aliases stay in `adapters`, not `automation_core`.
- the aliases add no Damai or Dianping business coupling.
- raw driver-method fallback behavior remains available.
- missing element-lookup support returns failed `ActionResult` values instead
  of uncaught adapter exceptions.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the adapter alias slice, then continue with the next roadmap
phase.

## 2026-06-16: Example Workflow Aliases

### Completed

- Switched the built-in web smoke workflow to use the `open` adapter alias.
- Added `launch_app` as an Appium adapter alias for starting an app by
  `app_id`.
- Switched the built-in Android smoke workflow to use `launch_app`.
- Kept raw driver-method fallback behavior available for framework-specific
  behavior.
- Updated example tests to expect the adapter alias vocabulary.
- Updated workflow docs to include `launch_app` in the adapter action
  vocabulary.

### Verification

Focused adapter and example tests:

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
.venv/bin/python -m pytest tests/examples --no-cov -q
```

Result:

```text
19 passed
9 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
167 passed
Total coverage: 95.02%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- example workflows use adapter aliases for the first-run web and Android
  paths.
- the new `launch_app` alias stays in `adapters.appium`, not
  `automation_core`.
- raw driver-method fallback behavior remains available.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the example alias slice, then continue with the next roadmap
phase.

## 2026-06-16: Action Batch Summary

### Completed

- Added `ActionBatchResult` to `automation_core.actions`.
- Updated `ActionExecutor.run_batch(...)` to return explicit batch summaries.
- Added `skipped` actions for stop-on-failure short-circuit behavior.
- Added `success` and `to_dict()` semantics for batch results.
- Exported `ActionBatchResult` from `automation_core.actions`.
- Updated workflow docs to describe batch summary behavior.

### Verification

Focused action tests:

```bash
.venv/bin/python -m pytest tests/actions/test_action_models.py --no-cov -q
```

Result:

```text
9 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
170 passed
Total coverage: 95.09%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- action batch summaries stay in `automation_core.actions` and are surfaced
  through runner reports only when workflows provide them.
- `action_batch` remains optional in reports and defaults to `None` when no batch summary is provided.
- default tests remain offline and deterministic.

### Next Phase

Commit and push the action batch reporting slice, then continue with the next roadmap
phase.

## 2026-06-16: Example Action Batches

### Completed

- Updated the Damai web smoke workflow to execute its `open` action through
  `ActionExecutor.run_batch(...)`.
- Updated the Damai Android smoke workflow to execute its `launch_app` action
  through `ActionExecutor.run_batch(...)`.
- Preserved the existing flat `actions` list while also returning
  `batch_result` from both example workflows.
- Documented the built-in smoke workflow batch path in
  `docs/adding-a-workflow.md`.

### Verification

Focused example and CLI tests:

```bash
.venv/bin/python -m pytest tests/examples tests/runner/test_cli.py --no-cov -q
```

Result:

```text
40 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
172 passed
Total coverage: 95.15%
Required coverage: 80%
```

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed the example workflows stay in the example layer
and the report contract remains backward compatible.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Examples JSON Discovery

### Completed

- Added `automation-runner examples --json`.
- Added `automation-runner examples --dry-run --json`.
- Kept existing plain text `examples --dry-run` behavior unchanged.
- Kept discovery limited to the built-in `WORKFLOWS` registry.
- Documented machine-readable built-in example discovery in `README.md` and
  `docs/adding-a-workflow.md`.

### Verification

Focused JSON discovery tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Result:

```text
2 passed, 35 deselected
```

Focused text compatibility tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'lists_example_workflows_without_live_execution or examples_does_not_validate_run_config' --no-cov -q
```

Result:

```text
2 passed, 35 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
185 passed
Total coverage: 94.86%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit` before commit.

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `examples --json` only lists the built-in `WORKFLOWS` registry.
- JSON discovery does not load live session factories.
- existing plain text examples output remains unchanged.
- no discovery behavior moved into `automation_core`.

### Next Phase

Commit and push the finished slice.

## 2026-06-16: Runner Config Workflow Parameters

### Completed

- Added `RunnerConfig.parameters` for config-sourced custom workflow inputs.
- Supported dictionary parameter values from config sources.
- Supported JSON object strings such as `AUTOMATION_RUNNER_PARAMETERS`.
- Validated that config parameter keys and values are strings.
- Merged CLI `--param` values over config parameters by key.
- Documented config-sourced workflow parameters in `README.md` and
  `docs/adding-a-workflow.md`.

### Verification

Focused runner config tests:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py --no-cov -q
```

Result:

```text
6 passed
```

Focused CLI config parameter tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'config_parameters' --no-cov -q
```

Result:

```text
2 passed, 33 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
183 passed
Total coverage: 94.81%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit` before commit.

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- config-sourced workflow parameters stay in `automation_runner`.
- `automation_core` remains free of runner parameter handling.
- invalid parameter config fails before live session factory loading.
- CLI `--param` values override matching config parameter keys while preserving
  other config keys.

### Next Phase

Commit and push the finished slice.

## 2026-06-16: Safe Action Batch Reporting

### Completed

- Changed runner `action_batch` report serialization to omit raw
  `ActionResult.data`.
- Changed runner `action_batch` skipped-action serialization to omit
  `ActionRequest.parameters`.
- Kept `automation_core.actions.ActionBatchResult.to_dict()` unchanged for core
  consumers.
- Documented that runner JSON reports exclude action `data` and skipped action
  parameters.

### Verification

Focused regression test:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_action_batch_summary --no-cov -q
```

Result:

```text
1 passed
```

Focused report and core action tests:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py tests/actions/test_action_models.py --no-cov -q
```

Result:

```text
17 passed
```

Focused runner/report/action tests:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py tests/runner/test_cli.py tests/actions/test_action_models.py --no-cov -q
```

Result:

```text
50 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
178 passed
Total coverage: 94.86%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit` before commit.

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- runner `action_batch` reports no longer include raw action result `data`.
- runner `action_batch` reports no longer include skipped action parameters.
- `automation_core.actions.ActionBatchResult.to_dict()` remains unchanged.
- documentation now states that skipped action parameters are excluded from
  JSON reports.

### Next Phase

Commit and push the finished slice.

## 2026-06-16: Runner Workflow Parameters

### Completed

- Added a repeated `--param KEY=VALUE` CLI input channel for custom workflow
  factories.
- Added `WorkflowOptions.parameters` as a business-agnostic string dictionary.
- Preserved values containing additional `=` characters.
- Rejected malformed parameters before live session factories are loaded.
- Documented custom workflow parameter usage in `README.md` and
  `docs/adding-a-workflow.md`.

### Verification

Focused context tests:

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Result:

```text
4 passed
```

Focused CLI parameter tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'context_and_options or rejects_invalid_workflow_param' --no-cov -q
```

Result:

```text
2 passed, 31 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
178 passed
Total coverage: 94.86%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit` before commit.

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `--param` parsing and validation happens before live session factory loading.
- malformed workflow parameters fail with a user-facing CLI error.
- `automation_core` remains untouched by runner parameter handling.
- raw `WorkflowOptions` are still not serialized as a top-level report object.

### Next Phase

Commit and push the finished slice.

## 2026-06-16: Runner Startup Failure Events

### Completed

- Added `task.start`, `error`, and `task.end` events to runner startup failure
  JSON reports.
- Reused existing `automation_core.events` event models instead of adding a
  second event shape.
- Covered live session factory startup failures and custom workflow factory
  construction failures.
- Documented startup failure event behavior in `docs/adding-a-workflow.md`.

### Verification

Focused startup failure regression tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'session_factory_fails or custom_workflow_factory_fails' --no-cov -q
```

Result:

```text
2 passed, 30 deselected
```

Focused runner CLI tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Result:

```text
32 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
177 passed
Total coverage: 94.72%
Required coverage: 80%
```

### Review

Used `production-code-quality-review` required setup scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- startup failure reports now include `task.start`, `error`, and `task.end`
  events.
- fallback event payloads use the same fallback run id as the report session.
- the change reuses existing `automation_core.events` models.
- normal `ExampleWorkflow.run()` event behavior is unchanged.

### Next Phase

Commit and push the finished slice.

## 2026-06-16: Workflow Steps

### Completed

- Added example-layer `WorkflowStep` helpers for ordered action and artifact
  composition.
- Added `run_workflow_steps(...)` to execute step sequences with shared
  session lifecycle handling.
- Moved the Damai web and Android smoke workflows onto the new step helper.
- Kept existing `ExampleWorkflow` result and event behavior intact.
- Documented workflow steps in `docs/adding-a-workflow.md`.

### Verification

Focused example and CLI tests:

```bash
.venv/bin/python -m pytest tests/examples tests/runner/test_cli.py --no-cov -q
```

Result:

```text
43 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
175 passed
Total coverage: 95.15%
Required coverage: 80%
```

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- workflow step composition stays in the example layer.
- `automation_core` remains business-agnostic.
- action failure short-circuits later steps and reports skipped actions.
- artifact-only sequences remain successful and do not emit empty
  `action_batch` summaries.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Runner Failure Reporting

### Completed

- Added structured JSON reports for runner execution failures before a workflow
  returns a normal result.
- Added startup-failure coverage for live session factories.
- Added workflow-construction failure coverage for custom workflow factories.
- Reused the existing runner report contract instead of adding a second error
  model.
- Documented startup failure reports in `docs/adding-a-workflow.md`.

### Verification

Focused runner CLI tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Result:

```text
32 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
177 passed
Total coverage: 94.71%
Required coverage: 80%
```

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- runner startup failures now emit a structured JSON report when `--json` is
  enabled.
- report file output stays aligned with stdout output on startup failure.
- the fallback session identity is only used when a real session never existed.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Runner Report Schema Version

### Completed

- Added top-level `schema_version` metadata to runner JSON reports.
- Kept schema versioning in `automation_runner.reports`.
- Left `automation_core`, workflow result models, and event envelopes unchanged.
- Added report unit coverage and CLI JSON coverage for the new field.
- Documented the report contract version in `docs/adding-a-workflow.md`.

### Verification

Focused red test run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_safe_workflow_summary tests/runner/test_cli.py::test_cli_runs_dry_workflow_without_live_flag --no-cov -q
```

Result:

```text
2 failed
KeyError: 'schema_version'
```

Focused green test run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_safe_workflow_summary tests/runner/test_cli.py::test_cli_runs_dry_workflow_without_live_flag --no-cov -q
```

Result:

```text
2 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
185 passed
Total coverage: 94.86%
Required coverage: 80%
```

Whitespace check:

```bash
git diff --check
```

Result: no output.

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- `schema_version` is additive runner report metadata.
- the field is emitted by both unit-level report serialization and CLI JSON.
- no business-specific data was moved into `automation_core`.
- workflow result models and event envelopes remain unversioned in this slice.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Runner Report JSON Schema

### Completed

- Added `docs/report-schema-v1.json` as the machine-readable runner report
  contract for `schema_version == "1"`.
- Added tests that compare the schema top-level fields with a real
  `build_report(...).to_dict()` payload.
- Added tests for safe nested report sections including `session`, `run_state`,
  `actions`, `artifacts`, and `action_batch`.
- Linked the schema from `README.md` and `docs/adding-a-workflow.md`.
- Kept the schema in `docs` with no runtime validation dependency.

### Verification

Focused red test run before adding the schema:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Result:

```text
2 failed
FileNotFoundError: docs/report-schema-v1.json
```

Focused green test run after adding the schema:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Result:

```text
2 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
187 passed
Total coverage: 94.86%
Required coverage: 80%
```

Whitespace check:

```bash
git diff --check
```

Result: no output.

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection confirmed:

- the schema is documentation and compatibility metadata only.
- report emission remains in `automation_runner.reports`.
- no JSON Schema runtime dependency was added.
- event payloads and artifact metadata remain extensible.
- raw action `data` and skipped action `parameters` remain excluded from the
  documented report contract.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Runner Report Schema CLI

### Completed

- Added `automation_runner.schemas.load_report_schema()` for packaged runner
  report schema discovery.
- Added `automation_runner/schemas/report-schema-v1.json` as a package
  resource that matches `docs/report-schema-v1.json`.
- Added `automation-runner report-schema --version 1` for CLI schema output.
- Added unsupported-version handling for `report-schema --version 2`.
- Added package configuration for including the schema resource in both sdist
  and wheel formats.
- Documented CLI schema discovery in `README.md` and
  `docs/adding-a-workflow.md`.

### Verification

Focused red test run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py tests/runner/test_cli.py::test_cli_prints_report_schema_v1 tests/runner/test_cli.py::test_cli_rejects_unknown_report_schema_version --no-cov -q
```

Result:

```text
1 error
ModuleNotFoundError: No module named 'automation_runner.schemas'
```

Focused green test run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py tests/runner/test_cli.py::test_cli_prints_report_schema_v1 tests/runner/test_cli.py::test_cli_rejects_unknown_report_schema_version --no-cov -q
```

Result:

```text
8 passed
```

Production review follow-up compatibility test:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_packaged_report_schema_loader_supports_python_38_resources --no-cov -q
```

Initial result:

```text
1 failed
AttributeError: module 'importlib.resources' has no attribute 'files'
```

After switching the loader to `importlib.resources.read_text(...)`, the focused
schema and CLI tests passed.

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
193 passed
Total coverage: 94.93%
Required coverage: 80%
```

Whitespace check:

```bash
git diff --check
```

Result: no output.

Package build check:

```bash
poetry build -f wheel
```

Result: not run locally because the `poetry` command and Python `build` module
are unavailable in this shell. The package resource include is covered by a
focused `pyproject.toml` contract test.

### Review

Ran the required production code quality review scripts against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `diff-line-map.py`
- `detect-stack.py`
- `run-safe-checks.py`

Follow-up inspection and optimization confirmed:

- schema discovery stays in `automation_runner`, not `automation_core`.
- the packaged schema matches the documented schema.
- unsupported schema versions return a clear CLI error without printing JSON.
- `pyproject.toml` declares the schema resource for both source and wheel
  distributions.
- `load_report_schema()` uses a Python 3.8-compatible `importlib.resources`
  API to match the declared package Python range.

### Next Phase

Stage, commit, and push the finished slice.
