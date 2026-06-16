from pathlib import Path

import pytest

from adapters import AdapterStartupError
from adapters.appium import AppiumSession, AppiumSessionFactory
from automation_core.drivers import DriverSession


class FakeMobileDriver:
    def __init__(self):
        self.closed = False
        self.activated = []
        self.lookups = []
        self.scripts = []
        self.screenshots = []
        self.page_source = "<hierarchy />"
        self.element = FakeMobileElement()

    def activate_app(self, app_id):
        self.activated.append(app_id)
        return "activated"

    def find_element(self, by, selector):
        self.lookups.append((by, selector))
        return self.element

    def execute_script(self, script, args):
        self.scripts.append((script, args))
        return {"script": script, "args": args}

    def save_screenshot(self, path):
        self.screenshots.append(path)
        Path(path).write_text("fake mobile image", encoding="utf-8")
        return True

    def quit(self):
        self.closed = True


class FakeMobileElement:
    def __init__(self):
        self.clicked = False
        self.cleared = False
        self.keys = []

    def click(self):
        self.clicked = True
        return "clicked"

    def clear(self):
        self.cleared = True

    def send_keys(self, text):
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


def test_appium_session_executes_mobile_script_action():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("mobile: clickGesture", x=1, y=2)

    assert result.success is True
    assert result.message == "mobile: clickGesture"
    assert result.data == {"script": "mobile: clickGesture", "args": {"x": 1, "y": 2}}
    assert driver.scripts == [("mobile: clickGesture", {"x": 1, "y": 2})]


def test_appium_session_tap_alias_executes_coordinate_tap():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("tap", x=1, y=2)

    assert result.success is True
    assert result.message == "tap"
    assert result.data == {"script": "mobile: clickGesture", "args": {"x": 1, "y": 2}}
    assert driver.scripts == [("mobile: clickGesture", {"x": 1, "y": 2})]


def test_appium_session_tap_alias_finds_and_clicks_element():
    driver = FakeMobileDriver()
    session = AppiumSession(driver=driver)

    result = session.execute_action("tap", selector="buy")

    assert result.success is True
    assert result.message == "tap"
    assert result.data == "clicked"
    assert driver.lookups == [("accessibility id", "buy")]
    assert driver.element.clicked is True


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


def test_appium_session_reports_unsupported_action():
    session = AppiumSession(driver=FakeMobileDriver())

    result = session.execute_action("missing_action")

    assert result.success is False
    assert "unsupported appium action" in result.message


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
