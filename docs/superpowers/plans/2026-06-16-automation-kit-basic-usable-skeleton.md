# Automation Kit Basic Usable Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `automation-kit` to a basic usable state where a developer can define a business-specific automation workflow, run it through a deterministic CLI, receive structured status, and collect debug artifacts without putting business logic into `automation_core`.

**Architecture:** Keep `automation_core` pure and business-agnostic. Put concrete framework glue in `adapters`, runnable orchestration in `automation_runner`, and domain samples in `examples`. Each phase must leave the repository runnable with default tests that do not require Chrome, Appium, ADB, Android devices, or network access.

**Tech Stack:** Python 3.8+, Poetry, pytest, pytest-cov, dataclasses, typing protocols, standard-library config sources, optional Selenium/Appium adapter shells.

---

## Current Baseline

Status update on 2026-06-16:

- The basic usable skeleton phases below have been implemented and verified.
- `EnvConfigSource` is implemented and exported.
- The runner supports dry execution by default, live execution behind
  `--live`, JSON stdout reports, and `--report-file` output.
- Reports include run metadata, actions, artifacts, structured events, and
  failure summaries.
- Selenium/Appium adapters are dependency-injectable and business-free.
- `README.md` and `docs/adding-a-workflow.md` document extension boundaries
  and runnable commands.
- The remaining work after this plan should build the next roadmap slice on
  top of the verified skeleton instead of redoing these phases.

Repository:

```text
/Users/mango/project/codex/automation-kit/
```

Already established:

- `automation_core.retries`: bounded retry policy and `retry_until`.
- `automation_core.tasks`: task lifecycle primitives.
- `automation_core.events`: structured runtime events.
- `automation_core.state`: generic run state.
- `automation_core.drivers`: framework-neutral driver contracts.
- `automation_core.artifacts`: generic artifact records and storage.
- `adapters.selenium` and `adapters.appium`: thin adapter shells.
- `examples.damai_web` and `examples.damai_android`: smoke workflow examples.
- `automation_runner`: minimal CLI runner with JSON output and report file support.
- `automation_core.config`: generic dictionary and environment config source
  primitives.

## Target Basic Usable State

A basic usable `automation-kit` means:

- Core modules are importable and tested.
- Config can come from dictionaries and environment variables.
- A workflow can be loaded by `module:object` factory and executed through CLI.
- CLI defaults to dry/non-live behavior and requires an explicit live flag for live systems.
- Runner emits structured events and JSON reports.
- Reports can be written to disk through `--report-file`.
- Adapter and example packages demonstrate boundaries without moving business logic into core.
- Project docs explain how to add a new website or Android app automation workflow.

## Phase 0: Repository And Boundary Baseline

### Outcome

The new repository remains clean, documented, and separate from `ticket-purchase`.

### Files

- Verify: `/Users/mango/project/codex/automation-kit/README.md`
- Verify: `/Users/mango/project/codex/automation-kit/docs/development-system.md`
- Verify: `/Users/mango/project/codex/automation-kit/docs/technical-landscape.md`
- Verify: `/Users/mango/project/codex/automation-kit/pyproject.toml`
- Verify: `/Users/mango/project/codex/automation-kit/tests/structure/test_boundaries.py`

### Steps

- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
git status --short --branch
```

Expected: only intentional in-progress files are shown.

- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/structure/test_boundaries.py -q
```

Expected: boundary tests pass and prove `automation_core` has no business or concrete driver coupling.

- [ ] If docs mention old repository-only implementation paths, update them to point at `automation-kit`.

### Acceptance

- Repository purpose is clear.
- `automation_core` remains business-agnostic.
- No Damai/Dianping selectors, URLs, package names, or order/review flows appear in core.

## Phase 1: Finish Generic Config Sources

### Outcome

Core config can read typed values from in-memory dictionaries and environment mappings without depending on business fields or file formats.

