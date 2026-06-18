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

## 2026-06-17: Task Runner Cancellation

### Completed

- Added a new `automation_core.tasks.TaskCancelledError` to represent
  intentional task cancellation.
- Extended `automation_core.tasks.TaskResult` with an explicit terminal
  `state` field so task results can distinguish succeeded, failed, and
  cancelled outcomes.
- Updated `TaskRunner.run(...)` so `TaskCancelledError` returns a cancelled
  result with `task.end` outcome `cancelled` instead of a normal failure.
- Kept ordinary exception handling and `KeyboardInterrupt` propagation
  unchanged.
- Documented the cancelled task outcome in `docs/adding-a-workflow.md`.
- Added import coverage and task runner tests for the cancelled path.

### Verification

Focused task/import verification:

```bash
.venv/bin/python -m pytest tests/tasks/test_runner.py tests/test_imports.py --no-cov -q
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
262 passed
Total coverage: 96.26%
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

- cancellation stays inside `automation_core.tasks`.
- cancelled tasks are represented explicitly instead of being converted into a
  generic failure.
- `KeyboardInterrupt` still propagates.
- `automation_core` remains business-agnostic.

### Next Phase

Proceed to the ecosystem consumer surface phase:

- publish workflow authoring helpers from `automation_runner`
- keep `examples/` as thin reference consumers
- document core/app/plugin repository boundaries

## 2026-06-17: Ecosystem Consumer Surface

### Completed

- Added `automation_runner.workflows` as the public workflow authoring module.
- Moved the shared workflow helper implementation out of `examples/` and into
  `automation_runner`.
- Kept `examples.workflows` as a compatibility layer for built-in examples and
  existing tests.
- Updated built-in Damai examples to import workflow authoring helpers from
  `automation_runner.workflows`.
- Updated runner modules to use `WorkflowResult` from
  `automation_runner.workflows`.
- Added `tests/runner/test_workflows.py` to verify the public workflow surface.
- Added `examples/README.md` and `docs/ecosystem.md`.
- Added structure tests that protect the thin-example boundary.

### Decision Record

#### Decision: promote workflow helpers instead of chaining re-exports

- Problem: the implementation plan sketched `automation_runner.workflows`
  forwarding to `examples.workflows` while `examples.workflows` also pointed
  back to the runner. That shape would create a circular import and make the
  public surface fragile.
- Choice: move the real implementation into `automation_runner.workflows` and
  reduce `examples.workflows` to a compatibility shim.
- Reason: external application repositories need a stable public dependency
  surface that does not rely on the example package internals.
- Risk: downstream code importing `examples.workflows` will continue to work
  for now, but the compatibility layer must remain documented until external
  consumers migrate.

#### Decision: use the repository virtualenv for verification

- Problem: the current shell environment does not expose a global `poetry`
  command.
- Choice: run verification through `/Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest`.
- Reason: this keeps phase verification moving without changing machine-wide
  tooling assumptions.
- Risk: command examples in docs still use `poetry`; CI and future execution
  should continue to verify that Poetry remains the supported workflow.

### Verification

Focused verification:

```bash
/Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest \
  tests/runner/test_workflows.py \
  tests/examples/damai_web/test_smoke_workflow.py \
  tests/examples/damai_android/test_smoke_workflow.py \
  tests/structure/test_boundaries.py \
  --no-cov -q
```

Result:

```text
44 passed
```

Full suite:

```bash
/Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest -q
```

Result:

```text
300 passed
Total coverage: 94.65%
Required coverage: 80%
```

Whitespace check:

```bash
git diff --check
```

Result: no output.

### Review

Ran the required production code quality review setup against
`/Users/mango/project/codex/automation-kit`:

- `collect-review-context.py`
- `run-safe-checks.py`

Review outcome:

- Severe issues: none
- Improvement suggestions:
  - keep migrating internal tests and helpers toward `automation_runner`
    imports so the compatibility shim can eventually be retired
  - add a dedicated compatibility matrix doc when application and plugin repos
    are created in later phases
- Quality score: 92
- Pass status: pass

Follow-up inspection confirmed:

- `automation_runner.workflows` is now the real implementation layer.
- `examples.workflows` no longer owns business-adjacent workflow primitives.
- built-in examples remain runnable and offline-testable.
- default verification remains browser/device/network free.

### Todo Status

- Phase 1 Task 1: done
- Phase 1 Task 2: done
- Phase 2 application repository work: pending
- Phase 3 plugin repository work: pending
- Phase 4 compatibility and CI federation: pending

### Next Phase Risk

- External application repos will need a stable minimum import surface from
  `automation_runner`; future changes to workflow result shapes should remain
  additive where possible.
- The compatibility shim in `examples.workflows` should not become permanent
  technical debt.

## 2026-06-17: Cross-Repo Compatibility And CI Baseline

### Completed

- Added `docs/compatibility.md` describing cross-repo versioning and the
  current verification matrix.
- Added `.github/workflows/ci.yml` to `automation-kit`.
- Extended structure tests so compatibility documentation becomes part of the
  repo boundary contract.
- Updated the root README to point readers to compatibility guidance in
  addition to ecosystem guidance.

### Decision Record

#### Decision: keep CI minimal and offline-first

- Problem: the ecosystem now spans multiple repositories, but default tests
  must still stay deterministic and not depend on browsers, devices, or
  network-side targets.
- Choice: define one simple Python CI job per repository that runs install plus
  offline pytest only.
- Reason: this matches the current documented baseline and avoids silently
  promoting live-system dependencies into default verification.
- Risk: future live integration coverage will need separate opt-in jobs instead
  of being folded into this baseline.

#### Decision: keep `poetry.lock` after final audit verification

- Problem: the final audit must prove the documented Poetry-based install and
  test path, not only raw local venv execution.
- Choice: run `poetry install && poetry run pytest -q` during the final audit
  and keep the resulting lockfile.
- Reason: the repository now declares Poetry-driven CI, so the lockfile is part
  of the reproducible delivery baseline.
- Risk: routine dependency drift becomes visible versioned change, which is
  acceptable for a shared foundation repo.

### Verification

Focused compatibility check:

```bash
/Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest \
  tests/structure/test_boundaries.py::test_compatibility_doc_exists \
  --no-cov -q
