import pytest

from adapters.phone_playwright.element import PhonePlaywrightElement
from tests.adapters.phone_playwright._fakes import FakePhoneLocator


def test_element_click_success():
    loc = FakePhoneLocator("text=登录", bounds={"left": 10, "top": 20, "right": 50, "bottom": 80})
    el = PhonePlaywrightElement("text=登录", loc)

    res = el.click()

    assert res.success is True
    assert loc.clicked == 1


def test_element_click_failure():
    loc = FakePhoneLocator("text=登录", should_fail_click=True)
    el = PhonePlaywrightElement("text=登录", loc)

    res = el.click()

    assert res.success is False
    assert "element click failed" in res.message


def test_element_input_text_success():
    loc = FakePhoneLocator("id=username")
    el = PhonePlaywrightElement("id=username", loc)

    res = el.input_text("admin_user")

    assert res.success is True
    assert loc.filled == ["admin_user"]


def test_element_input_text_failure():
    loc = FakePhoneLocator("id=username", should_fail_fill=True)
    el = PhonePlaywrightElement("id=username", loc)

    res = el.input_text("admin_user")

    assert res.success is False
    assert "element input failed" in res.message


def test_element_text():
    loc = FakePhoneLocator("text=提交", text="确认提交")
    el = PhonePlaywrightElement("text=提交", loc)

    assert el.text() == "确认提交"


def test_element_text_empty_when_none():
    loc = FakePhoneLocator("text=提交", text=None)
    el = PhonePlaywrightElement("text=提交", loc)

    assert el.text() == ""


def test_element_bounds_ltrb_dict():
    loc = FakePhoneLocator("btn", bounds={"left": 100, "top": 200, "right": 300, "bottom": 450})
    el = PhonePlaywrightElement("btn", loc)

    b = el.bounds
    assert b == {"x": 100, "y": 200, "width": 200, "height": 250}


def test_element_bounds_xywh_dict():
    loc = FakePhoneLocator("btn", bounds={"x": 50, "y": 60, "width": 70, "height": 80})
    el = PhonePlaywrightElement("btn", loc)

    b = el.bounds
    assert b == {"x": 50, "y": 60, "width": 70, "height": 80}


def test_element_bounds_none_when_unavailable():
    loc = FakePhoneLocator("btn", bounds=None)
    el = PhonePlaywrightElement("btn", loc)

    assert el.bounds is None


def test_click_failure_preserves_error_message():
    class FailingLocator:
        def click(self, **kwargs):
            from tests.adapters.phone_playwright._fakes import FakeActionResult
            return FakeActionResult(success=False, verb="click", error="timeout 5.0s on device")

    el = PhonePlaywrightElement("btn", FailingLocator())
    res = el.click()

    assert res.success is False
    assert "timeout 5.0s on device" in res.message


def test_input_failure_preserves_error_message():
    class FailingLocator:
        def fill(self, text, **kwargs):
            from tests.adapters.phone_playwright._fakes import FakeActionResult
            return FakeActionResult(success=False, verb="fill", error="element not editable")

    el = PhonePlaywrightElement("input", FailingLocator())
    res = el.input_text("test")

    assert res.success is False
    assert "element not editable" in res.message
