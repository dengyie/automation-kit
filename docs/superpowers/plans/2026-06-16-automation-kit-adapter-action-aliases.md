# Adapter Action Aliases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small adapter-layer action vocabulary for common web and Android operations.

**Architecture:** Keep the shared `DriverSession.execute_action(...)` contract unchanged. Implement aliases inside concrete adapter sessions and leave raw driver-method fallback behavior intact. Do not import Selenium/Appium packages or add business-specific logic.

**Tech Stack:** Python dataclasses/protocols already in the repo, pytest, fake Selenium/Appium-like drivers.

---

## Task 1: Selenium Action Aliases

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/selenium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/selenium/session.py`

- [ ] **Step 1: Write failing tests**

Add fake element behavior and tests for:

- `open(url=...)` calls `driver.get(url)`.
- `click(selector=...)` finds an element and clicks it.
- `type_text(selector=..., text=...)` clears and sends keys.
- missing required alias parameters return failed `ActionResult` values.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
```

Expected: new alias tests fail because aliases are not implemented.

- [ ] **Step 3: Implement aliases**

Handle aliases inside `SeleniumSession.execute_action(...)` before the existing
raw driver-method fallback.

- [ ] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
```

Expected: Selenium adapter tests pass.

## Task 2: Appium Action Aliases

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`

- [ ] **Step 1: Write failing tests**

Add fake element behavior and tests for:

- `tap(x=..., y=...)` calls `execute_script("mobile: clickGesture", ...)`.
- `tap(selector=...)` finds an element and clicks it.
- `type_text(selector=..., text=...)` clears and sends keys.
- missing required alias parameters return failed `ActionResult` values.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: new alias tests fail because aliases are not implemented.

- [ ] **Step 3: Implement aliases**

Handle aliases inside `AppiumSession.execute_action(...)` before the existing
mobile-script and raw driver-method fallback paths.

- [ ] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: Appium adapter tests pass.

## Task 3: Docs, Verification, Review

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document adapter aliases**

Add the supported action aliases and note that raw driver methods remain an
adapter escape hatch.

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
git add adapters tests docs
git commit -m "feat: add adapter action aliases"
git push origin main
```