```

Result:

```text
1 passed
```

Full suite:

```bash
/Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest -q
```

Result:

```text
301 passed
Total coverage: 94.65%
Required coverage: 80%
```

### Review

Production code quality review outcome:

- Severe issues: none
- Improvement suggestions:
  - later add a matrix version table once published package versions begin to
    diverge
  - keep CI scoped to offline checks unless a repository explicitly introduces
    opt-in live jobs
- Quality score: 91
- Pass status: pass

### Final Audit Note

- Confirmed the documented Poetry path:
  `poetry install && poetry run pytest -q`.

Commit and push the finished slice, then continue with the next roadmap slice.

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

## 2026-06-18: Phase 5 Slidex Visual Platform Baseline

### Completed

- Added `docs/slidex-visual-platform.md` as the automation-kit-side baseline
  for consuming the latest `dengyie/slidex` visual platform.
- Updated `README.md`, `docs/ecosystem.md`, `docs/compatibility.md`, and
  `docs/development-system.md` to point to the new slidex integration baseline.
- Documented the latest local slidex baseline:
  `aa48a12 Fix visual solver cleanup and artifacts`.
- Recorded the current slidex public consumer surface:
  `VisualChallengeSolver`, `VisualChallengeRequest`, `VisualChallengeResult`,
  `to_action_result`, `to_artifacts`, and `to_events`.
- Captured resource ownership for Playwright page reuse: application owns the
  page/browser lifecycle, while slidex owns and cleans its temporary listener
  and CDP session.
- Extended the structure boundary test so the new slidex baseline document is
  checked with the ecosystem docs.

### Decision Record

#### Decision: keep slidex optional and outward-only

Problem: slidex now exposes native automation-kit adapters, but importing
slidex from `automation_core` would make the base depend on a visual platform.

Choice: keep the dependency direction one-way. Applications may install and
instantiate slidex, and slidex may convert its result outward to automation-kit
objects when automation-kit is import-visible.

Reason: preserves the core rule that `automation_core` stays business-agnostic
and visual-platform-agnostic while still giving application repositories a
stable integration path.

Risk: application repositories must add their own optional integration tests
once they inject slidex in real workflows.

#### Decision: document dict and native adapter modes separately

Problem: slidex has two adapter modes: JSON-safe dictionaries by default and
native automation-kit dataclasses with `prefer_native=True`.

Choice: document both modes explicitly instead of requiring automation-kit to
wrap or normalize slidex output again.

Reason: keeps automation-kit generic and lets applications choose between
report-friendly dict payloads and native `ActionResult`, `ArtifactHandle`, and
`EventEnvelope` values.

Risk: downstream workflows must choose one mode consistently at report assembly
boundaries.

### Verification

Structure boundary test without global coverage gate:

```bash
.venv/bin/python -m pytest -q -o addopts='' tests/structure/test_boundaries.py
```

Result:

```text
9 passed
```

Full automation-kit suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
302 passed
Total coverage: 95.12%
Required coverage: 80%
```

Slidex optional native adapter compatibility:

```bash
PYTHONPATH=/Users/mango/project/codex/automation-kit /opt/homebrew/bin/pytest -q tests/test_automation_kit_integration.py
```

Result:

```text
6 passed
```

Whitespace check:

```bash
git diff --check
```

Result: no output.

### Production Code Quality Review

Mode: checkpoint.

Scope: documentation and structure-test updates for the slidex visual platform
integration baseline.

Findings: no P0/P1/P2 correctness, safety, boundary, or irreversible operation
issues found in the current diff.

Improvement suggestions:

- Keep app-level slidex integration tests in application repositories, not in
  automation-kit default tests.
- Continue treating slidex compatibility as optional and explicit at workflow
  construction boundaries.

Quality score: 92/100.

Status: passed.

### Todo Status

- Phase 5 documentation baseline: done.
- automation-kit core implementation changes: not needed for this phase.
- application repository slidex injection: pending next phase.
- app-level compatibility tests with slidex: pending next phase.

### Next Phase Risk

Application repositories may still use old local visual or OCR assumptions.
Next phase should update app workflows to inject slidex at workflow boundaries
and add optional compatibility tests without making default offline tests depend
on browser, device, network, or slidex.

## 2026-06-18: Phase 6 Application Slidex Injection Closure

### Completed

- Confirmed `automation-plugin-ocr` is archived and deprecated in favor of
  `dengyie/slidex`.
- Updated `automation-app-damai` with lazy app-layer helpers for
  `PLAYWRIGHT_PAGE` slider challenge request construction and slidex result
  conversion.
- Updated `automation-app-dianping` with lazy app-layer helpers for
  `ANDROID_SCREENSHOT_BYTES` image-text request construction and slidex result
  conversion.
- Confirmed both application repositories keep default offline tests free of
  slidex/browser/device/network requirements.
- Updated `docs/slidex-visual-platform.md` so the ecosystem status now reflects
  completed app-level helper and compatibility-test work.

### Decision Record

#### Decision: close app-level helper work before live workflow execution

Problem: the apps can now construct slidex requests and convert slidex results,
but they still do not own real production browser pages or Android screenshot
bytes in the offline smoke workflows.

Choice: close this phase at the app-level helper boundary and leave live
browser/Appium execution for future production workflow phases.

Reason: this preserves the offline default test contract while making the
slidex integration surface concrete and testable in each application repo.

Risk: live production challenge behavior remains unproven until the app
workflows own real page/screenshot resources.

### Verification

automation-plugin-ocr archived baseline:

```bash
/Users/mango/project/codex/automation-plugin-ocr/.venv/bin/python -m pytest -q
```

Result:

```text
2 passed
Total coverage: 93.75%
Required coverage: 80%
```

Damai default offline suite:

```bash
/Users/mango/project/codex/automation-app-damai/.venv/bin/python -m pytest -q
```

Result:

```text
9 passed, 2 skipped
Total coverage: 85.29%
Required coverage: 80%
```

Damai slidex compatibility slice:

```bash
PYTHONPATH=/Users/mango/project/codex/automation-app-damai:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'
```

Result:

```text
2 passed, 4 deselected
```

Dianping default offline suite:

```bash
/Users/mango/project/codex/automation-app-dianping/.venv/bin/python -m pytest -q
```

Result:

```text
6 passed, 2 skipped
Total coverage: 100.00%
Required coverage: 80%
```

Dianping slidex compatibility slice:

```bash
PYTHONPATH=/Users/mango/project/codex/automation-app-dianping:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'
```

Result:

```text
2 passed, 4 deselected
```

### Production Code Quality Review

Mode: checkpoint.

Findings: no P0/P1/P2 correctness, boundary, safety, or irreversible operation
issues found across the application helper and documentation changes.

Improvement suggestions:

- Raise Dianping default-suite coverage above the 80% floor in the next Android
  workflow slice.
- Add live browser/Appium visual challenge tests only when those resources are
  explicitly opt-in and owned by the application workflow.

Quality score: 89/100.

Status: passed.

### Todo Status

- automation-plugin-ocr archived path: done.
- Damai app-level slidex helper and compatibility test: done.
- Dianping app-level slidex helper and compatibility test: done.
- automation-kit core dependency boundary: preserved.
- Live Damai browser visual solving: pending future production workflow phase.
- Live Dianping Android visual solving: pending future production workflow
  phase.

### Next Phase Risk

The ecosystem has a stable optional slidex integration contract, but live
end-to-end visual challenge execution still depends on production app workflows
owning real browser pages or Android screenshot bytes.

## 2026-06-18: Phase 7 Slidex Contract Re-Review

### Completed

- Re-read the latest committed slidex implementation at
  `aa48a12 Fix visual solver cleanup and artifacts`.
- Checked the current slidex working-tree documentation draft for
  `docs/automation-kit-vision-platform.md` and confirmed it is directionally
  aligned with the automation-kit boundary model.
- Updated `docs/slidex-visual-platform.md` with implementation-level facts:
  OCR and image-text route through the configured OCR extractor, slider solving
  supports `cdp` and `playwright_page`, unsupported paths return failed
  `VisualChallengeResult` values, and slider resources are closed in `finally`.
- Extended `docs/compatibility.md` so the cross-repository verification list
  includes the Damai and Dianping optional slidex slices.

### Decision Record

#### Decision: keep slidex draft docs non-authoritative until committed

Problem: slidex has pending documentation changes that introduce a broader
automation-kit vision platform design document, but those changes are still
uncommitted in the slidex working tree.

Choice: automation-kit references the committed slidex code baseline and records
that the slidex draft document is aligned but not yet part of the committed
baseline.

