from adapters.phone_playwright import PhonePlaywrightSession
from tests.adapters.phone_playwright._fakes import (
    DisconnectablePage,
    FakePhonePage,
    NoClosePage,
    QuitOnlyPage,
)


def test_stop_without_start_is_noop():
    page = DisconnectablePage()
    session = PhonePlaywrightSession(page)

    session.stop()

    assert page.disconnect_count == 0


def test_stop_calls_close_first():
    page = FakePhonePage()
    session = PhonePlaywrightSession(page)
    session.start()

    session.stop()

    assert page.closed == 1


def test_stop_falls_back_to_disconnect():
    page = DisconnectablePage()
    session = PhonePlaywrightSession(page)
    session.start()

    session.stop()

    assert page.disconnect_count == 1


def test_stop_falls_back_to_quit():
    page = QuitOnlyPage()
    session = PhonePlaywrightSession(page)
    session.start()

    session.stop()

    assert page.quit_count == 1


def test_stop_is_idempotent():
    page = FakePhonePage()
    session = PhonePlaywrightSession(page)
    session.start()

    session.stop()
    session.stop()

    assert page.closed == 1


def test_stop_without_close_hooks_is_safe():
    page = NoClosePage()
    session = PhonePlaywrightSession(page)
    session.start()

    session.stop()
    assert session._started is False
