# Runner Report Schema Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stable top-level `schema_version` field to runner JSON reports.

**Architecture:** Keep schema versioning in `automation_runner.reports` as report-contract metadata. The value is an additive string field and does not change `automation_core`, workflow result models, or event envelopes.

**Tech Stack:** Python dataclasses, pytest, existing runner report and CLI tests.

---

## Task 1: Add Failing Report Schema Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Assert schema version in report unit test**

In `test_build_report_serializes_safe_workflow_summary`, add:

```python
assert report["schema_version"] == "1"
```

- [x] **Step 2: Assert schema version in CLI JSON test**

In `test_cli_runs_dry_workflow_without_live_flag`, add:

```python
assert report["schema_version"] == "1"
```

- [x] **Step 3: Run red focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_safe_workflow_summary tests/runner/test_cli.py::test_cli_runs_dry_workflow_without_live_flag --no-cov -q
```

Expected: fail because reports do not include `schema_version`.

## Task 2: Add Schema Version To RunnerReport

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`

- [x] **Step 1: Add `schema_version` field**

Add a top-level dataclass field:

```python
schema_version: str
```

Set it in `build_report(...)`:

```python
schema_version="1",
```

- [x] **Step 2: Run green focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py::test_build_report_serializes_safe_workflow_summary tests/runner/test_cli.py::test_cli_runs_dry_workflow_without_live_flag --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document report schema version**

Add `schema_version` to the report field list and explain that it is a
top-level runner report contract version.

- [x] **Step 2: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and diff check reports no whitespace errors.

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and no unresolved P0/P1/P2 findings remain.

- [ ] **Step 4: Commit and push**

```bash
git add automation_runner tests docs
git commit -m "feat: version runner reports"
git push origin main
```