Reason: this keeps automation-kit development docs tied to reproducible code
while still acknowledging the newest design direction.

Risk: once slidex commits the draft document, automation-kit should re-check
whether any examples or status lines changed.

### Verification

Focused documentation boundary test:

```bash
.venv/bin/python -m pytest -q -o addopts='' tests/structure/test_boundaries.py
```

Result:

```text
9 passed
```

Full automation-kit suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
302 passed
Total coverage: 95.12%
Required coverage: 80%
```

### Production Code Quality Review

Mode: checkpoint.

Scope: development documentation re-review after slidex latest code and
documentation draft inspection.

Findings: no P0/P1/P2 correctness, boundary, safety, or irreversible operation
issues found in the documentation diff.

Improvement suggestions:

- Re-run this review after slidex commits and pushes its currently uncommitted
  documentation draft.
- Keep live browser/Appium visual execution out of the core baseline until the
  application repositories own those resources explicitly.

Quality score: 93/100.

Status: passed.

## 2026-06-18: Phase 8 Application Live Visual Helper Sync

### Completed

- Re-read the latest application commits:
  - `automation-app-damai`: `3ccd788 feat(阶段5): 补齐 damai live 视觉调用边界`
  - `automation-app-dianping`: `3a1c94e feat(阶段5): 补齐 dianping 截图视觉调用边界`
  - `slidex`: `b5e6521 docs(阶段8): 固化 automation-kit 视觉平台基线`
- Updated `docs/slidex-visual-platform.md` so the current ecosystem status now
  distinguishes implemented app-layer live helpers from still-pending opt-in
  target-site/device E2E validation.
- Updated `docs/compatibility.md` with the new focused live-helper slices:
  `solve_slider_visual_challenge` and
  `solve_android_screenshot_visual_challenge`.

### Decision Record

#### Decision: keep live helper completion separate from real E2E completion

Problem: Damai and Dianping now expose production-callable helpers, but neither
repository can prove target-site CAPTCHA availability or real Android device
state in default tests.

Choice: mark the app-layer live helper boundary as done and keep real
Playwright/Appium E2E as opt-in validation.

Reason: this closes the code-owned integration boundary without weakening the
no-live-default policy or adding browser/Appium concepts to `automation_core`.

Risk: production rollout still needs a user-side target environment smoke run.

### Verification

Damai live-helper slice:

```bash
PYTHONPATH=/Users/mango/project/codex/automation-app-damai:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'solve_slider_visual_challenge'
```

Result:

```text
2 passed, 6 deselected
```

Dianping live-helper slice:

```bash
PYTHONPATH=/Users/mango/project/codex/automation-app-dianping:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'solve_android_screenshot_visual_challenge'
```

Result:

```text
3 passed, 6 deselected
```

### Production Code Quality Review

Mode: checkpoint.

Findings: no P0/P1/P2 correctness, boundary, safety, or irreversible operation
issues found in the documentation sync.

Improvement suggestions:

- Keep real browser/device validation opt-in and environment-specific.

Quality score: 92/100.

Status: passed.

## 2026-06-18: Phase 9 GitHub Publication Closure

### Completed

- Pushed the latest local commits to GitHub for:
  - `automation-kit`
  - `automation-app-damai`
  - `automation-app-dianping`
  - `slidex`
- Confirmed all five ecosystem repositories are public on GitHub.
- Confirmed `automation-plugin-ocr` is archived on GitHub and remains public.
- Confirmed all five local repositories are clean and aligned with
  `origin/main`.

### Decision Record

#### Decision: treat external E2E as environment validation, not local code todo

Problem: the only remaining incomplete item depends on real target-site CAPTCHA
availability or a real Android/Appium device state.

Choice: keep those checks as opt-in production validation and close the local
code/documentation baseline once repositories are public, pushed, tested, and
reviewed.

Reason: default tests intentionally avoid browser/device/network dependencies,
and the app-layer helper boundaries are already implemented and verified with
fake resources.

Risk: production rollout still needs one environment-specific smoke run before
using the helpers against live targets.

### Verification

GitHub repository state:

```text
automation-kit: public, not archived
automation-app-damai: public, not archived
automation-app-dianping: public, not archived
automation-plugin-ocr: public, archived
slidex: public, not archived
```

Local repository state:

```text
automation-kit: main...origin/main
automation-app-damai: main...origin/main
automation-app-dianping: main...origin/main
automation-plugin-ocr: main...origin/main
slidex: main...origin/main
```

### Production Code Quality Review

Mode: checkpoint.

Findings: no P0/P1/P2 correctness, boundary, safety, or irreversible operation
issues found in the publication closure.

Improvement suggestions:

- Run target-site/device smoke tests only in the owner-controlled production
  environment.

Quality score: 94/100.

Status: passed.

## 2026-06-17: Runner Report Contract Consistency

### Completed

- Added a design note and implementation plan for tightening runner report
  contract consistency without changing schema version `"1"`.
- Added report-schema regression coverage that compares the documented artifact
  report-entry fields in `docs/artifacts.md` with a real
  `build_report(...).to_dict()` artifact entry.
- Added report-schema coverage for artifact metadata safety wording so report
  docs keep mentioning metadata and redaction behavior.
- Updated `docs/artifacts.md` to match the existing runner report contract:
  artifact entries include `artifact_type`, `path`, and `metadata`.
- Documented that artifact metadata should stay generic and small and that
  runner JSON serialization redacts sensitive metadata keys.
- Left `automation_runner.reports`, packaged schema files, and
  `automation_core` unchanged.

### Verification

Focused red verification before doc alignment:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_artifact_guide_documents_current_artifact_report_fields tests/runner/test_report_schema.py::test_artifact_guide_documents_metadata_safety_rules --no-cov -q
```

Initial result:

```text
2 failed
```

Focused green verification after doc/test alignment:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_artifact_guide_documents_current_artifact_report_fields tests/runner/test_report_schema.py::test_artifact_guide_documents_metadata_safety_rules --no-cov -q
```

Result:

```text
2 passed
```

Report schema regression tests:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Result:

```text
9 passed
```

Runner regression tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
102 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
295 passed
Total coverage: 96.14%
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

- the change stays in report-contract documentation and test coverage;
- `docs/artifacts.md` now matches the current emitted runner report artifact
  shape;
- packaged schema parity and runtime report shape remain unchanged;
- `automation_core` remains untouched and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner CLI Blank String Validation

### Completed

- Added CLI regression coverage for explicit whitespace-only values passed to:
  - `--url` for `damai-web-smoke`
  - `--app-id` for `damai-android-smoke`
  - `--workflow-factory`
  - `--factory` in live mode
- Added override regression coverage proving explicit blank `--url` and
  `--app-id` do not silently fall back to config defaults.
- Tightened `automation_runner.cli` merge behavior so:
  - explicit blank `--url` and `--app-id` become missing values and trigger the
    built-in required-option errors,
  - explicit blank `--factory` and `--workflow-factory` keep surfacing the
    import-path validation error instead of being treated as omitted.
- Added a focused CLI helper to keep this logic inside `automation_runner`
  without changing `automation_core`.
- Documented the non-whitespace requirement for explicit CLI string inputs in
  `README.md` and `docs/adding-a-workflow.md`.

### Verification

Focused red verification:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_blank_explicit_workflow_factory tests/runner/test_cli.py::test_cli_rejects_blank_explicit_factory_for_live_workflow --no-cov -q
```

