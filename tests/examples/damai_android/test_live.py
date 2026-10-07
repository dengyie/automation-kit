import pytest

from examples.damai_android.live import (
    UIA2_UDID_ENV,
    create_session_factory,
)


def test_create_session_factory_rejects_unknown_driver():
    with pytest.raises(ValueError, match="unsupported driver: nope"):
        create_session_factory("nope")


def test_create_session_factory_rejects_appium_without_external_factory():
    with pytest.raises(ValueError, match="pass one via --factory"):
        create_session_factory("appium")


def test_uia2_factory_connects_and_wraps_device(monkeypatch):
    class FakeDevice:
        pass

    connected = []

    def fake_connect(udid):
        connected.append(udid)
        return FakeDevice()

    monkeypatch.setattr(
        "examples.damai_android.live._connect_uia2", fake_connect
    )

    factory = create_session_factory("uia2", udid="1275cb0e")
    session = factory()

    assert connected == ["1275cb0e"]
    assert session.info.driver_name == "uia2"
    assert session.driver is not None


def test_uia2_zero_arg_factory_reads_udid_env(monkeypatch):
    class FakeDevice:
        pass

    monkeypatch.setenv(UIA2_UDID_ENV, "serial-1")
    monkeypatch.setattr(
        "examples.damai_android.live._connect_uia2",
        lambda udid: FakeDevice(),
    )

    from examples.damai_android import live

    session = live.uia2_session_factory()

    assert session.info.driver_name == "uia2"


def test_uia2_connect_failure_becomes_startup_error(monkeypatch):
    def broken_connect(udid):
        raise RuntimeError("no devices")

    monkeypatch.setattr(
        "examples.damai_android.live._connect_uia2", broken_connect
    )

    from adapters.errors import AdapterStartupError

    factory = create_session_factory("uia2")
    with pytest.raises(AdapterStartupError):
        factory()


def test_phone_playwright_factory_connects_and_wraps(monkeypatch):
    # phone-playwright is an optional live-device SDK; the offline suite and
    # CI never install it, so skip instead of failing on the import.
    pytest.importorskip("phone_playwright")

    class FakeDev:
        current_page = object()

    class FakePW:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def connect(self, udid):
            return FakeDev()

    monkeypatch.setattr("phone_playwright.SyncPhonePlaywright", FakePW)

    factory = create_session_factory("phone_playwright", udid="192.168.1.3:43037")
    session = factory()

    assert session.info.driver_name == "phone_playwright"
    assert session.driver is FakeDev.current_page
