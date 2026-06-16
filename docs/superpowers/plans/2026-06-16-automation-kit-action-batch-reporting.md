# Action Batch Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface action batch summaries in runner reports.

**Architecture:** Keep the existing flat `actions` report field, and add a separate summary field for batch execution only when workflows provide one. Reuse `ActionBatchResult.to_dict()` so report serialization stays explicit and stable.

**Tech Stack:** Python dataclasses, pytest, existing runner report code.

---

## Task 1: Add Failing Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`

- [ ] **Step 1: Write the failing tests**

Add a test where `ExampleWorkflowResult` includes an `ActionBatchResult` and
`build_report(...)` includes a serialized `action_batch` field.

Add a CLI test that expects the same field in JSON output.

Add a workflow test that returns a batch summary from a fake run function.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py tests/runner/test_cli.py tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: tests fail because `batch_result` and `action_batch` are not yet
implemented.

## Task 2: Implement Batch Reporting

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/workflows.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/fixtures.py`

- [ ] **Step 1: Add batch_result to workflow results**

Extend `ExampleWorkflowResult` with an optional `batch_result`.

- [ ] **Step 2: Serialize action_batch in reports**

Add `action_batch` to `RunnerReport` and fill it from `batch_result.to_dict()`
when present.

- [ ] **Step 3: Update fixtures if needed**

Make the test fixture workflow return a batch summary so CLI report coverage is
real, not mocked away.

- [ ] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/runner/test_reports.py tests/runner/test_cli.py tests/examples/damai_web/test_smoke_workflow.py --no-cov -q
```

Expected: tests pass.

## Task 3: Docs, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document batch reporting**

Explain how batch summaries appear in runner reports.

- [ ] **Step 2: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Commit and push**

```bash
git add automation_runner examples tests docs
git commit -m "feat: report action batch summaries"
git push origin main
```