Result:

```text
2 failed, 2 passed
```

Focused override red verification:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_even_with_config_default tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_even_with_config_default --no-cov -q
```

Result:

```text
2 failed
```

Focused green verification:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_even_with_config_default tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_even_with_config_default tests/runner/test_cli.py::test_cli_rejects_blank_explicit_workflow_factory tests/runner/test_cli.py::test_cli_rejects_blank_explicit_factory_for_live_workflow --no-cov -q
```

Result:

```text
6 passed
```

Runner regression tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
100 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
293 passed
Total coverage: 96.14%
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

- the change stays inside `automation_runner.cli`, which is the correct
  ownership layer for CLI argument semantics;
- built-in required-option validation now rejects explicit blank `--url` and
  `--app-id` even when config defaults are present;
- explicit blank factory import paths still produce the existing
  `import path must use module:object` error instead of changing failure mode;
- `automation_core` remains unchanged and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Step Action Name Validation

### Completed

- Added a design note and implementation plan for constructor-level action name
  validation in example workflows.
- Added focused tests for `WorkflowStep.action(...)` rejecting empty,
  traversal-like, and non-string names.
- Added a valid-action regression test proving parameters are preserved.
- Added `_validate_workflow_action_name(...)` in `examples.workflows` and wired
  it into `WorkflowStep.action(...)`.
- Documented that `WorkflowStep` authoring helpers reject invalid names before
  workflow execution starts.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'action_rejects_invalid_name or action_rejects_non_string_name or action_allows_valid_name' --no-cov -q
```

Initial result:

```text
6 failed, 1 passed, 23 deselected
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'action_rejects_invalid_name or action_rejects_non_string_name or action_allows_valid_name' --no-cov -q
```

Result:

```text
7 passed, 23 deselected
```

Example regression tests:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Result:

```text
34 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
278 passed
Total coverage: 96.29%
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

- action validation remains in the example authoring layer.
- `automation_core.actions.ActionRequest` remains generic and unchanged.
- adapter-specific action vocabularies remain in adapters and examples.
- invalid constructor inputs are covered by tests that failed before the fix.
- valid action names and parameters remain backward compatible.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Step Artifact Name Validation

### Completed

- Added a design note and implementation plan for explicit artifact-name
  validation in `WorkflowStep.artifact(...)`.
- Added example coverage for invalid string artifact names, non-string artifact
  names, and a valid-name regression.
- Updated `WorkflowStep.artifact(...)` so empty, whitespace-only, and
  traversal-like names fail immediately at the authoring boundary.
- Tightened the validator during production review so non-string names fail
  instead of being coerced with `str(...)`.
- Documented the workflow authoring boundary in `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'artifact_rejects_invalid_name or artifact_allows_valid_name' --no-cov -q
```

Initial result:

```text
4 failed, 1 passed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py -k 'artifact_rejects_invalid_name or artifact_allows_valid_name' --no-cov -q
```

Result:

```text
7 passed, 16 deselected
```

Example regression tests:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Result:

```text
27 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
271 passed
Total coverage: 96.29%
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

Review follow-up found and fixed one issue:

- `WorkflowStep.artifact(...)` initially validated names through `str(name)`,
  which would have accepted non-string values such as `None` or `123`.
  Added non-string regression coverage and changed the validator to reject
  non-string names directly.

Follow-up inspection confirmed:

- artifact-name validation stays in `examples.workflows`, where the
  `WorkflowStep` authoring helper lives.
- `automation_core` remains unchanged and business-agnostic.
- invalid artifact names now fail before workflow execution starts.
- storage-layer artifact validation remains unchanged as a separate safeguard.
- valid artifact step construction and existing example workflows remain
  covered by focused regression tests.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Step Kind Validation

### Completed

- Added a design note and implementation plan for explicit
  `WorkflowStep.kind` validation.
- Added a web example regression test covering an unsupported step kind after
  earlier action and artifact steps already completed.
- Updated `run_workflow_steps(...)` so unsupported step kinds return a failed
  `ExampleWorkflowResult` with a direct structured error instead of falling
  into the artifact branch.
- Preserved already completed action and artifact evidence when the invalid
  step is reached.
- Documented the authoring boundary in `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_run_workflow_steps_rejects_unknown_step_kind_and_preserves_prior_results --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_run_workflow_steps_rejects_unknown_step_kind_and_preserves_prior_results --no-cov -q
```

Result:

```text
1 passed
```

Example regression tests:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Result:

```text
20 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
264 passed
Total coverage: 96.29%
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

- step-kind validation stays in `examples.workflows`, where the
  `WorkflowStep` authoring helper lives.
- `automation_core` remains unchanged and business-agnostic.
- unsupported workflow step kinds now fail with a direct structured error
  instead of surfacing an indirect `KeyError`.
- already completed actions and artifacts are preserved when the invalid step
  is reached.
- existing action, artifact, and action-batch failure behavior remains covered
  by the example regression tests.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Cancelled Exit Code

### Completed

- Added a design note and implementation plan for a distinct cancelled runner
  exit code.
- Tightened the cancelled JSON CLI regression test to assert the new process
  exit-code contract.
- Added plain-text CLI coverage proving cancelled custom workflows return the
  same distinct exit code without requiring JSON parsing.
- Added `_workflow_exit_code(...)` in `automation_runner.cli` so cancelled
  workflow results return exit code `130` while failed runs still return `1`
  and successful runs still return `0`.
- Documented the cancelled exit-code contract in `README.md` and
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_is_cancelled tests/runner/test_cli.py::test_cli_returns_cancelled_exit_code_without_json --no-cov -q
```

Initial result:

```text
2 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_is_cancelled tests/runner/test_cli.py::test_cli_returns_cancelled_exit_code_without_json --no-cov -q
```

Result:

```text
2 passed
```

Runner CLI regression tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Result:

```text
48 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
263 passed
Total coverage: 96.29%
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

- cancelled exit-code policy stays in `automation_runner.cli`.
- `automation_core` cancellation models and report schemas remain unchanged.
- cancelled JSON and plain-text CLI paths now share one exit-code mapping.
- validation/configuration errors still return `2`, failures still return `1`,
  and cancelled runs now return `130`.
- focused and full runner tests would fail if the cancelled path regressed back
  to the failure exit code.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Task Cancellation

### Completed

- Added a design note and implementation plan for runner-level task
  cancellation propagation.
- Extended `examples.workflows.ExampleWorkflowResult` with explicit terminal
  `state` tracking so workflow, runner, and report layers can distinguish
  succeeded, failed, and cancelled outcomes.
- Updated `ExampleWorkflow.run()` so `TaskCancelledError` produces a cancelled
  workflow result with `task.start` and `task.end` events, without a synthetic
  error event.
- Updated `automation_runner.cli` to map cancelled workflow results to
  `RunState.cancel(...)`.
- Updated `automation_runner.reports.build_report()` so top-level report
  `status` becomes `cancelled` when the run state is cancelled.
- Documented cancelled report behavior in `README.md` and
  `docs/adding-a-workflow.md`.

### Verification

Focused examples/runner verification:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py tests/runner/test_cli.py tests/runner/test_reports.py tests/runner/test_report_schema.py --no-cov -q
```

Result:

```text
83 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
259 passed
Total coverage: 96.22%
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

- cancellation stays expressed as a core runtime signal and is only serialized
  into CLI/report policy at the runner layer.
