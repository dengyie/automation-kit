# Adapter Action Execution Failure Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Selenium and Appium adapter actions return failed `ActionResult` values when underlying driver or element operations raise.

**Architecture:** Keep exception normalization in `adapters.selenium.session` and `adapters.appium.session` using a small per-adapter helper. Validate required inputs and resolve elements exactly as today, then wrap the actual driver or element operation so successful data and messages remain unchanged.

**Tech Stack:** Python adapter sessions, fake Selenium/Appium drivers, pytest.

---

### Task 1: Add Failing Selenium Adapter Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/selenium/test_session.py`

- [ ] **Step 1: Extend Selenium fakes with action failures**

Update `FakeDriver.__init__` and methods:

```python
class FakeDriver:
    def __init__(self, lookup_failures=0, failures=None):
        self.closed = False
        self.visited = []
        self.lookups = []
        self.lookup_failures = lookup_failures
        self.failures = failures or {}
        self.screenshots = []
        self.page_source = "<html />"
        self.element = FakeElement(failures=self.failures)

    def get(self, url):
        if "get" in self.failures:
            raise RuntimeError(self.failures["get"])
        self.visited.append(url)
        return "loaded"

    def refresh(self):
        if "refresh" in self.failures:
            raise RuntimeError(self.failures["refresh"])
        return "refreshed"
```

Update `FakeElement`:

```python
class FakeElement:
    def __init__(self, failures=None):
        self.clicked = False
        self.cleared = False
        self.keys = []
        self.failures = failures or {}

    def click(self):
        if "click" in self.failures:
            raise RuntimeError(self.failures["click"])
        self.clicked = True
        return "clicked"

    def clear(self):
        if "clear" in self.failures:
            raise RuntimeError(self.failures["clear"])
        self.cleared = True

    def send_keys(self, text):
        if "send_keys" in self.failures:
            raise RuntimeError(self.failures["send_keys"])
        self.keys.append(text)
        return "typed"
```

- [ ] **Step 2: Add Selenium execution-failure tests**

Add these tests near the existing Selenium alias tests:

```python
def test_selenium_session_open_reports_driver_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"get": "navigation failed"}))

    result = session.execute_action("open", url="https://example.test")

    assert result.success is False
    assert result.message == "open failed: navigation failed"


def test_selenium_session_click_reports_element_action_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"click": "click intercepted"}))

    result = session.execute_action("click", selector="#buy")

    assert result.success is False
    assert result.message == "click failed: click intercepted"


def test_selenium_session_type_text_reports_clear_failure():
    driver = FakeDriver(failures={"clear": "clear failed"})
    session = SeleniumSession(driver=driver)

    result = session.execute_action("type_text", selector="#kw", text="concert")

    assert result.success is False
    assert result.message == "type_text failed: clear failed"
    assert driver.element.keys == []


def test_selenium_session_type_text_reports_send_keys_failure():
    driver = FakeDriver(failures={"send_keys": "keyboard failed"})
    session = SeleniumSession(driver=driver)

    result = session.execute_action("type_text", selector="#kw", text="concert")

    assert result.success is False
    assert result.message == "type_text failed: keyboard failed"
    assert driver.element.cleared is True


def test_selenium_session_reports_raw_driver_action_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"refresh": "browser closed"}))

    result = session.execute_action("refresh")

    assert result.success is False
    assert result.message == "refresh failed: browser closed"
```

- [ ] **Step 3: Run Selenium red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py --no-cov -q
```

Expected: new tests fail because adapter execution exceptions still escape.

### Task 2: Add Failing Appium Adapter Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/adapters/appium/test_session.py`

- [ ] **Step 1: Extend Appium fakes with action failures**

Update `FakeMobileDriver.__init__` and methods:

```python
class FakeMobileDriver:
    def __init__(self, lookup_failures=0, failures=None):
        self.closed = False
        self.activated = []
        self.lookups = []
        self.lookup_failures = lookup_failures
        self.failures = failures or {}
        self.scripts = []
        self.screenshots = []
        self.page_source = "<hierarchy />"
        self.element = FakeMobileElement(failures=self.failures)

    def activate_app(self, app_id):
        if "activate_app" in self.failures:
            raise RuntimeError(self.failures["activate_app"])
        self.activated.append(app_id)
        return "activated"

    def execute_script(self, script, args):
        if "execute_script" in self.failures:
            raise RuntimeError(self.failures["execute_script"])
        self.scripts.append((script, args))
        return {"script": script, "args": args}
```

Update `FakeMobileElement`:

