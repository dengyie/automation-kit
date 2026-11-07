"""Gap-coverage tests for adapters/phone_playwright/session.py and snapshot.py.

Pins the rarely-hit session contracts: the by-normalization prefix
remapping, tap/element-bounds defensive failure branches, scroll-into-view
invalid direction and no-scroll-locator, wait_for's non-ActionResult and
raising wait_for contracts, the invalid-coordinates tap guard, the
artifact-not-written raise, the base64-image screenshot fallback path, and
snapshot._ref_to_int / _optional_float guards.
"""

import pytest

from adapters.errors import AdapterArtifactError
from tests.adapters.phone_playwright._fakes import (
    FakeActionResult,
    FakePhoneLocator,
    FakePhonePage,
    FakePhoneSnapshot,
)

from adapters.phone_playwright import PhonePlaywrightSession
from adapters.phone_playwright.snapshot import _optional_float, _ref_to_int


def make_session(**kwargs):
    page = kwargs.pop("page", None) or FakePhonePage()
    return PhonePlaywrightSession(page, **kwargs), page


# --- resolve by-prefix remapping (461-462) -------------------------------------------


def test_resource_id_selector_gets_prefix_added_once():
    """A bare resource-id selector has the prefix added; one already carrying
    the prefix passes through verbatim — both resolve to the same locator
    target (461-462)."""
    session, page = make_session()

    session.execute_action("element_bounds", selector="com.example:id/ok", by="resource-id")
    session.execute_action("element_bounds", selector="resource-id=com.example:id/ok", by="resource-id")

    assert page.calls.count(("locator", "resource-id=com.example:id/ok")) == 2


# --- tap defensive branches (183, 194, 214) -------------------------------------------


def test_tap_missing_element_returns_failure():
    """A None-resolved element in _tap produces the element-not-found
    failure (defensive guard, unreachable via the real resolver)."""
    session, _ = make_session()

    original = session._resolve_element

    def fake_resolve(selector, by, retry_lookup=False):
        return None, None

    session._resolve_element = fake_resolve
    result = session.execute_action("tap", selector="幽灵")

    assert result.success is False
    assert result.message == "element not found: 幽灵"


def test_tap_non_numeric_y_reports_invalid_coordinates():
    """A non-numeric coordinate is rejected by _number_parameter first; the
    invalid-coordinates guard (194) is only reachable when the pair-level
    check returns coordinates=None without an error."""
    session, _ = make_session()
    result = session.execute_action("tap", x=100, y="high")

    assert result.success is False
    assert result.message == "y must be a number"

    # Defensive branch: coordinate_pair returning (None, None).
    original = session._coordinate_pair
    session._coordinate_pair = lambda x, y: (None, None)
    result = session.execute_action("tap", x=100, y=200)

    assert result.success is False
    assert result.message == "invalid coordinates"


def test_tap_error_from_resolver_propagates():
    session, _ = make_session()
    result = session.execute_action("tap", selector="", by="text")

    assert result.success is False
    assert result.message == "selector must be a non-empty string"


# --- scroll_into_view guards (264, 266, 279) ------------------------------------------


def test_scroll_into_view_invalid_direction_fails():
    session, _ = make_session()
    result = session.execute_action(
        "scroll_into_view", selector="列表项", direction="diagonal"
    )

    assert result.success is False
    assert result.message == "invalid scroll direction: diagonal"


def test_scroll_into_view_locator_without_scroll_support():
    class NoScrollLocator:
        def is_visible(self):
            return True

    session, page = make_session()
    page.locators["text=静态"] = NoScrollLocator()

    result = session.execute_action("scroll_into_view", selector="静态")

    assert result.success is False
    assert result.message == "locator does not support scroll_into_view"


def test_scroll_into_view_success_records_scroll_kwargs():
    session, page = make_session()
    result = session.execute_action(
        "scroll_into_view",
        selector="列表项",
        direction="down",
        max_swipes=3,
        distance_ratio=0.8,
    )

    assert result.success is True
    assert page.locators["text=列表项"].scroll_calls == [
        {"max_swipes": 3, "direction": "down", "distance_ratio": 0.8}
    ]


# --- wait_for_element locator-channel contracts (370, 390, 398-399) --------------------


def test_wait_for_element_non_action_result_wait_for_is_success():
    """A locator wait_for returning a plain (non-ActionResult) value still
    counts as success — only objects carrying .success are inspected."""

    class PlainLocator:
        def __init__(self):
            self.wait_calls = []

        def wait_for(self, state="visible", timeout_s=5.0):
            self.wait_calls.append((state, timeout_s))
            return "visible-now"

    locator = PlainLocator()
    session, page = make_session()
    page.locators["text=裸值"] = locator

    result = session.execute_action("wait_for_element", selector="裸值", timeout=1.0)

    assert result.success is True
    assert result.message == "wait_for_element"
    assert result.data == "text=裸值"
    assert locator.wait_calls == [("visible", 1.0)]