- cancelled workflows are no longer flattened into failed reports.
- ordinary failure and startup-failure behavior remains unchanged.
- `automation_core` remains business-agnostic.

### Next Phase

Commit and push the finished slice, then continue with the next roadmap slice.

## 2026-06-17: Element Lookup Session Contract Alignment

### Completed

- Added a design note and implementation plan for aligning the core element
  lookup session contract with the real adapter lookup shape.
- Updated `automation_core.drivers.ElementLookupSession` so
  `find_element(...)` accepts both an optional lookup strategy and a selector.
- Updated driver contract tests so the fake lookup session matches the real
  two-argument lookup shape already used by Selenium and Appium adapters.
- Documented the aligned contract shape in `docs/adding-a-workflow.md`.
- Kept `automation_core` business-agnostic and left Selenium/Appium runtime
  behavior unchanged.

### Verification

Focused driver/import verification:

```bash
.venv/bin/python -m pytest tests/drivers/test_contracts.py tests/test_imports.py --no-cov -q
```

Result:

```text
16 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
258 passed
Total coverage: 96.20%
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

- the contract change lives in `automation_core.drivers`.
- Selenium/Appium adapter lookup behavior was already using the aligned shape.
- the update removes a misleading core boundary without adding business
  coupling.
- `automation_core` remains business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Task Event Deduplication

### Completed

- Added a design note and implementation plan for task lifecycle event
  deduplication in example workflow event assembly.
- Added regression coverage proving `ExampleWorkflow` does not duplicate
  caller-provided `task.start` and `task.end` events when they already match
  the workflow result.
- Updated `ExampleWorkflow.run(...)` to skip automatic lifecycle event
  creation when the workflow result already includes matching lifecycle
  events.
- Documented the task event deduplication behavior in
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_task_events --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_task_events tests/examples/damai_web/test_smoke_workflow.py::test_damai_web_smoke_workflow_factory_returns_runnable_workflow tests/examples/damai_android/test_smoke_workflow.py::test_damai_android_smoke_workflow_factory_returns_runnable_workflow --no-cov -q
```

Result:

```text
3 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
258 passed
Total coverage: 96.20%
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

- task lifecycle event deduplication lives in `examples.workflows`.
- caller-provided workflow events are still preserved.
- automatic lifecycle events are still created for built-in workflows that
  only return artifact handles or no explicit lifecycle events.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Artifact Event Deduplication

### Completed

- Added a design note and implementation plan for artifact event deduplication
  in example workflow event assembly.
- Added regression coverage proving `ExampleWorkflow` does not duplicate an
  `artifact` event when the workflow result already includes a matching
  caller-provided artifact event.
- Updated `ExampleWorkflow.run(...)` to skip automatic artifact event creation
  for artifacts already represented by returned events.
- Documented the artifact event deduplication behavior in
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_artifact_events --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py::test_example_workflow_does_not_duplicate_returned_artifact_events tests/examples/damai_web/test_smoke_workflow.py::test_damai_web_smoke_workflow_factory_returns_runnable_workflow tests/examples/damai_android/test_smoke_workflow.py::test_damai_android_smoke_workflow_factory_returns_runnable_workflow --no-cov -q
```

Result:

```text
3 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
257 passed
Total coverage: 96.20%
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

- artifact event deduplication lives in `examples.workflows`.
- caller-provided workflow events are still preserved.
- automatic artifact events are still created for built-in workflows that only
  return artifact handles.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Report Contract Run State Documentation

### Completed

- Added a design note and implementation plan for keeping the workflow guide's
  report contract field list aligned with the actual runner report.
- Added a documentation regression test that parses
  `docs/adding-a-workflow.md` and compares the documented top-level JSON report
  fields with a sample `build_report(...)` output.
- Documented the missing `run_state` field in the workflow authoring guide.
- Left report serialization, JSON schema files, and `automation_core`
  unchanged.

### Verification

Focused red run before documentation update:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_workflow_guide_documents_current_top_level_report_fields --no-cov -q
```

Initial result:

```text
1 failed
Extra items in the right set: 'run_state'
```

Focused green run after documentation update:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_workflow_guide_documents_current_top_level_report_fields --no-cov -q
```

Result:

```text
1 passed
```

Report schema regression tests:

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Result:

```text
7 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
256 passed
Total coverage: 96.20%
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

- the human workflow guide now lists all current top-level report fields.
- the added regression test guards future guide/report drift.
- report serialization and packaged schema files remain unchanged.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Examples Metadata Consistency

### Completed

- Added a design note and implementation plan for built-in examples metadata
  consistency.
- Added a regression test for `examples --json` when a workflow is present in
  `WORKFLOWS` without matching `WORKFLOW_METADATA`.
- Updated JSON examples discovery to validate metadata before printing the
  payload.
- Converted the previous raw `KeyError` path into a clear CLI error with exit
  code `2` and no partial stdout.
- Documented that built-in workflow entries must have matching discovery
  metadata.
- Left plain text `automation-runner examples` behavior unchanged.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_examples_json_rejects_workflow_missing_metadata --no-cov -q
```

Initial result:

```text
1 failed
KeyError: 'missing-metadata'
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json or missing_metadata' --no-cov -q
```

Result:

```text
3 passed, 43 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
255 passed
Total coverage: 96.20%
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

- metadata validation stays in `automation_runner.cli`.
- successful JSON discovery shape remains unchanged.
- missing metadata fails before any JSON is emitted.
- plain text examples listing still only reads `WORKFLOWS`.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Examples JSON Metadata

### Completed

- Added a design note and implementation plan for richer built-in example
  workflow discovery metadata.
- Updated `automation-runner examples --json` so each built-in workflow entry
  includes `name`, `description`, `platform`, `required_options`, and
  `supports_dry_run`.
- Preserved the top-level `dry_run` and `workflows` JSON shape.
- Kept plain text `automation-runner examples` behavior unchanged.
- Documented the metadata fields in `README.md` and
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Initial result:

```text
2 failed, 43 deselected
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Result:

```text
2 passed, 43 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
254 passed
Total coverage: 96.15%
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

- metadata lives beside the built-in `WORKFLOWS` registry in
  `automation_runner.cli`.
- discovery output remains deterministic and offline.
- no live session factories or adapters are loaded by examples discovery.
- no workflow registry or business metadata moved into `automation_core`.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Report Event Payload Redaction

### Completed

- Added a design note and implementation plan for runner report event payload
  redaction.
- Added report serialization coverage for sensitive event payload keys,
  including nested dictionaries and dictionaries inside lists.
- Added recursive report-level redaction for sensitive keys containing
  `authorization`, `cookie`, `password`, `secret`, or `token`.
- Reused the same redaction helper for artifact metadata so report-safe key
  handling stays consistent.
- Updated `build_report(...)` to serialize events through a report-safe helper.
- Documented event payload redaction in `docs/adding-a-workflow.md`.
- Left `automation_core.events` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
```

Initial result:

```text
1 failed, 8 passed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
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
254 passed
Total coverage: 96.13%
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

- redaction happens in `automation_runner.reports`.
- `EventEnvelope` payloads remain unchanged before report serialization.
- event payload dictionaries are redacted recursively by sensitive key name.
- artifact metadata redaction still uses the same report-safe key policy.
- the runner report schema remains unchanged because event payloads are still
  extensible objects.
- `automation_core.events` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Workflow Artifact Failure Reporting

