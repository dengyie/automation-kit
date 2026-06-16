from pathlib import Path

import pytest

from adapters import AdapterStartupError
from adapters.appium import AppiumSession, AppiumSessionFactory
from automation_core.drivers import DriverSession


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

    def find_element(self, by, selector):
        self.lookups.append((by, selector))
        if len(self.lookups) <= self.lookup_failures:
            raise LookupError("not found")
        return self.element

    def execute_script(self, script, args):
        if "execute_script" in self.failures:
            raise RuntimeError(self.failures["execute_script"])
        self.scripts.append((script, args))
        return {"script": script, "args": args}

    def save_screenshot(self, path):
        self.screenshots.append(path)
        Path(path).write_text("fake mobile image", encoding="utf-8")
        return True

    def quit(self):
        self.closed = True


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


def test_appium_session_implements_driver_contract(tmp_path):
    session = AppiumSession(
        driver=FakeMobileDriver(),
        identifier="device-1",
        artifact_root=tmp_path,
    )

    assert isinstance(session, DriverSession)
    assert session.info.driver_name == "appium"
    assert session.info.platform == "android"
    assert session.info.identifier == "device-1"


def test_appium_session_executes_supported_driver_action():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("activate_app", app_id="example.app")

    assert result.success is True
    assert result.message == "activate_app"
    assert result.data == "activated"
    assert driver.activated == ["example.app"]


def test_appium_session_launch_app_alias_activates_app():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("launch_app", app_id="example.app")

    assert result.success is True
    assert result.message == "launch_app"
    assert result.data == "activated"
    assert driver.activated == ["example.app"]


def test_appium_session_launch_app_reports_driver_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"activate_app": "app unavailable"})
    )

    result = session.execute_action("launch_app", app_id="example.app")

    assert result.success is False
    assert result.message == "launch_app failed: app unavailable"


def test_appium_session_launch_app_alias_requires_app_id():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action("launch_app")

    assert result.success is False
    assert result.message == "missing required parameter: app_id"


def test_appium_session_executes_mobile_script_action():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("mobile: clickGesture", x=1, y=2)

    assert result.success is True
    assert result.message == "mobile: clickGesture"
    assert result.data == {"script": "mobile: clickGesture", "args": {"x": 1, "y": 2}}
    assert driver.scripts == [("mobile: clickGesture", {"x": 1, "y": 2})]


def test_appium_session_reports_mobile_script_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"execute_script": "scroll failed"})
    )

    result = session.execute_action("mobile: scrollGesture", direction="down")

    assert result.success is False
    assert result.message == "mobile: scrollGesture failed: scroll failed"


def test_appium_session_tap_alias_executes_coordinate_tap():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("tap", x=1, y=2)

    assert result.success is True
    assert result.message == "tap"
    assert result.data == {"script": "mobile: clickGesture", "args": {"x": 1, "y": 2}}
    assert driver.scripts == [("mobile: clickGesture", {"x": 1, "y": 2})]


def test_appium_session_coordinate_tap_reports_script_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"execute_script": "gesture failed"})
    )

    result = session.execute_action("tap", x=1, y=2)

    assert result.success is False
    assert result.message == "tap failed: gesture failed"


def test_appium_session_tap_alias_finds_and_clicks_element():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("tap", selector="buy")

    assert result.success is True
    assert result.message == "tap"
    assert result.data == "clicked"
    assert driver.lookups == [("accessibility id", "buy")]
    assert driver.element.clicked is True


def test_appium_session_element_tap_reports_element_action_failure():
    session = AppiumSession(driver=FakeMobileDriver(failures={"click": "tap failed"}))

    result = session.execute_action("tap", selector="buy")

    assert result.success is False
    assert result.message == "tap failed: tap failed"


def test_appium_session_type_text_alias_clears_and_sends_keys():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("type_text", selector="search", text="concert")

    assert result.success is True
    assert result.message == "type_text"
    assert result.data == "typed"
    assert driver.lookups == [("accessibility id", "search")]
    assert driver.element.cleared is True
    assert driver.element.keys == ["concert"]


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


def test_appium_session_type_text_alias_can_skip_clear():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action(
        "type_text",
        selector="search",
        text="concert",
        clear=False,
    )

    assert result.success is True
    assert driver.element.cleared is False
    assert driver.element.keys == ["concert"]


def test_appium_session_wait_for_element_alias_retries_until_found():
    driver = FakeMobileDriver(lookup_failures=1)
    session = AppiumSession(driver=driver)

    result = session.execute_action(
        "wait_for_element",
        selector="buy",
        timeout=1.0,
        interval=0,
    )

    assert result.success is True
    assert result.message == "wait_for_element"
    assert result.data is driver.element
    assert driver.lookups == [
        ("accessibility id", "buy"),
        ("accessibility id", "buy"),
    ]