def test_wait_for_element_raising_wait_for_falls_through_to_retry():
    """A raising locator wait_for is swallowed (398-399) and the action
    falls back to the retry-lookup channel, which then times out."""

    class ExplodingWaitLocator:
        def wait_for(self, state="visible", timeout_s=5.0):
            raise RuntimeError("locator detached")

        def is_visible(self):
            return False

    session, page = make_session()
    page.locators["text=爆的"] = ExplodingWaitLocator()

    result = session.execute_action(
        "wait_for_element", selector="爆的", timeout=0.15, interval=0.05
    )

    assert result.success is False
    assert result.message == "timed out waiting for element: 爆的"


def test_wait_for_element_locator_wait_timeout_returns_failure():
    class TimingOutLocator:
        def wait_for(self, state="visible", timeout_s=5.0):
            return FakeActionResult(success=False, verb="wait_for", error="timeout")

    session, page = make_session()
    page.locators["text=等不到"] = TimingOutLocator()

    result = session.execute_action("wait_for_element", selector="等不到", timeout=0.5)

    assert result.success is False
    assert result.message == "timed out waiting for element: 等不到"


# --- element_bounds guards (331-332) ----------------------------------------------------


def test_element_bounds_with_partial_dict_is_unavailable():
    """A bounds dict missing keys lands in the (KeyError, TypeError,
    ValueError) guard rather than leaking a partial result."""
    session, page = make_session()

    class PartialBoundsLocator(FakePhoneLocator):
        def bounds(self):
            return {"x": 10, "y": 20}  # no width/height

    page.locators["text=残缺"] = PartialBoundsLocator("text=残缺")

    result = session.execute_action("element_bounds", selector="残缺")

    assert result.success is False
    assert result.message == "element bounds unavailable"


# --- capture_artifact / screenshot (509, 542-543) ---------------------------------------


def test_capture_artifact_raises_when_not_written(tmp_path):
    """If the writer silently produces nothing, capture_artifact raises
    AdapterArtifactError instead of returning a dangling handle (509)."""
    session, _ = make_session(artifact_root=tmp_path)

    session._write_screenshot = lambda path: None

    with pytest.raises(AdapterArtifactError, match="artifact was not written"):
        session.capture_artifact("screenshot", "empty.png")


def test_screenshot_bad_base64_string_falls_through_to_unsaveable(tmp_path):
    """A string that is neither a file path nor valid base64 falls past the
    base64 attempt (542-543) and surfaces as the unsaveable error."""
    session, page = make_session(artifact_root=tmp_path)
    page.screenshot_result = "!!! not base64 at all !!!"

    with pytest.raises(AdapterArtifactError, match="not saveable"):
        session.capture_artifact("screenshot", "bad.png")


def test_screenshot_base64_string_is_decoded(tmp_path):
    """The success mirror: a base64 string screenshot is decoded to bytes."""
    import base64

    session, page = make_session(artifact_root=tmp_path)
    page.screenshot_result = base64.b64encode(b"png-bytes").decode("ascii")

    handle = session.capture_artifact("screenshot", "decoded.png")

    assert handle.path.read_bytes() == b"png-bytes"


# --- remaining guard branches (108, 214, 225, 264, 266, 279, 317, 322, 331-332, 342, 390, 398-399)


def test_find_element_raises_keyerror_for_missing_element():
    """find_element converts a resolver error into KeyError (108) — the
    ElementHandle-lookup contract shared with the core session protocols."""
    session, _ = make_session()

    with pytest.raises(KeyError, match="selector must be a non-empty string"):
        session.find_element("text", "")


def test_type_text_missing_element_guard():
    session, _ = make_session()
    session._resolve_element = lambda selector, by, retry_lookup=False: (None, None)

    result = session.execute_action("type_text", selector="幽灵", text="hi")

    assert result.success is False
    assert result.message == "element not found: 幽灵"


def test_swipe_directional_distance_ratio_error_propagates():
    session, _ = make_session()
    result = session.execute_action("swipe", direction="up", distance_ratio="broad")

    assert result.success is False
    assert result.message == "distance_ratio must be a number"


def test_scroll_into_view_error_and_none_guards():
    session, _ = make_session()
    # resolver error propagates verbatim (264)
    result = session.execute_action("scroll_into_view", selector="", by="text")
    assert result.message == "selector must be a non-empty string"

    # None element → element-not-found (266)
    session._resolve_element = lambda selector, by, retry_lookup=False: (None, None)
    result = session.execute_action("scroll_into_view", selector="幽灵")
    assert result.message == "element not found: 幽灵"

    # bad distance_ratio surfaces its own error (279) — needs a real
    # resolved element so validation reaches the ratio.
    session2, page2 = make_session()
    result = session2.execute_action(
        "scroll_into_view", selector="列表项", distance_ratio="wide"
    )
    assert result.message == "distance_ratio must be a number"


