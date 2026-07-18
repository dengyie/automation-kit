from adapters.appium.session import AppiumSession
from adapters.selenium.session import SeleniumSession


class RecordingDriver:
    def __init__(self):
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1

    def get(self, url):
        return None

    def activate_app(self, app_id):
        return None


def test_selenium_session_stop_is_idempotent_for_owned_driver():
    driver = RecordingDriver()
    session = SeleniumSession(driver=driver, identifier="web-1")

    session.start()
    session.stop()
    session.stop()

    assert driver.quit_calls == 1


def test_appium_session_stop_is_idempotent_for_owned_driver():
    driver = RecordingDriver()
    session = AppiumSession(driver=driver, identifier="android-1")

    session.start()
    session.stop()
    session.stop()

    assert driver.quit_calls == 1