### Files

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/config/sources.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/config/__init__.py`
- Verify: `/Users/mango/project/codex/automation-kit/tests/config/test_sources.py`
- Verify: `/Users/mango/project/codex/automation-kit/tests/config/test_value.py`
- Verify: `/Users/mango/project/codex/automation-kit/tests/config/test_env.py`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Run the focused config tests before implementation:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/config -q
```

Expected: `EnvConfigSource` import or behavior fails until implementation is added.

- [ ] Implement `EnvConfigSource` in `automation_core/config/sources.py`.

Required behavior:

- Accept a mapping such as `os.environ` or a plain dictionary.
- Accept an optional prefix such as `AUTOMATION_`.
- Resolve logical key `timeout` to environment key `AUTOMATION_TIMEOUT`.
- Preserve returned `ConfigValue.key` as the logical key.
- Support `require(key, expected_type=...)`.
- Support `get(key, default=..., expected_type=...)`.
- Reuse the existing type validation path.
- Copy the input mapping on construction so later external mutations do not change source behavior.

- [ ] Export `EnvConfigSource` from `automation_core.config`.
- [ ] Add one immutability test for env mappings.
- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/config -q
.venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] Update `docs/development-log.md` with the config phase summary, verification command, and result.

### Acceptance

- Config sources stay standard-library only.
- Core config APIs contain generic names only.
- No file parsing or third-party config library is introduced.

## Phase 2: Stabilize Runner Contract

### Outcome

The runner is the supported way to execute a workflow factory in dry mode or live mode, with predictable JSON/report output.

### Files

- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_runner/runner.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_runner.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Confirm current runner behavior:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner -q
```

Expected: runner tests pass before any changes.

- [ ] Ensure `automation_runner run` requires `--live` before any workflow touches live systems.
- [ ] Ensure `--factory module:object` is required for live workflow execution.
- [ ] Ensure `--json` prints a stable JSON report to stdout.
- [ ] Ensure `--report-file path.json` writes the same stable report structure to disk.
- [ ] Add tests for invalid factory strings and missing factory objects if not already covered.
- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner -q
.venv/bin/python -m pytest -q
```

Expected: all tests pass.

### Acceptance

- Runner behavior is deterministic by default.
- Live execution remains opt-in.
- Reports stay in the runner layer, not `automation_core`.

## Phase 3: Define Minimal Workflow Authoring API

### Outcome

A developer can create a small Python workflow factory that uses core primitives and can be executed by the runner.

### Files

- Create/Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/examples/damai_web/smoke.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/examples/damai_android/smoke.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_android/test_smoke_workflow.py`
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Keep examples dry and dependency-free by default.
- [ ] Define a tiny workflow object shape for examples:

```python
class Workflow:
    def run(self):
        ...
```

- [ ] Ensure example workflow factories return runnable workflow objects.
- [ ] Add tests that instantiate the examples without importing Selenium, Appium, or target business code.
- [ ] Add README instructions for running a dry example:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m automation_runner run --factory examples.damai_web.smoke:create_workflow --json
```

- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/examples -q
.venv/bin/python -m pytest -q
```

Expected: examples prove workflow shape without requiring live browser/device access.

### Acceptance

- Examples show composition style.
- Examples do not become a second core.
- Business selectors and target package names remain outside core.

## Phase 4: Keep Adapter Shells Framework-Aware But Business-Free

### Outcome

Selenium and Appium adapter packages define the location for framework integration without requiring those dependencies during default tests.

### Files

- Verify/Modify: `/Users/mango/project/codex/automation-kit/adapters/selenium/session.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/selenium/test_session.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Confirm adapter tests do not import real Selenium/Appium packages unless marked integration.
- [ ] Keep concrete import points lazy or injectable so default tests can run with pure fakes.
- [ ] Ensure adapters implement `automation_core.drivers.DriverSession` behavior through small wrapper classes.
- [ ] Add tests for startup/shutdown behavior using fake framework objects.
- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters -q
.venv/bin/python -m pytest -q
```

Expected: adapter shell tests pass without live systems.

### Acceptance

- Adapter code may know Selenium/Appium framework concepts.
- Adapter code must not know Damai/Dianping business concepts.
- Default tests remain offline and deterministic.

## Phase 5: Artifact And Event Integration In Runner

### Outcome

Runner output includes enough structured context to debug dry workflows and later live workflows.

### Files

- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_runner/runner.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_core/events/models.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/automation_core/artifacts/store.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`
- Verify/Modify: `/Users/mango/project/codex/automation-kit/tests/artifacts/test_store.py`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Ensure every runner report includes:
  - run ID
  - status
  - start/end timestamps or elapsed time
  - workflow factory reference
  - live mode flag
  - event list
  - artifact list
  - error summary when failed