### Completed

- Added a design note and implementation plan for workflow artifact failure
  reporting.
- Added web example workflow coverage for artifact capture failures after prior
  actions and artifacts have already completed.
- Added `ExampleWorkflow` coverage for returned failed results that need an
  `error` event.
- Added coverage proving caller-provided `error` events are not duplicated.
- Updated `run_workflow_steps(...)` so artifact capture failures return a
  failed `ExampleWorkflowResult` that preserves prior actions, prior artifacts,
  and the current action batch summary.
- Updated `ExampleWorkflow.run(...)` so returned failed results with `error`
  produce a task-level `error` event before `task.end` when one is not already
  present.
- Documented the artifact-step failure behavior in
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Initial result:

```text
2 failed, 9 passed
```

Error-event deduplication red run before final adjustment:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Result:

```text
1 failed, 11 passed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Result:

```text
16 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
250 passed
Total coverage: 96.03%
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

- artifact failure reporting remains in `examples.workflows`.
- already executed actions and already captured artifacts are preserved when a
  later artifact step fails.
- returned failed workflow results emit one task-level `error` event before
  `task.end`.
- caller-provided `error` events are not duplicated.
- Python type annotations remain compatible with the project's `python = "^3.8"`
  declaration.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Action Executor Exception Results

### Completed

- Added a design note and implementation plan for action executor exception
  result handling.
- Added core action executor tests for ordinary session action exceptions.
- Added core batch tests proving prior action results are preserved and later
  actions are skipped when an action raises.
- Added interruption coverage proving `KeyboardInterrupt` still propagates.
- Updated web, Android, and CLI workflow tests to expect structured failed
  action results instead of top-level workflow exceptions for action execution
  failures.
- Updated `ActionExecutor.run(...)` so ordinary `execute_action(...)`
  exceptions return failed `ActionResult` values.
- Documented the action batch exception contract in `docs/adding-a-workflow.md`.
- Kept the behavior generic in `automation_core.actions` with no business,
  website, or Android-specific logic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/actions/test_action_models.py tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py --no-cov -q
```

Initial result:

```text
4 failed, 24 passed
```

Focused green run after implementation and expectation updates:

```bash
.venv/bin/python -m pytest tests/actions/test_action_models.py tests/examples/damai_web/test_smoke_workflow.py tests/examples/damai_android/test_smoke_workflow.py tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_fails --no-cov -q
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
253 passed
Total coverage: 96.05%
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

- exception normalization lives in `automation_core.actions.ActionExecutor`.
- ordinary action exceptions become failed `ActionResult` values.
- `KeyboardInterrupt` and other non-`Exception` interruption paths are not
  swallowed.
- batch skipped-action reporting remains unchanged.
- workflow and CLI reports now retain structured failed action evidence.
- `automation_core` remains business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Adapter Action Execution Failure Handling

### Completed

- Added a design note and implementation plan for adapter action execution
  failure handling.
- Extended Selenium adapter tests for driver navigation, element click, text
  clear, text send, and raw driver action failures.
- Extended Appium adapter tests for app launch, mobile script, coordinate tap,
  element tap, text clear, text send, and raw driver action failures.
- Added small per-adapter `_run_action(...)` helpers so aliased and raw supported
  actions return failed `ActionResult` values when the underlying driver or
  element operation raises.
- Kept required-parameter validation, unsupported-action behavior, element
  lookup semantics, and `wait_for_element` retry semantics unchanged.
- Documented the adapter execution-failure contract in
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Initial result:

```text
12 failed, 55 passed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Result:

```text
67 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
247 passed
Total coverage: 96.03%
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

- action execution failures are normalized only inside concrete adapters.
- successful action messages and `data` payloads remain unchanged.
- parameter validation and lookup failures still return their existing messages.
- `wait_for_element` still uses retry semantics and timeout messaging.
- no auth or access-control logic was changed; the review risk flag was
  triggered by adapter terminology rather than a security path.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Retry Snapshot Event Bridge

### Completed

- Added a design note and implementation plan for retry snapshot to event
  bridging.
- Added `retry_attempt_event_from_snapshot(...)` in `automation_core.events`.
- Kept the bridge one-way: `automation_core.events` can adapt retry snapshots,
  while `automation_core.retries` remains independent from events.
- Added focused tests proving the bridge and the retry boundary.
- Documented the one-way retry-to-event wiring rule in `docs/development-system.md`.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/events/test_events.py tests/structure/test_boundaries.py --no-cov -q
```

Initial result:

```text
ImportError: cannot import name 'retry_attempt_event_from_snapshot'
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/events/test_events.py tests/structure/test_boundaries.py --no-cov -q
```

Result:

```text
14 passed
```

### Review

Full verification:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
215 passed in 0.26s
Total coverage: 95.03%
```

Diff hygiene:

```bash
git diff --check
```

Result: no output.

Production review scripts:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Result: review context and changed-line maps were generated; stack detection
reported Python; no additional review blockers were found.

The safe-check helper suggested `python3 -m unittest discover`. In this pytest
repository, running the equivalent command returned no discovered unittest
tests:

```bash
.venv/bin/python -m unittest discover
```

Result:

```text
Ran 0 tests in 0.000s
NO TESTS RAN
```

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Retry Attempt Observer

### Completed

- Added a design note and implementation plan for retry attempt observability.
- Added `RetryAttemptSnapshot` as an immutable retry-attempt state object.
- Added optional `on_attempt` support to `retry_until(...)`.
- Kept retry observability inside `automation_core.retries` without importing
  event, runner, adapter, or business modules.
- Exported `RetryAttemptSnapshot` from `automation_core.retries`.
- Documented that higher layers own conversion from retry snapshots into
  task events, logs, and reports.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/retries/test_policy.py --no-cov -q
```

Initial result:

```text
1 error
ImportError: cannot import name 'RetryAttemptSnapshot'
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/retries/test_policy.py --no-cov -q
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
213 passed
Total coverage: 95.01%
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

- retry attempt snapshots stay in `automation_core.retries`.
- the retry package still does not import event, runner, adapter, or business
  modules.
- existing retry callers remain compatible because `on_attempt` is optional.
- snapshots cover predicate misses, retryable exceptions, terminal failure, and
  final success.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-16: Adapter Wait For Element Alias

### Completed

- Added a design note and implementation plan for adapter-level element waits.
- Added Selenium `wait_for_element` action alias.
- Added Appium `wait_for_element` action alias.
- Reused `automation_core.retries.retry_until` for bounded polling.
- Kept wait behavior in `adapters` without changing `automation_core`.
- Added offline fake-driver tests for:
  - retrying until an element appears.
  - timeout reporting when the element never appears.
  - missing selector validation.
  - missing driver lookup support.
- Documented the wait alias in `docs/adding-a-workflow.md`.

### Verification

Focused red runs before implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Initial result:

```text
Selenium: 3 failed, 16 passed
Appium: 3 failed, 19 passed
```

Follow-up red run for missing lookup support:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py::test_selenium_session_wait_for_element_reports_missing_lookup_support --no-cov -q
```

Initial result:

```text
1 failed
```

Production review follow-up red runs for invalid wait timing inputs:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py::test_selenium_session_wait_for_element_rejects_invalid_timeout tests/adapters/selenium/test_session.py::test_selenium_session_wait_for_element_rejects_invalid_interval --no-cov -q
.venv/bin/python -m pytest tests/adapters/appium/test_session.py::test_appium_session_wait_for_element_rejects_invalid_timeout tests/adapters/appium/test_session.py::test_appium_session_wait_for_element_rejects_invalid_interval --no-cov -q
```

