# Example Workflow Aliases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move built-in smoke examples onto the adapter action vocabulary.

**Architecture:** Keep examples business-specific but framework-light by using adapter aliases. Add only the Android `launch_app` alias needed to avoid teaching raw Appium method names in the first example path. Leave `automation_core` unchanged.

**Tech Stack:** Python, pytest, existing fake driver/session tests.

---

## Task 1: Update Example Expectations

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_web/test_smoke_workflow.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/examples/damai_android/test_smoke_workflow.py`

- [ ] **Step 1: Write failing tests**

Change the web example expectations from `get` to `open`. Change the Android
example expectations from `activate_app` to `launch_app`.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/examples --no-cov -q
```

Expected: tests fail because examples still call raw driver method names.

## Task 2: Add Appium Launch Alias

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`

- [ ] **Step 1: Write failing adapter test**

Add a test proving `launch_app(app_id=...)` calls the underlying
`activate_app(app_id)` driver method and reports a missing `app_id` as a failed
`ActionResult`.

- [ ] **Step 2: Run red verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: new launch alias tests fail because the alias is not implemented.

- [ ] **Step 3: Implement `launch_app`**

Handle `launch_app` before existing Appium mobile-script and raw driver-method
fallback logic.

- [ ] **Step 4: Run green verification**

```bash
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: Appium adapter tests pass.

## Task 3: Update Examples And Docs

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_web/smoke.py`
- Modify: `/Users/mango/project/codex/automation-kit/examples/damai_android/smoke.py`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Switch example action names**

Use `open` in the web example and `launch_app` in the Android example.

- [ ] **Step 2: Update docs**

Document `launch_app` as an Appium adapter alias and add a development-log
entry for this slice.

- [ ] **Step 3: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 4: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 5: Commit and push**

```bash
git add adapters examples tests docs
git commit -m "feat: use adapter aliases in examples"
git push origin main
```
