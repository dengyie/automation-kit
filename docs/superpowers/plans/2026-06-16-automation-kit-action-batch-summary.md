# Action Batch Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return an explicit summary from `ActionExecutor.run_batch(...)`.

**Architecture:** Add an `ActionBatchResult` dataclass to `automation_core.actions` and keep action execution business-agnostic. Preserve individual action execution behavior while making batch-level status and skipped actions explicit.

**Tech Stack:** Python dataclasses, typing, pytest.

---

## Task 1: Add Batch Summary Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/actions/test_action_models.py`

- [ ] **Step 1: Write failing tests**

Add tests for:

- successful batch exposes `success=True`, executed `results`, and empty
  `skipped`.
- stop-on-failure exposes failed `success=False` and skipped remaining actions.
- continue-after-failure exposes no skipped actions.
- empty batch returns `success=False`, empty `results`, and empty `skipped`.
- `ActionBatchResult.to_dict()` serializes executed results and skipped action
  requests.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/actions/test_action_models.py --no-cov -q
```

Expected: tests fail because `ActionBatchResult` does not exist and
`run_batch(...)` returns a list.

## Task 2: Implement Batch Summary

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/actions/models.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/actions/__init__.py`

- [ ] **Step 1: Add `ActionBatchResult`**

Add a frozen dataclass with `results`, `skipped`, `success`, and `to_dict()`.

- [ ] **Step 2: Update `run_batch(...)`**

Return `ActionBatchResult` and populate skipped actions when execution stops
early.

- [ ] **Step 3: Run green verification**

```bash
.venv/bin/python -m pytest tests/actions/test_action_models.py --no-cov -q
```

Expected: action tests pass.

## Task 3: Docs, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document batch result semantics**

Explain that batch results distinguish executed actions from skipped actions.

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
git add automation_core tests docs
git commit -m "feat: add action batch summaries"
git push origin main
```