- [ ] Keep report serialization stable with explicit dictionaries.
- [ ] Add tests for success, failure, and artifact metadata in reports.
- [ ] Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner tests/artifacts tests/events -q
.venv/bin/python -m pytest -q
```

Expected: reports are stable and artifact-aware.

### Acceptance

- Debug output is machine-readable.
- Report file output is deterministic.
- Artifact metadata remains generic.

## Phase 6: Documentation For Extension

### Outcome

A developer can read the docs and add a new web or Android automation adapter without guessing the boundaries.

### Files

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Create: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_web/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_android/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Document the package boundary:
  - `automation_core`: generic primitives only.
  - `automation_runner`: execution and report CLI.
  - `adapters`: framework integration.
  - `examples`: business-specific composition samples.
- [ ] Document how to create a new workflow factory.
- [ ] Document dry-run and live-run commands.
- [ ] Document the no-live-default test policy.
- [ ] Document where screenshots, page dumps, UI dumps, and JSON reports should be attached.

### Acceptance

- Docs are enough for a developer to create the next adapter shell.
- Docs explicitly forbid business logic in `automation_core`.
- Docs include runnable commands.

## Phase 7: Review, Verification, And Merge Gate

### Outcome

The project reaches a verified basic usable state.

### Files

- Verify: all changed files.
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

### Steps

- [ ] Run full tests:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
```

Expected: all tests pass and coverage remains above the configured threshold.

- [ ] Run production review setup scripts from the local skill:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and any actionable findings are fixed or recorded.

- [ ] Manually verify these invariants:
  - `automation_core` imports no `adapters`, `examples`, Selenium, Appium, browser, Android, Damai, or Dianping symbols.
  - Default tests do not require network, Chrome, Appium, ADB, or a device.
  - Live execution requires an explicit `--live` flag.
  - Reports and artifacts are generic and serializable.

- [ ] Update `docs/development-log.md` with final verification results.

### Acceptance

- Full test suite passes.
- Production review has no unresolved P0/P1/P2 issues.
- `README.md` contains the first-run commands.
- Basic dry workflow execution is available from CLI.

## Commit Plan

Use small commits so each phase is reviewable:

```bash
git add automation_core/config tests/config docs/development-log.md
git commit -m "feat: add environment config source"

git add automation_runner tests/runner docs/development-log.md
git commit -m "feat: stabilize workflow runner contract"

git add examples tests/examples README.md docs/development-log.md
git commit -m "docs: document dry workflow authoring"

git add adapters tests/adapters docs/development-log.md
git commit -m "feat: keep adapter shells dependency-injectable"

git add automation_runner automation_core tests docs/development-log.md
git commit -m "feat: include artifacts in runner reports"

git add README.md docs examples docs/development-log.md
git commit -m "docs: add workflow extension guide"
```

## Definition Of Done

- `automation-kit` can be installed and tested locally.
- `automation_core` is generic, tested, and reusable.
- `automation_runner` can run a dry workflow by factory path.
- JSON output and report files work.
- Adapters and examples demonstrate extension points without core pollution.
- Documentation explains how to build the next website or Android app workflow.
- Full verification and production review pass.
