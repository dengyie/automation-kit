# Retry Snapshot Event Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small event-layer helper that converts `RetryAttemptSnapshot` objects into `RetryAttemptEvent` records.

**Architecture:** Keep the dependency one-way from `automation_core.events` to `automation_core.retries`. The retry package must remain unaware of events, reports, adapters, and business workflows. Preserve the existing `RetryAttemptEvent` payload shape in this slice.

**Tech Stack:** Python dataclasses, existing `automation_core.events`, existing `automation_core.retries`, pytest.

---

### Task 1: Add Failing Event Bridge Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/events/test_events.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/structure/test_boundaries.py`

- [x] **Step 1: Add event helper test**

Add a test importing `RetryAttemptSnapshot` and
`retry_attempt_event_from_snapshot`. Create a snapshot with attempt `3` and
elapsed `1.25`, then assert the returned event has task name, task id, attempt,
elapsed, and `retry.attempt` envelope type.

- [x] **Step 2: Add retry package boundary test**

Add a structure test proving `automation_core/retries/policy.py` does not
contain `automation_core.events`.

- [x] **Step 3: Run red verification**

```bash
.venv/bin/python -m pytest tests/events/test_events.py tests/structure/test_boundaries.py --no-cov -q
```

Expected: fail because `retry_attempt_event_from_snapshot` does not exist.

### Task 2: Implement The Event Bridge

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/events/models.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/events/__init__.py`

- [x] **Step 1: Add helper function**

Add `retry_attempt_event_from_snapshot(task_name, task_id, snapshot)` to
`automation_core.events.models`. It should return:

```python
RetryAttemptEvent(
    task_name=task_name,
    task_id=task_id,
    attempt=snapshot.attempt,
    elapsed=snapshot.elapsed,
)
```

- [x] **Step 2: Export helper**

Add `retry_attempt_event_from_snapshot` to `automation_core.events.__all__`.

- [x] **Step 3: Run green verification**

```bash
.venv/bin/python -m pytest tests/events/test_events.py tests/structure/test_boundaries.py --no-cov -q
```

Expected: focused tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-system.md`

- [x] **Step 1: Document the event bridge**

Mention that event helpers may adapt retry snapshots into task-scoped events,
while retry primitives stay independent from events.

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
git commit -m "feat: bridge retry snapshots to events"
git push origin main
```