def test_tap_error_and_none_guards():
    session, _ = make_session()
    # resolver error propagates verbatim (183 covered earlier; this is the
    # error-return in the tap path shared by tap/click)
    result = session.execute_action("click", selector="", by="text")
    assert result.message == "selector must be a non-empty string"


def test_element_bounds_and_wait_missing_selector():
    session, _ = make_session()

    result = session.execute_action("element_bounds")
    assert result.success is False
    assert result.message == "missing required parameter: selector"

    result = session.execute_action("wait_for_element")
    assert result.success is False
    assert result.message == "missing required parameter: selector"


def test_element_bounds_none_element_guard():
    session, _ = make_session()
    session._resolve_element = lambda selector, by, retry_lookup=False: (None, None)

    result = session.execute_action("element_bounds", selector="幽灵")

    assert result.message == "element not found: 幽灵"


def test_element_bounds_non_dict_and_bad_values_are_unavailable():
    """Both element-bounds failure shapes: a non-dict bounds value and a dict
    with unconvertible values both land in 'element bounds unavailable'
    (331-332)."""
    session, page = make_session()

    class NonDictBoundsLocator(FakePhoneLocator):
        def bounds(self):
            return "somewhere"

    class BadValuesLocator(FakePhoneLocator):
        def bounds(self):
            return {"x": "abc", "y": None, "width": 1, "height": 1}

    page.locators["text=字符串"] = NonDictBoundsLocator("text=字符串")
    page.locators["text=坏值"] = BadValuesLocator("text=坏值")

    assert session.execute_action("element_bounds", selector="字符串").message == (
        "element bounds unavailable"
    )
    assert session.execute_action("element_bounds", selector="坏值").message == (
        "element bounds unavailable"
    )


def test_element_bounds_partial_dict_hits_value_guard():
    """element.bounds normalizes bad ints to None upstream, so session-side
    line 331-332 needs a dict that is complete-but-unconvertible — pinned by
    patching the element lookup to return one directly."""

    class FakeResolved:
        bounds = {"x": "abc", "y": None, "width": 1, "height": 1}
        identifier = "text=坏值"

    session, _ = make_session()
    session._resolve_element = lambda selector, by, retry_lookup=False: (
        FakeResolved(),
        None,
    )

    result = session.execute_action("element_bounds", selector="坏值")

    assert result.success is False
    assert result.message == "element bounds unavailable"


def test_find_element_raises_when_resolver_returns_none_element():
    """The second find_element KeyError branch (108): resolver succeeds but
    returns no element."""
    session, _ = make_session()
    session._resolve_element = lambda selector, by, retry_lookup=False: (None, None)

    with pytest.raises(KeyError, match="element not found: 幽灵"):
        session.find_element("text", "幽灵")


def test_wait_for_retry_lookup_none_element_returns_none():
    """In the retry-lookup channel, a None element makes lookup return None
    (390) so retry_until keeps polling until the timeout expires."""
    session, _ = make_session()
    session._resolve_element = lambda selector, by, retry_lookup=False: (None, None)

    result = session.execute_action(
        "wait_for_element", selector="幽灵", timeout=0.15, interval=0.05
    )

    assert result.success is False
    assert result.message == "timed out waiting for element: 幽灵"


def test_wait_for_retry_lookup_invisible_and_raising_is_visible():
    """An invisible locator (398-399 covers the raising is_visible variant)
    keeps lookup returning None until timeout."""

    class RaisingVisibleLocator(FakePhoneLocator):
        def is_visible(self):
            raise RuntimeError("detached mid-check")

    session, page = make_session()
    page.locators["text=隐身"] = RaisingVisibleLocator("text=隐身")

    result = session.execute_action(
        "wait_for_element", selector="隐身", timeout=0.15, interval=0.05
    )

    assert result.success is False
    assert result.message == "timed out waiting for element: 隐身"



# --- snapshot.py guards (91, 104-105) ----------------------------------------------------


def test_ref_to_int_rejects_non_numeric_refs():
    assert _ref_to_int(None) is None
    assert _ref_to_int("@7") == 7
    assert _ref_to_int(" 12 ") == 12
    assert _ref_to_int("e7") is None
    assert _ref_to_int("@") is None


def test_optional_float_guard():
    assert _optional_float(None) is None
    assert _optional_float(3.5) == 3.5
    assert _optional_float("9") == 9.0
    assert _optional_float("soon") is None
