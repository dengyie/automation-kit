from pathlib import Path

import pytest

from adapters import AdapterStartupError
from adapters.selenium import SeleniumSession, SeleniumSessionFactory
from automation_core.drivers import DriverSession


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

    def find_element(self, by, selector):
        self.lookups.append((by, selector))
        if len(self.lookups) <= self.lookup_failures:
            raise LookupError("not found")
        return self.element

    def save_screenshot(self, path):
        self.screenshots.append(path)
        Path(path).write_text("fake image", encoding="utf-8")
        return True

    def quit(self):
        self.closed = True


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


def test_selenium_session_implements_driver_contract(tmp_path):
    session = SeleniumSession(
        driver=FakeDriver(),
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    assert isinstance(session, DriverSession)
    assert session.info.driver_name == "selenium"
    assert session.info.platform == "web"
    assert session.info.identifier == "browser-1"


def test_selenium_session_executes_supported_driver_action():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    result = session.execute_action("get", url="https://example.test")

    assert result.success is True
    assert result.message == "get"
    assert result.data == "loaded"
    assert driver.visited == ["https://example.test"]


def test_selenium_session_open_alias_loads_url():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    result = session.execute_action("open", url="https://example.test")

    assert result.success is True
    assert result.message == "open"
    assert result.data == "loaded"
    assert driver.visited == ["https://example.test"]


def test_selenium_session_open_reports_driver_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"get": "navigation failed"}))

    result = session.execute_action("open", url="https://example.test")

    assert result.success is False
    assert result.message == "open failed: navigation failed"


def test_selenium_session_click_alias_finds_and_clicks_element():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    result = session.execute_action("click", selector="#buy")

    assert result.success is True
    assert result.message == "click"
    assert result.data == "clicked"
    assert driver.lookups == [("css selector", "#buy")]
    assert driver.element.clicked is True


def test_selenium_session_click_reports_element_action_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"click": "click intercepted"}))

    result = session.execute_action("click", selector="#buy")

    assert result.success is False
    assert result.message == "click failed: click intercepted"


def test_selenium_session_type_text_alias_clears_and_sends_keys():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    result = session.execute_action("type_text", selector="#kw", text="concert")

    assert result.success is True
    assert result.message == "type_text"
    assert result.data == "typed"
    assert driver.lookups == [("css selector", "#kw")]
    assert driver.element.cleared is True
    assert driver.element.keys == ["concert"]


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


def test_selenium_session_type_text_alias_can_skip_clear():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    result = session.execute_action(
        "type_text",
        selector="#kw",
        text="concert",
        clear=False,
    )

    assert result.success is True
    assert driver.element.cleared is False
    assert driver.element.keys == ["concert"]


def test_selenium_session_wait_for_element_alias_retries_until_found():
    driver = FakeDriver(lookup_failures=1)
    session = SeleniumSession(driver=driver)

    result = session.execute_action(
        "wait_for_element",
        selector="#buy",
        timeout=1.0,
        interval=0,
    )

    assert result.success is True
    assert result.message == "wait_for_element"
    assert result.data is driver.element
    assert driver.lookups == [
        ("css selector", "#buy"),
        ("css selector", "#buy"),
    ]


def test_selenium_session_wait_for_element_alias_reports_timeout():
    driver = FakeDriver(lookup_failures=3)
    session = SeleniumSession(driver=driver)

    result = session.execute_action(
        "wait_for_element",
        selector="#missing",
        timeout=0,
        interval=0,
    )

    assert result.success is False
    assert result.message == "timed out waiting for element: #missing"
    assert len(driver.lookups) == 1


def test_selenium_session_wait_for_element_alias_requires_selector():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action("wait_for_element")

    assert result.success is False
    assert result.message == "missing required parameter: selector"


