"""Deep-coverage tests for PhonePlaywrightElement polymorphic backends.

The element wrapper duck-types three locator generations (playwright
text_content/bounding_box, phone-playwright text/bounds, uia-style
get_text/info); each backend variant is pinned here so a refactor cannot
silently drop one.
"""

from adapters.phone_playwright.element import PhonePlaywrightElement


class RawResult:
    """Locator click() returning a plain dict (no .success attr)."""

    def __init__(self, payload):
        self._payload = payload

    def __call__(self):
        return self._payload


class DictClickLocator:
    """click() returns a bare dict — the `hasattr(res, "success") is False`
    branch must still report success."""

    def __init__(self):
        self.clicked = 0

    def click(self):
        self.clicked += 1
        return {"ok": True}

    def text(self):
        return "plain text"

    def get_text(self):
        return "get_text fallback"


def test_click_plain_dict_result_is_success():
    loc = DictClickLocator()
    el = PhonePlaywrightElement("btn", loc)

    res = el.click()

    assert res.success is True
    assert res.message == "element click"
    assert loc.clicked == 1


def test_click_raises_action_result_failure():
    class Failing:
        def click(self):
            raise RuntimeError("device detached")

    res = PhonePlaywrightElement("btn", Failing()).click()

    assert res.success is False
    assert "device detached" in res.message


def test_input_text_type_text_backend():
    class TypeTextLocator:
        def __init__(self):
            self.typed = []

        def type_text(self, text):
            self.typed.append(text)
            return None  # no .success attr

    loc = TypeTextLocator()
    res = PhonePlaywrightElement("input", loc).input_text(12345)

    assert res.success is True
    assert res.message == "element input"
    assert loc.typed == ["12345"]  # non-str coerced via str()


def test_input_text_send_keys_backend():
    class SendKeysLocator:
        def __init__(self):
            self.sent = []

        def send_keys(self, text):
            self.sent.append(text)

    loc = SendKeysLocator()
    res = PhonePlaywrightElement("input", loc).input_text("hi")

    assert res.success is True
    assert loc.sent == ["hi"]


def test_input_text_no_supported_method():
    class Inert:
        pass

    res = PhonePlaywrightElement("input", Inert()).input_text("hi")

    assert res.success is False
    assert "does not support text input" in res.message


def test_input_text_result_success_with_verb():
    class OkResult:
        success = True
        verb = "fill"
        error = None
        data = {"len": 2}

        def __init__(self, locator):
            self._locator = locator

    class FillLocator:
        def fill(self, text):
            return OkResult(self)

    res = PhonePlaywrightElement("input", FillLocator()).input_text("hi")

    assert res.success is True
    assert res.message == "fill"
    assert res.data == {"len": 2}


def test_input_text_raises():
    class Exploding:
        def fill(self, text):
            raise RuntimeError("input frozen")

    res = PhonePlaywrightElement("input", Exploding()).input_text("hi")

    assert res.success is False
    assert "input frozen" in res.message


def test_text_priority_order():
    """text_content wins over text, text over get_text, get_text over attr."""

    class AllBackends:
        text_content = None  # callable class attr? no — make it a method

        def text_content(self):
            return "from text_content"

        def text(self):
            return "from text"

        def get_text(self):
            return "from get_text"

        text_value = "from attr"

    class NoTextContent:
        def text(self):
            return "from text"

        def get_text(self):
            return "from get_text"

        text_value = "from attr"

    class OnlyGetText:
        def get_text(self):
            return "from get_text"

        text_value = "from attr"

    class OnlyAttr:
        text_value = "attr only"

    assert PhonePlaywrightElement("x", AllBackends()).text() == "from text_content"
    assert PhonePlaywrightElement("x", NoTextContent()).text() == "from text"
    assert PhonePlaywrightElement("x", OnlyGetText()).text() == "from get_text"
    assert PhonePlaywrightElement("x", OnlyAttr()).text() == "attr only"
    assert PhonePlaywrightElement("x", object()).text() == ""


def test_text_returns_empty_on_exception():
    class Exploding:
        def text_content(self):
            raise RuntimeError("stale element")

    assert PhonePlaywrightElement("x", Exploding()).text() == ""


def test_text_non_string_coerced():
    class Numeric:
        def text_content(self):
            return 42

    assert PhonePlaywrightElement("x", Numeric()).text() == "42"


# --- bounds: bounding_box path -----------------------------------------------


def test_bounds_bounding_box_valid_dict():
    class BoundingBox:
        def bounding_box(self):
            return {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0}

    assert PhonePlaywrightElement("x", BoundingBox()).bounds == {
        "x": 1, "y": 2, "width": 3, "height": 4,
    }


def test_bounds_bounding_box_raises_then_attr_fallback():
    class RaisesBox:
        bounds = {"left": 1, "top": 2, "right": 5, "bottom": 9}

        def bounding_box(self):
            raise RuntimeError("not attached")

    assert PhonePlaywrightElement("x", RaisesBox()).bounds == {
        "x": 1, "y": 2, "width": 4, "height": 7,
    }


def test_bounds_bounding_box_incomplete_dict_falls_through():
    class PartialBox:
        bounds = None

        def bounding_box(self):
            return {"x": 1, "y": 2}  # missing width/height

    assert PhonePlaywrightElement("x", PartialBox()).bounds is None


def test_bounds_info_dict_fallback():
    class InfoOnly:
        info = {"bounds": {"left": 0, "top": 0, "right": 10, "bottom": 20}}

    assert PhonePlaywrightElement("x", InfoOnly()).bounds == {
        "x": 0, "y": 0, "width": 10, "height": 20,
    }


def test_bounds_ltrb_bad_values_return_none():
    class BadBounds:
        bounds = {"left": "x", "top": 0, "right": 1, "bottom": 2}

    assert PhonePlaywrightElement("x", BadBounds()).bounds is None


def test_bounds_xywh_bad_values_return_none():
    class BadBounds:
        bounds = {"x": 0, "y": 0, "width": None, "height": 2}

    assert PhonePlaywrightElement("x", BadBounds()).bounds is None


def test_bounds_object_with_attributes():
    """CompactElement shape: locator.bounds returns self (a rect object)."""
    class CompactRect:
        left, top, right, bottom = 5, 6, 25, 46

        @property
        def bounds(self):
            return self

    assert PhonePlaywrightElement("x", CompactRect()).bounds == {
        "x": 5, "y": 6, "width": 20, "height": 40,
    }


def test_bounds_object_with_bad_attributes():
    class CompactRect:
        left, top, right, bottom = "a", 6, 25, 46

        @property
        def bounds(self):
            return self

    assert PhonePlaywrightElement("x", CompactRect()).bounds is None


def test_bounds_unknown_shape_returns_none():
    class Weird:
        bounds = 42

    assert PhonePlaywrightElement("x", Weird()).bounds is None
