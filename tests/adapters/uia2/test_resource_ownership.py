from adapters.uia2 import Uia2Session
from tests.adapters.uia2._fakes import (
    DisconnectableDevice,
    FakeDevice,
    FullyClosableDevice,
    QuitOnlyDevice,
)


def test_stop_without_start_is_noop():
    device = DisconnectableDevice()
    session = Uia2Session(device)

    session.stop()

    assert device.disconnect_count == 0


def test_stop_calls_disconnect_only():
    device = FullyClosableDevice()
    session = Uia2Session(device)
    session.start()

    session.stop()

    assert device.disconnect_count == 1
    assert device.quit_count == 0


def test_stop_falls_back_to_quit():
    device = QuitOnlyDevice()
    session = Uia2Session(device)
    session.start()

    session.stop()

    assert device.quit_count == 1


def test_stop_is_idempotent():
    device = DisconnectableDevice()
    session = Uia2Session(device)
    session.start()

    session.stop()
    session.stop()

    assert device.disconnect_count == 1


def test_stop_without_close_hooks_is_safe():
    device = FakeDevice()
    session = Uia2Session(device)
    session.start()

    session.stop()

    assert device.disconnect_count == 0
    assert device.quit_count == 0
