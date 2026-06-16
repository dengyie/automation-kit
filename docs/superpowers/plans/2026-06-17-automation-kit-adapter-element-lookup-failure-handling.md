# Adapter Element Lookup Failure Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Selenium and Appium direct element actions return failed `ActionResult` values when lookup fails, instead of surfacing unhandled driver exceptions.

**Architecture:** Keep the fix inside `adapters.selenium.session` and `adapters.appium.session`. Add a small lookup helper per adapter, reuse the existing missing-lookup support message, and leave `automation_core` unchanged.

**Tech Stack:** Python adapter sessions, fake drivers, pytest.

---

### Task 1: Add Failing Adapter Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/selenium/test_session.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`

- [ ] **Step 1: Add Selenium lookup-failure action tests**

Add these tests near the existing lookup tests:

```python
def test_selenium_session_click_reports_missing_lookup_failure():
    driver = FakeDriver(lookup_failures=1)
    session = SeleniumSession(driver=driver)

    result = session.execute_action("click", selector="#buy")

    assert result.success is False
    assert result.message == "element lookup failed: #buy"
    assert driver.lookups == [("css selector", "#buy")]


def test_selenium_session_type_text_reports_missing_lookup_failure():
    driver = FakeDriver(lookup_failures=1)
    session = SeleniumSession(driver=driver)

    result = session.execute_action("type_text", selector="#kw", text="concert")

    assert result.success is False
    assert result.message == "element lookup failed: #kw"
    assert driver.lookups == [("css selector", "#kw")]
```

- [ ] **Step 2: Add Appium lookup-failure action tests**

Add these tests near the existing lookup tests:

```python
def test_appium_session_tap_reports_missing_lookup_failure():
    driver = FakeMobileDriver(lookup_failures=1)
    session = AppiumSession(driver=driver)

    result = session.execute_action("tap", selector="buy")

    assert result.success is False
    assert result.message == "element lookup failed: buy"
    assert driver.lookups == [("accessibility id", "buy")]


def test_appium_session_type_text_reports_missing_lookup_failure():
    driver = FakeMobileDriver(lookup_failures=1)
    session = AppiumSession(driver=driver)

    result = session.execute_action("type_text", selector="buy", text="concert")

    assert result.success is False
    assert result.message == "element lookup failed: buy"
    assert driver.lookups == [("accessibility id", "buy")]
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Expected: the new lookup-failure action tests fail because direct element actions currently let lookup exceptions escape.

### Task 2: Implement Lookup Failure Handling

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/adapters/selenium/session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`

- [ ] **Step 1: Add adapter lookup helpers**

In `SeleniumSession`, add:

```python
    def _lookup_element(self, selector: str, by: Optional[str]) -> Tuple[Optional[Any], Optional[ActionResult]]:
        find_element = getattr(self.driver, "find_element", None)
        if not callable(find_element):
            return None, ActionResult(False, "driver does not support element lookup")
        try:
            return find_element(by or "css selector", selector), None
        except Exception:
            return None, ActionResult(False, f"timed out waiting for element: {selector}")
```

In `AppiumSession`, add:

```python
    def _lookup_element(self, selector: str, by: Optional[str]) -> Tuple[Optional[Any], Optional[ActionResult]]:
        find_element = getattr(self.driver, "find_element", None)
        if not callable(find_element):
            return None, ActionResult(False, "driver does not support element lookup")
        try:
            return find_element(by or "accessibility id", selector), None
        except Exception:
            return None, ActionResult(False, f"timed out waiting for element: {selector}")
```

- [ ] **Step 2: Use the helper in direct element actions**

Update `_click`, `_type_text`, and `_tap` to call the new helper and return the
lookup error before touching the element.

- [ ] **Step 3: Keep `wait_for_element` unchanged**

Leave the existing `retry_until(...)` logic in `_wait_for_element` untouched.

- [ ] **Step 4: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Expected: all adapter tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document direct-action lookup failures**

Add a short note near the adapter rules:

```markdown
Direct element actions return failed `ActionResult` values when lookup fails;
`wait_for_element` remains the retrying primitive for wait-style flows.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: full tests pass and `git diff --check` emits no output.

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify Python stack review context.

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Adapter Element Lookup Failure Handling` section to
`docs/development-log.md` with:

- red and green focused test results,
- full suite result,
- production review result,
- boundary note that `automation_core` remains unchanged.

- [ ] **Step 5: Commit and push**

Run:

```bash
git add adapters tests docs
git commit -m "fix: handle adapter lookup failures"
git push origin main
```