Initial result:

```text
Selenium: 2 failed
Appium: 2 failed
```

Focused green runs after implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Result:

```text
Selenium: 24 passed
Appium: 27 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
209 passed
Total coverage: 94.93%
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

Follow-up inspection and optimization confirmed:

- wait behavior stays in `adapters`, not `automation_core`.
- waiting reuses the existing bounded retry primitive.
- missing driver lookup support returns a direct failed `ActionResult`.
- negative timeout and interval inputs return failed `ActionResult` values
  instead of leaking `RetryPolicy` exceptions.
- non-numeric timeout and interval inputs return failed `ActionResult` values
  instead of leaking `TypeError`.
- default tests still use fake drivers and require no live browser, Appium,
  ADB, Android device, or network.

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

## 2026-06-17: Module Entrypoint Coverage

### Completed

- Added a design note and implementation plan for direct runner module
  entrypoint coverage.
- Added direct tests for `automation_runner.__main__` delegation.
- Added a tiny `run()` wrapper so module-entrypoint behavior can be tested
  in-process.
- Kept existing subprocess coverage for `python -m automation_runner`.
- Kept all behavior inside `automation_runner`; `automation_core` remains
  untouched.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_module_entrypoint.py --no-cov -q
```

Initial result:

```text
1 failed, 2 passed
AttributeError: module 'automation_runner.__main__' has no attribute 'run'
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_module_entrypoint.py --no-cov -q
```

Result:

```text
3 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
217 passed
Total coverage: 95.65%
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

- module entrypoint behavior remains in `automation_runner`.
- `automation_core` remains untouched.
- the new direct tests cover the wrapper delegation and script exit code.
- the existing subprocess smoke test still proves `python -m automation_runner`
  executes through the package entrypoint.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Version CLI

### Completed

- Added a design note and implementation plan for the runner version command.
- Added `automation-runner --version`.
- Added `python -m automation_runner --version` coverage through the existing
  module entrypoint path.
- Reused `automation_core.__version__` as the existing package version source.
- Kept report `schema_version` unchanged.
- Documented the version command in `README.md`.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_prints_runner_version tests/runner/test_module_entrypoint.py::test_runner_module_entrypoint_prints_version --no-cov -q
```

Initial result:

```text
2 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_prints_runner_version tests/runner/test_module_entrypoint.py::test_runner_module_entrypoint_prints_version --no-cov -q
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
219 passed
Total coverage: 95.90%
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

- version display stays in `automation_runner.cli`.
- `automation_core` is only used as the existing version source.
- runner report `schema_version` remains unchanged.
- direct CLI and module-entrypoint tests cover both supported invocation paths.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Param Validation

### Completed

- Added a design note and implementation plan for runner `--param` validation.
- Added a regression test proving invalid `--param` syntax is rejected for
  built-in workflows before any session is created.
- Moved runner parameter parsing to the shared `run` command path so custom and
  built-in workflows use the same CLI validation boundary.
- Kept parsed custom parameters available only through custom workflow
  `WorkflowOptions.parameters`.
- Left `automation_core` untouched and business-agnostic.
- Documented that `--param KEY=VALUE` syntax is validated before execution even
  when a selected workflow does not consume custom parameters.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_for_builtin_workflow --no-cov -q
```

Initial result:

```text
1 failed
assert 0 == 2
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_before_loading_factory --no-cov -q
```

Result:

```text
2 passed
```

Runner CLI test suite:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
```

Result:

```text
41 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
220 passed
Total coverage: 95.88%
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

- parameter validation remains in `automation_runner.cli`.
- `automation_core` remains untouched.
- built-in workflows still ignore custom parameters after syntax validation.
- custom workflows still receive parsed parameters through `WorkflowOptions`.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Workflow Factory Selection

### Completed

- Added a design note and implementation plan for workflow source selection.
- Added regression coverage for explicit `workflow + --workflow-factory`
  conflicts.
- Added coverage proving a positional workflow name overrides a
  config-provided workflow factory, matching the documented CLI precedence
  rule.
- Added `_resolve_workflow_selection(...)` in `automation_runner.cli` to keep
  selection validation in the runner layer.
- Documented the workflow source rule in `README.md` and
  `docs/adding-a-workflow.md`.
- Left `automation_core` untouched and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_workflow_name_with_explicit_workflow_factory tests/runner/test_cli.py::test_cli_workflow_name_overrides_config_workflow_factory --no-cov -q
```

Initial result:

```text
2 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_workflow_name_with_explicit_workflow_factory tests/runner/test_cli.py::test_cli_workflow_name_overrides_config_workflow_factory --no-cov -q
```

Result:

```text
2 passed
```

Runner CLI test suite:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
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
222 passed
Total coverage: 95.96%
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

- workflow source selection remains in `automation_runner.cli`.
- explicit built-in/custom workflow conflicts fail before execution.
- CLI positional workflows override config-provided workflow factories.
- `automation_core` remains untouched.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Report File Write Failure Handling

### Completed

- Added a design note and implementation plan for clean report-file write
  failure handling.
- Added a regression test covering a blocked report-file parent path so the CLI
  now fails cleanly instead of surfacing an unhandled filesystem traceback.
- Split JSON report payload, report-file writing, and stdout emission so the
  report file is written before stdout while filesystem errors stay scoped to
  the report-file path.
- Kept report-file/stdout parity intact for successful runs and for failure
  reports generated from workflow or session errors.
- Documented the report-file failure contract in `docs/adding-a-workflow.md`.
- Left `automation_core` untouched and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_handles_report_file_write_failure_without_partial_stdout --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_handles_report_file_write_failure_without_partial_stdout --no-cov -q
```

Result:

```text
1 passed
```

Report-file regression tests:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_can_write_json_report_to_file tests/runner/test_cli.py::test_cli_can_write_report_file_when_json_comes_from_config tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_fails tests/runner/test_cli.py::test_cli_emits_json_report_when_session_factory_fails tests/runner/test_cli.py::test_cli_creates_report_file_parent_directories tests/runner/test_cli.py::test_cli_rejects_report_file_without_json --no-cov -q
```

Result:

```text
6 passed
```

Runner CLI test suite:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py --no-cov -q
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
223 passed
Total coverage: 96.00%
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

- report-file write failures return a clean CLI error with no partial JSON
  stdout.
- successful report-file output remains byte-for-byte aligned with stdout.
- filesystem error handling is scoped to report-file writing, not stdout.
- `automation_core` remains untouched.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Artifact Path Component Sanitization

### Completed

- Added a design note and implementation plan for artifact path component
  sanitization.
- Added regression coverage proving `run_id` and `artifact_type` cannot escape
  the artifact root through path-like input.
- Added invalid component coverage for `run_id`, `artifact_type`, and artifact
  names.
- Replaced the name-only sanitizer in `ArtifactStore` with a shared path
  component sanitizer used for `run_id`, `artifact_type`, and artifact names.
- Documented that all artifact path components are reduced to one safe segment
  and spaces are normalized to `_`.
- Kept Selenium/Appium adapters delegating artifact paths to `ArtifactStore`.
- Kept `automation_core` business-agnostic; the change only hardens a generic
  storage contract.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/artifacts/test_store.py --no-cov -q
```

