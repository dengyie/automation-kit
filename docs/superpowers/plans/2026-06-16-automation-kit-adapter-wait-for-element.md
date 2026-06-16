# Adapter Wait For Element Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an adapter-layer `wait_for_element` action for Selenium and Appium sessions.

**Architecture:** Keep the shared driver contract unchanged. Implement the waiting primitive inside each concrete adapter session and reuse `automation_core.retries.retry_until` for polling. Default tests must stay offline, and `automation_core` must remain business-agnostic.

**Tech Stack:** Python dataclasses and protocols already in the repo, `automation_core.retries`, pytest, fake Selenium/Appium-style drivers.

---

### Task 1: Selenium Wait Alias

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/selenium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/selenium/session.py`

- [x] **Step 1: Write the failing tests**

Add a fake driver that raises on the first lookup and returns an element on the
next lookup. Add tests for:

- `wait_for_element(selector=...)` retries until the element appears.
- `wait_for_element(selector=...)` returns a failed `ActionResult` when the
  lookup keeps failing.
- missing `selector` returns a failed `ActionResult`.

- [x] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
```

Expected: the new wait tests fail because the alias does not exist yet.

- [x] **Step 3: Implement the Selenium wait alias**

Handle `wait_for_element` inside `SeleniumSession.execute_action(...)` before
the raw driver-method fallback. Reuse `retry_until` with a timeout-based retry
policy and preserve the existing `click`, `type_text`, and `open` aliases.

- [x] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
```

Expected: Selenium adapter tests pass.

### Task 2: Appium Wait Alias

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`

- [x] **Step 1: Write the failing tests**

Add a fake mobile driver that raises on the first lookup and returns an element
on the next lookup. Add tests for:

- `wait_for_element(selector=...)` retries until the element appears.
- `wait_for_element(selector=...)` returns a failed `ActionResult` when the
  lookup keeps failing.
- missing `selector` returns a failed `ActionResult`.

- [x] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: the new wait tests fail because the alias does not exist yet.

- [x] **Step 3: Implement the Appium wait alias**

Handle `wait_for_element` inside `AppiumSession.execute_action(...)` before the
mobile-script and raw driver-method fallback paths. Reuse `retry_until` with a
timeout-based retry policy and preserve the existing `tap`, `type_text`, and
`launch_app` aliases.

- [x] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: Appium adapter tests pass.

### Task 3: Docs, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document the wait alias**

Add the supported `wait_for_element` action for both adapters and note that raw
driver methods remain available as an escape hatch.

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
git add adapters tests docs
git commit -m "feat: add adapter wait aliases"
git push origin main
```