def test_appium_session_wait_for_element_alias_reports_timeout():
    driver = FakeMobileDriver(lookup_failures=3)
    session = AppiumSession(driver=driver)

    result = session.execute_action(
        "wait_for_element",
        selector="missing",
        timeout=0,
        interval=0,
    )

    assert result.success is False
    assert result.message == "timed out waiting for element: missing"
    assert len(driver.lookups) == 1


def test_appium_session_wait_for_element_alias_requires_selector():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action("wait_for_element")

    assert result.success is False
    assert result.message == "missing required parameter: selector"


def test_appium_session_wait_for_element_reports_missing_lookup_support():
    class NoLookupDriver:
        pass

    session = AppiumSession(driver=NoLookupDriver())

    result = session.execute_action("wait_for_element", selector="buy")

    assert result.success is False
    assert result.message == "driver does not support element lookup"


def test_appium_session_wait_for_element_rejects_negative_timeout():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="buy",
        timeout=-1,
    )

    assert result.success is False
    assert result.message == "timeout must be >= 0"


def test_appium_session_wait_for_element_rejects_negative_interval():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="buy",
        interval=-1,
    )

    assert result.success is False
    assert result.message == "interval must be >= 0"


def test_appium_session_wait_for_element_rejects_invalid_timeout():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="buy",
        timeout="soon",
    )

    assert result.success is False
    assert result.message == "timeout must be a number"


def test_appium_session_wait_for_element_rejects_invalid_interval():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action(
        "wait_for_element",
        selector="buy",
        interval="soon",
    )

    assert result.success is False
    assert result.message == "interval must be a number"


def test_appium_session_alias_reports_missing_required_parameter():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action("tap")

    assert result.success is False
    assert "missing required parameter: selector or x/y" in result.message


def test_appium_session_element_alias_reports_missing_lookup_support():
    class NoLookupDriver:
        pass

    session = AppiumSession(driver=NoLookupDriver())

    result = session.execute_action("tap", selector="buy")

    assert result.success is False
    assert result.message == "driver does not support element lookup"


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


def test_appium_session_reports_unsupported_action():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action("missing_action")

    assert result.success is False
    assert "unsupported appium action" in result.message


def test_appium_session_reports_raw_driver_action_failure():
    session = AppiumSession(
        driver=FakeMobileDriver(failures={"activate_app": "device offline"})
    )

    result = session.execute_action("activate_app", app_id="example.app")

    assert result.success is False
    assert result.message == "activate_app failed: device offline"


def test_appium_session_captures_screenshot(tmp_path):
    driver = FakeMobileDriver()
    session = AppiumSession(
        driver=driver,
        identifier="device-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("screenshot", "screen.png")

    assert handle.artifact_type == "screenshot"
    assert handle.path.exists()
    assert handle.path.read_text(encoding="utf-8") == "fake mobile image"
    assert driver.screenshots == [str(handle.path)]


def test_appium_session_captures_page_source(tmp_path):
    driver = FakeMobileDriver()
    session = AppiumSession(
        driver=driver,
        identifier="device-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("page_source", "tree.xml")

    assert handle.artifact_type == "page_source"
    assert handle.path.read_text(encoding="utf-8") == "<hierarchy />"


def test_appium_session_captures_ui_tree_alias(tmp_path):
    driver = FakeMobileDriver()
    session = AppiumSession(
        driver=driver,
        identifier="device-1",
        artifact_root=tmp_path,
    )

    handle = session.capture_artifact("ui_tree", "tree.xml")

    assert handle.artifact_type == "ui_tree"
    assert handle.path.read_text(encoding="utf-8") == "<hierarchy />"


def test_appium_session_rejects_invalid_artifact_name(tmp_path):
    session = AppiumSession(
        driver=FakeMobileDriver(),
        identifier="device-1",
        artifact_root=tmp_path,
    )

    with pytest.raises(ValueError, match="invalid artifact name"):
        session.capture_artifact("screenshot", "..")


def test_appium_session_stops_driver():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    session.start()
    session.stop()

    assert driver.closed is True


def test_appium_session_factory_creates_session(tmp_path):
    factory = AppiumSessionFactory(
        driver_factory=FakeMobileDriver,
        identifier="device-1",
        artifact_root=tmp_path,
    )

    session = factory.create()

    assert isinstance(session, AppiumSession)
    assert session.info.identifier == "device-1"


def test_appium_session_factory_wraps_driver_startup_failure(tmp_path):
    def failing_driver_factory():
        raise RuntimeError("device failed")

    factory = AppiumSessionFactory(
        driver_factory=failing_driver_factory,
        identifier="device-1",
        artifact_root=tmp_path,
    )

    with pytest.raises(AdapterStartupError, match="failed to create appium driver"):
        factory.create()