Initial result:

```text
3 failed, 4 passed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/artifacts/test_store.py --no-cov -q
```

Result:

```text
7 passed
```

Adapter and driver artifact regression tests:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py tests/drivers/test_contracts.py --no-cov -q
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
226 passed
Total coverage: 96.01%
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

- artifact path sanitization lives in `automation_core.artifacts`.
- adapters keep using the shared store contract.
- path-like run IDs and artifact types no longer escape the artifact root.
- existing artifact record serialization and report paths remain unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Config String Validation

### Completed

- Added a design note and implementation plan for runner config string field
  validation.
- Added runner config coverage for non-string `factory`, `workflow_factory`,
  `url`, and `app_id` values.
- Added CLI coverage proving invalid config factories fail before live factory
  loading.
- Tightened `_optional_string(...)` in `automation_runner.config` so dictionary
  or file-backed config cannot silently coerce non-string values.
- Documented dictionary-backed runner config type expectations in `README.md`
  and `docs/adding-a-workflow.md`.
- Kept `automation_core.config` generic and unchanged.

### Verification

Focused red config run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py --no-cov -q
```

Initial result:

```text
4 failed, 6 passed
```

Focused red CLI boundary run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_non_string_config_factory_before_loading_factory --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py tests/runner/test_cli.py::test_cli_rejects_non_string_config_factory_before_loading_factory --no-cov -q
```

Result:

```text
11 passed
```

Runner regression tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
79 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
231 passed
Total coverage: 96.03%
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

- string-field validation lives in `automation_runner.config`.
- environment-backed config remains string-based and compatible.
- invalid dictionary-backed config fails before workflow or factory loading.
- `automation_core` remains unchanged and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Adapter Element Lookup Failure Handling

### Completed

- Added a design note and implementation plan for direct element lookup failure
  handling in adapters.
- Added Selenium coverage for `click` and `type_text` when driver element lookup
  raises.
- Added Appium coverage for `tap` and `type_text` when driver element lookup
  raises.
- Updated Selenium and Appium `_resolve_element(...)` helpers so direct element
  actions return failed `ActionResult` values instead of surfacing lookup
  exceptions.
- Preserved `wait_for_element` retry behavior by letting that path continue to
  route lookup exceptions through `retry_until(...)`.
- Documented the adapter contract in `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Initial result:

```text
4 failed, 51 passed
```

Message-semantics red run before final adjustment:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py::test_selenium_session_click_reports_missing_lookup_failure tests/adapters/selenium/test_session.py::test_selenium_session_type_text_reports_missing_lookup_failure tests/adapters/appium/test_session.py::test_appium_session_tap_reports_missing_lookup_failure tests/adapters/appium/test_session.py::test_appium_session_type_text_reports_missing_lookup_failure --no-cov -q
```

Result:

```text
4 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Result:

```text
55 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
235 passed
Total coverage: 96.03%
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

- lookup failure handling remains in concrete adapters.
- direct element actions now return failed `ActionResult` values on lookup
  failure.
- `wait_for_element` still uses retry semantics and timeout messaging.
- no security-sensitive access-control logic was changed; the review risk flag
  was triggered by adapter terminology rather than an auth path.
- `automation_core` remains unchanged.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Param Key Validation

### Completed

- Added a design note and implementation plan for rejecting whitespace-only
  CLI parameter keys.
- Added focused CLI regression tests for blank-key and tab-only-key `--param`
  values.
- Tightened `_parse_parameters(...)` in `automation_runner.cli` so blank keys
  are rejected before any workflow executes.
- Documented the non-whitespace key requirement in `README.md` and
  `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'blank_workflow_param_key or tab_only_workflow_param_key' --no-cov -q
```

Initial result:

```text
2 failed
```

Focused green run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'blank_workflow_param_key or tab_only_workflow_param_key or passes_context_and_options_to_custom_workflow_factory or param_overrides_config_parameters' --no-cov -q
```

Result:

```text
4 passed, 46 deselected
```

Runner regression tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
87 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
280 passed
Total coverage: 96.29%
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

- `automation_runner.cli` now rejects blank keys before workflow execution.
- valid keys, empty values, and values containing `=` remain unchanged.
- built-in and custom workflows still receive the same parameter shape for
  valid inputs.
- `automation_core` remains unchanged and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Config Param Key Validation

### Completed

- Added a design note and implementation plan for rejecting whitespace-only
  config-backed workflow parameter keys.
- Added focused runner-config regression tests for blank keys in dictionary and
  JSON-string parameter inputs.
- Tightened `_optional_parameters(...)` in `automation_runner.config` so blank
  keys are rejected before workflow construction.
- Documented the non-whitespace key requirement for config-backed workflow
  parameters in `README.md` and `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_parameter_key' --no-cov -q
```

Initial result:

```text
1 failed, 11 deselected
```

Focused green config run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_parameter_key or reads_json_parameters or rejects_non_string_parameter_values' --no-cov -q
```

Result:

```text
3 passed, 9 deselected
```

Focused CLI compatibility run:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'config_parameters or blank_workflow_param_key or tab_only_workflow_param_key' --no-cov -q
```

Result:

```text
4 passed, 46 deselected
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
282 passed
Total coverage: 96.29%
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

- `automation_runner.config` now rejects blank parameter keys from dictionary
  and environment-backed JSON config sources.
- valid keys, empty string values, and CLI-over-config override behavior remain
  unchanged.
- config-backed and CLI-backed workflow parameter boundaries are now aligned.
- `automation_core` remains unchanged and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.

## 2026-06-17: Runner Config Blank String Validation

### Completed

- Added a design note and implementation plan for rejecting whitespace-only
  config strings for `factory`, `workflow_factory`, `url`, and `app_id`.
- Added focused runner-config regression tests covering blank strings across all
  four runtime string fields.
- Added a CLI regression test proving a blank config `url` now fails during
  config loading instead of being treated as a valid workflow input.
- Tightened `_optional_string(...)` in `automation_runner.config` so blank
  strings are rejected before runner execution proceeds.
- Documented the non-whitespace requirement for config-backed runtime strings in
  `README.md` and `docs/adding-a-workflow.md`.
- Left `automation_core` unchanged and business-agnostic.

### Verification

Focused red config run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_string_fields' --no-cov -q
```

Initial result:

```text
4 failed, 12 deselected
```

Focused red CLI run before implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_config_url_for_builtin_workflow --no-cov -q
```

Initial result:

```text
1 failed
```

Focused green config run after implementation:

```bash
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_string_fields or reads_runtime_values or rejects_non_string_fields' --no-cov -q
```

Result:

```text
9 passed, 7 deselected
```

Focused green CLI compatibility run:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_config_url_for_builtin_workflow tests/runner/test_cli.py -k 'config_parameters or blank_config_url_for_builtin_workflow' --no-cov -q
```

Result:

```text
3 passed, 48 deselected
```

Runner regression tests:

```bash
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Result:

```text
94 passed
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
287 passed
Total coverage: 96.29%
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

- `automation_runner.config` now rejects blank runtime strings for config-backed
  `factory`, `workflow_factory`, `url`, and `app_id` values.
- valid non-empty strings, config parameter parsing, and CLI overrides remain
  unchanged.
- config-backed runtime validation now matches the CLI expectation that these
  fields carry meaningful values.
- `automation_core` remains unchanged and business-agnostic.

### Next Phase

Stage, commit, and push the finished slice.
