from adapters.uia2 import Uia2Element
from tests.adapters.uia2._fakes import FakeUiObject


def test_click_success():
    element = Uia2Element("text=登录", FakeUiObject("text=登录"))

    result = element.click()

    assert result.success is True


def test_click_failure_is_reported():
    class Broken:
        def click(self):
            raise RuntimeError("stale")

    result = Uia2Element("text=x", Broken()).click()

    assert result.success is False
    assert "stale" in result.message


def test_input_text_focuses_clears_and_sends():
    lookup = FakeUiObject("text=搜索")

    result = Uia2Element("text=搜索", lookup).input_text("门票")

    assert result.success is True
    assert lookup.clicked == 1
    assert lookup.cleared == 1
    assert lookup.sent == [("门票", False)]


def test_input_text_failure_is_reported():
    class Broken:
        def click(self):
            pass

        def send_keys(self, text):
            raise RuntimeError("ime gone")

    result = Uia2Element("text=x", Broken()).input_text("hi")

    assert result.success is False
    assert "ime gone" in result.message


def test_text_returns_value():
    element = Uia2Element("text=x", FakeUiObject("text=x", text="门票"))

    assert element.text() == "门票"


def test_text_missing_returns_empty():
    element = Uia2Element("text=x", FakeUiObject("text=x"))

    assert element.text() == ""
