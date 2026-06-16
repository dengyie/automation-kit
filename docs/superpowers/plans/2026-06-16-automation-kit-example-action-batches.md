# Example Action Batches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move built-in smoke workflows onto `ActionExecutor.run_batch(...)`.

**Architecture:** Keep examples as the integration layer that composes core action primitives with adapter sessions. Return the existing flat action list for report compatibility, and additionally return `batch_result` for batch-level observability.

**Tech Stack:** Python dataclasses, pytest, existing fake sessions.

---

## Task 1: Add Failing Example And CLI Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_android/test_smoke_workflow.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Write failing tests**

Add assertions that web and Android smoke workflows return a non-`None`
`batch_result` whose results match the existing action list.

Add CLI JSON assertions that built-in dry workflows include `action_batch`.

- [x] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/examples tests/runner/test_cli.py --no-cov -q
```

Expected: tests fail because built-in workflows still do not return
`batch_result`.

## Task 2: Implement Example Batch Execution

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_web/smoke.py`
- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_android/smoke.py`

- [x] **Step 1: Use ActionExecutor in web smoke**

Create an `ActionBatch` with one `ActionRequest(name="open", parameters={"url": url})`.
Run it with `ActionExecutor(session).run_batch(...)`.

- [x] **Step 2: Use ActionExecutor in Android smoke**

Create an `ActionBatch` with one
`ActionRequest(name="launch_app", parameters={"app_id": app_id})`.
Run it with `ActionExecutor(session).run_batch(...)`.

- [x] **Step 3: Return existing actions plus batch_result**

Set `actions=batch_result.results` and `batch_result=batch_result`.

- [x] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/examples tests/runner/test_cli.py --no-cov -q
```

Expected: focused tests pass.

## Task 3: Docs, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document example batch use**

Document that built-in smoke workflows now use action batches and report
`action_batch`.

- [x] **Step 2: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Commit and push**

```bash
git add examples tests docs
git commit -m "feat: use action batches in examples"
git push origin main
```