```python
class FakeMobileElement:
    def __init__(self, failures=None):
        self.clicked = False
        self.cleared = False
        self.keys = []
        self.failures = failures or {}

    def click(self):
        if "click" in self.failures:
            raise RuntimeError(self.failures["click"])
        self.clicked = True
        return "clicked"

    def clear(self):
        if "clear" in self.failures:
            raise RuntimeError(self.failures["clear"])
        self.cleared = True

    def send_keys(self, text):
        if "send_keys" in self.failures:
            raise RuntimeError(self.failures["send_keys"])
        self.keys.append(text)
        return "typed"
```

- [ ] **Step 2: Add Appium execution-failure tests**

Add these tests near the existing Appium alias tests:

```python
def test_appium_session_launch_app_reports_driver_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"activate_app": "app unavailable"})
    )

    result = session.execute_action("launch_app", app_id="example.app")

    assert result.success is False
    assert result.message == "launch_app failed: app unavailable"


def test_appium_session_coordinate_tap_reports_script_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"execute_script": "gesture failed"})
    )

    result = session.execute_action("tap", x=1, y=2)

    assert result.success is False
    assert result.message == "tap failed: gesture failed"


def test_appium_session_element_tap_reports_element_action_failure():
    session = AppiumSession(driver=FakeMobileDriver(failures={"click": "tap failed"}))

    result = session.execute_action("tap", selector="buy")

    assert result.success is False
    assert result.message == "tap failed: tap failed"


def test_appium_session_type_text_reports_clear_failure():
    driver = FakeMobileDriver(failures={"clear": "clear failed"})
    session = AppiumSession(driver=driver)

    result = session.execute_action("type_text", selector="search", text="concert")

    assert result.success is False
    assert result.message == "type_text failed: clear failed"
    assert driver.element.keys == []


def test_appium_session_type_text_reports_send_keys_failure():
    driver = FakeMobileDriver(failures={"send_keys": "keyboard failed"})
    session = AppiumSession(driver=driver)

    result = session.execute_action("type_text", selector="search", text="concert")

    assert result.success is False
    assert result.message == "type_text failed: keyboard failed"
    assert driver.element.cleared is True


def test_appium_session_reports_mobile_script_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"execute_script": "scroll failed"})
    )

    result = session.execute_action("mobile: scrollGesture", direction="down")

    assert result.success is False
    assert result.message == "mobile: scrollGesture failed: scroll failed"


def test_appium_session_reports_raw_driver_action_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"activate_app": "device offline"})
    )

    result = session.execute_action("activate_app", app_id="example.app")

    assert result.success is False
    assert result.message == "activate_app failed: device offline"
```

- [ ] **Step 3: Run Appium red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/appium/test_session.py --no-cov -q
```

Expected: new tests fail because adapter execution exceptions still escape.

### Task 3: Implement Execution Failure Handling

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/adapters/selenium/session.py`
- Modify: `/Users/mango/project/codex/automation-kit/adapters/appium/session.py`

- [ ] **Step 1: Add a Selenium action wrapper**

Add this helper inside `SeleniumSession`:

```python
    def _run_action(self, action_name: str, action: Callable[[], Any]) -> ActionResult:
        try:
            result = action()
        except Exception as exc:
            return ActionResult(False, f"{action_name} failed: {exc}")
        return ActionResult(success=True, message=action_name, data=result)
```

- [ ] **Step 2: Use the Selenium wrapper**

Wrap `driver.get(...)`, `element.click()`, optional `element.clear()` plus
`element.send_keys(...)`, and raw supported driver actions with `_run_action`.
Keep all parameter validation and lookup handling before the wrapper.

- [ ] **Step 3: Add an Appium action wrapper**

Add this helper inside `AppiumSession`:

```python
    def _run_action(self, action_name: str, action: Callable[[], Any]) -> ActionResult:
        try:
            result = action()
        except Exception as exc:
            return ActionResult(False, f"{action_name} failed: {exc}")
        return ActionResult(success=True, message=action_name, data=result)
```

- [ ] **Step 4: Use the Appium wrapper**

Wrap `activate_app(...)`, `execute_script(...)`, `element.click()`, optional
`element.clear()` plus `element.send_keys(...)`, `mobile:*` execution, and raw
supported driver actions with `_run_action`. Keep all parameter validation and
lookup handling before the wrapper.

- [ ] **Step 5: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py --no-cov -q
```

Expected: all adapter tests pass.

### Task 4: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document adapter execution failures**

Add this note near the adapter action vocabulary:

```markdown
Adapter aliases return failed `ActionResult` values for lookup and execution
failures. `wait_for_element` remains the retrying primitive for wait-style
flows.
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

Append a `2026-06-17: Adapter Action Execution Failure Handling` section to
`docs/development-log.md` with:

- red and green focused test results,
- full suite result,
- production review result,
- boundary note that `automation_core` remains unchanged.

- [ ] **Step 5: Commit and push**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
git add adapters tests docs
git commit -m "fix: handle adapter action failures"
git push origin main
```
