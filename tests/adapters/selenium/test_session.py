from pathlib import Path

import pytest

from adapters import AdapterStartupError
from adapters.selenium import SeleniumSession, SeleniumSessionFactory
from automation_core.drivers import DriverSession


class FakeDriver:
    def __init__(self):
        self.closed = False
        self.visited = []
        self.screenshots = []
        self.page_source = "<html />"

    def get(self, url):
        self.visited.append(url)
        return "loaded"

    def save_screenshot(self, path):
        self.screenshots.append(path)
        Path(path).write_text("fake image", encoding="utf-8")
        return True

    def quit(self):
        self.closed = True


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


def test_selenium_session_reports_unsupported_action():
    session = SeleniumSession(driver=FakeDriver())

    result = session.execute_action("missing_action")

    assert result.success is False
    assert "unsupported selenium action" in result.message


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