def test_selenium_session_wait_for_element_reports_missing_lookup_support():
    class NoLookupDriver:
        pass

    session = SeleniumSession(driver=NoLookupDriver())

    result = session.execute_action("wait_for_element", selector="#buy")

    assert result.success is False
    assert result.message == "driver does not support element lookup"


def test_selenium_session_wait_for_element_rejects_negative_timeout():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="#buy",
        timeout=-1,
    )

    assert result.success is False
    assert result.message == "timeout must be >= 0"


def test_selenium_session_wait_for_element_rejects_negative_interval():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="#buy",
        interval=-1,
    )

    assert result.success is False
    assert result.message == "interval must be >= 0"


def test_selenium_session_wait_for_element_rejects_invalid_timeout():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="#buy",
        timeout="soon",
    )

    assert result.success is False
    assert result.message == "timeout must be a number"


def test_selenium_session_wait_for_element_rejects_invalid_interval():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="#buy",
        interval="soon",
    )

    assert result.success is False
    assert result.message == "interval must be a number"


def test_selenium_session_alias_reports_missing_required_parameter():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action("open")

    assert result.success is False
    assert "missing required parameter: url" in result.message


def test_selenium_session_element_alias_reports_missing_lookup_support():
    class NoLookupDriver:
        pass

    session = SeleniumSession(driver=NoLookupDriver())

    result = session.execute_action("click", selector="#buy")

    assert result.success is False
    assert result.message == "driver does not support element lookup"


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


def test_selenium_session_reports_unsupported_action():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action("missing_action")

    assert result.success is False
    assert "unsupported selenium action" in result.message


def test_selenium_session_reports_raw_driver_action_failure():
    session = SeleniumSession(driver=FakeDriver(failures={"refresh": "browser closed"}))

    result = session.execute_action("refresh")

    assert result.success is False
    assert result.message == "refresh failed: browser closed"


def test_selenium_session_captures_screenshot(tmp_path):
    driver = FakeDriver()
    session = SeleniumSession(
        driver=driver,
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("screenshot", "home.png")

    assert handle.artifact_type == "screenshot"
    assert handle.path.exists()
    assert handle.path.read_text(encoding="utf-8") == "fake image"
    assert driver.screenshots == [str(handle.path)]


def test_selenium_session_captures_page_source(tmp_path):
    driver = FakeDriver()
    session = SeleniumSession(
        driver=driver,
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("page_source", "source.html")

    assert handle.artifact_type == "page_source"
    assert handle.path.exists()
    assert handle.path.read_text(encoding="utf-8") == "<html />"


def test_selenium_session_captures_ui_tree_alias(tmp_path):
    driver = FakeDriver()
    session = SeleniumSession(
        driver=driver,
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("ui_tree", "tree.xml")

    assert handle.artifact_type == "ui_tree"
    assert handle.path.exists()
    assert handle.path.read_text(encoding="utf-8") == "<html />"


def test_selenium_session_rejects_invalid_artifact_name(tmp_path):
    session = SeleniumSession(
        driver=FakeDriver(),
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    with pytest.raises(ValueError, match="invalid artifact name"):
        session.capture_artifact("screenshot", "..")


def test_selenium_session_stops_driver():
    driver = FakeDriver()
    session = SeleniumSession(driver=driver)

    session.start()
    session.stop()

    assert driver.closed is True


def test_selenium_session_factory_creates_session(tmp_path):
    factory = SeleniumSessionFactory(
        driver_factory=FakeDriver,
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    session = factory.create()

    assert isinstance(session, SeleniumSession)
    assert session.info.identifier == "browser-1"


def test_selenium_session_factory_wraps_driver_startup_failure(tmp_path):
    def failing_driver_factory():
        raise RuntimeError("browser failed")

    factory = SeleniumSessionFactory(
        driver_factory=failing_driver_factory,
        identifier="browser-1",
        artifact_root=tmp_path,
    )

    with pytest.raises(AdapterStartupError, match="failed to create selenium driver"):
        factory.create()
