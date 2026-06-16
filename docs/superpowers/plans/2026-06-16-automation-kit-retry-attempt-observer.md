# Retry Attempt Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional retry attempt observer callback to `retry_until(...)`.

**Architecture:** Keep retry observability in `automation_core.retries` as a generic runtime primitive. Expose immutable attempt snapshots from the retry package and let runner or workflow layers decide how to convert them into events or logs. Preserve the current `retry_until(...)` behavior for callers that do not pass a callback.

**Tech Stack:** Python dataclasses, standard-library typing, pytest, existing retry tests.

---

### Task 1: Add Retry Attempt Snapshot Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/retries/test_policy.py`

- [x] **Step 1: Write failing callback tests**

Add tests proving:

- a predicate-miss attempt calls `on_attempt` with `will_retry=True`.
- a retryable exception attempt records `exception` and `value=None`.
- a final success attempt calls `on_attempt` with `will_retry=False`.
- the snapshot type is importable from `automation_core.retries`.

- [x] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/retries/test_policy.py --no-cov -q
```

Expected: fail because `RetryAttemptSnapshot` and `on_attempt` do not exist.

### Task 2: Implement Retry Attempt Observer

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/retries/policy.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/retries/__init__.py`

- [x] **Step 1: Add `RetryAttemptSnapshot`**

Add a frozen dataclass with:

- `attempt: int`
- `elapsed: float`
- `value: Any`
- `exception: Optional[Exception]`
- `will_retry: bool`

- [x] **Step 2: Add optional `on_attempt` callback**

Add an optional callback argument to `retry_until(...)`. Build one snapshot
after each handled attempt, once `will_retry` is known, and call the callback
before returning or sleeping.

- [x] **Step 3: Export the snapshot type**

Add `RetryAttemptSnapshot` to `automation_core.retries.__all__`.

- [x] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/retries/test_policy.py --no-cov -q
```

Expected: retry tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-system.md`

- [x] **Step 1: Document retry observability**

Mention that retry behavior can expose attempt snapshots for higher-level
events/logs while keeping retry primitives independent from event models.

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
git add automation_core tests docs
git commit -m "feat: expose retry attempt snapshots"
git push origin main
```
