"""Deep-coverage tests for Uia2Session validation and degradation paths.

These pin the error-message and graceful-degradation contracts of
``adapters/uia2/session.py`` — the branches a refactor would silently
break (parameter validation, driver-capability fallbacks, artifact
writer failures). Foreground-guard retry behavior lives in
``test_snapshot_session.py``.
"""

import pytest

from adapters.errors import AdapterArtifactError
from adapters.uia2 import Uia2Session
from tests.adapters.uia2._fakes import FakeDevice, FakeUiObject


def make_session(device=None, **kwargs):
    device = device or FakeDevice()
    return Uia2Session(device, **kwargs), device


_MINIMAL_XML = (
    '<hierarchy rotation="0">'
    '<node text="设置" clickable="true" bounds="[0,0][1080,2400]"/>'
    "</hierarchy>"
)


def make_snapshot_session(device=None, **kwargs):
    """Session over a device whose single dump distills to one clickable
    element (@1, full-viewport bounds)."""
    device = device or FakeDevice(hierarchy_result=_MINIMAL_XML)
    session = Uia2Session(device, **kwargs)
    return session, device


# --- by / descriptor normalization ------------------------------------------


def test_non_string_by_is_rejected():
    session, _ = make_session()

    result = session.execute_action("tap", selector="登录", by=42)

    assert result.success is False
    assert "by must be a string" in result.message


def test_unsupported_by_lists_the_supported_set():
    session, _ = make_session()

    result = session.execute_action("tap", selector="登录", by="regex")

    assert result.success is False
    assert "unsupported by: regex" in result.message
    assert "text" in result.message and "uiautomator" in result.message


def test_instance_only_descriptor_is_rejected():
    session, _ = make_session()

    result = session.execute_action(
        "tap", selector={"instance": 2}, by="uiautomator"
    )

    assert result.success is False
    assert "at least one attribute constraint" in result.message


# --- launch/terminate capability fallbacks ------------------------------------


def test_launch_app_without_device_support():
    class NoStart(FakeDevice):
        app_start = None  # class attr silences the base method

    session, _ = make_session(NoStart())

    result = session.execute_action("launch_app", app_id="cn.damai")

    assert result.success is False
    assert "does not support app launch" in result.message


def test_terminate_app_without_device_support():
    class NoStop(FakeDevice):
        app_stop = None

    session, _ = make_session(NoStop())

    result = session.execute_action("terminate_app", app_id="cn.damai")

    assert result.success is False
    assert "does not support app termination" in result.message


# --- tap / coordinate paths ----------------------------------------------------


def test_tap_neither_selector_nor_coordinates():
    session, _ = make_session()

    result = session.execute_action("tap")

    assert result.success is False
    assert "missing required parameter: selector or x/y" in result.message


def test_tap_rejects_non_numeric_coordinates():
    session, _ = make_session()

    result = session.execute_action("tap", x="left", y=100)

    assert result.success is False
    assert "x must be a number" in result.message


def test_tap_without_device_click_support():
    class NoClick(FakeDevice):
        click = None

    session, _ = make_session(NoClick())

    result = session.execute_action("tap", x=10, y=20)

    assert result.success is False
    assert "does not support coordinate taps" in result.message


# --- type_text / swipe validation ------------------------------------------------


def test_type_text_requires_selector_then_text():
    session, _ = make_session()

    result = session.execute_action("type_text", text="hi")
    assert result.success is False
    assert "missing required parameter: selector" in result.message

    result = session.execute_action("type_text", selector="搜索")
    assert result.success is False
    assert "missing required parameter: text" in result.message


def test_swipe_lists_all_missing_parameters():
    session, _ = make_session()

    result = session.execute_action("swipe", start_x=10)

    assert result.success is False
    assert "start_y, end_x, end_y" in result.message


def test_swipe_rejects_negative_coordinate():
    session, device = make_session()

    result = session.execute_action(
        "swipe", start_x=-1, start_y=0, end_x=10, end_y=10
    )

    assert result.success is False
    assert "start_x must be >= 0" in result.message
    assert device.calls == []


def test_swipe_without_device_support():
    class NoSwipe(FakeDevice):
        swipe = None

    session, _ = make_session(NoSwipe())

    result = session.execute_action(
        "swipe", start_x=0, start_y=0, end_x=10, end_y=10
    )

    assert result.success is False
    assert "does not support swipe" in result.message


# --- element_bounds degradation ---------------------------------------------------


def test_element_bounds_malformed_dict_is_unavailable():
    device = FakeDevice(
        elements={("text", "口味"): FakeUiObject("text=口味", info={"bounds": {"x": 1}})}
    )
    session, _ = make_session(device)

    result = session.execute_action("element_bounds", selector="口味")

    assert result.success is False
    assert "element bounds unavailable" in result.message


def test_element_bounds_requires_selector():
    session, _ = make_session()

    result = session.execute_action("element_bounds")

    assert result.success is False
    assert "missing required parameter: selector" in result.message


# --- wait_for_element validation + masking contract --------------------------------


def test_wait_for_element_rejects_ref_selectors():
    session, _ = make_session()

    result = session.execute_action("wait_for_element", selector="@1", by="ref")

    assert result.success is False
    assert "does not support ref selectors" in result.message


def test_wait_for_element_rejects_bad_timeout():
    session, _ = make_session()

    result = session.execute_action(
        "wait_for_element", selector="登录", timeout="soon"
    )

    assert result.success is False
    assert "timeout must be a number" in result.message


def test_wait_for_element_lookup_raise_surfaces_as_timeout():
    """retry_until folds persistent lookup raises into the timeout result
    (the documented masking contract for the default retry policy)."""

    class ExplodingDevice(FakeDevice):
        def __call__(self, **kwargs):
            raise RuntimeError("device detached")

    session, _ = make_session(ExplodingDevice(), snapshot_ttl=0)

    result = session.execute_action(
        "wait_for_element", selector="登录", timeout=0.01, interval=0.01
    )

    assert result.success is False
    assert "timed out waiting for element: 登录" in result.message


# --- descriptor lookup failure paths ------------------------------------------------


def test_descriptor_lookup_failure_reports_element_lookup_failed():
    device = FakeDevice(missing={("text", "缺失")})
    session, _ = make_session(device)

    result = session.execute_action("tap", selector="缺失")

    assert result.success is False
    assert "element lookup failed: 缺失" in result.message


def test_descriptor_lookup_failure_re_raises_for_wait_retry():
    """wait_for_element sets retry_lookup=True: the raise propagates and
    folds into the timeout result instead of an error ActionResult."""
    device = FakeDevice(missing={("text", "缺失")})
    session, _ = make_session(device)

    result = session.execute_action(
        "wait_for_element", selector="缺失", timeout=0.01, interval=0.01
    )

    assert result.success is False
    assert "timed out" in result.message


def test_ref_selector_dispatches_coordinate_tap():
    """A valid @N ref taps at cached bounds; the device click records the
    ref element's center."""
    session, device = make_snapshot_session()
    # Prime the warm cache with a snapshot containing one element.
    session.execute_action("semantic_snapshot", refresh=True)

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    # FakeDevice.click records ("click", x, y) as flat call args.
    assert ("click", 540, 1200) in device.calls


def test_ref_without_coordinate_dispatcher_is_rejected():
    class NoClickNoTap(FakeDevice):
        click = None
        tap = None

    session, _ = make_snapshot_session(NoClickNoTap(hierarchy_result=_MINIMAL_XML))
    session.execute_action("semantic_snapshot", refresh=True)

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "driver does not support coordinate taps" in result.message


def test_invalid_ref_selector_text():
    session, _ = make_session()

    result = session.execute_action("tap", selector="abc", by="ref")

    assert result.success is False
    assert "invalid ref selector: abc" in result.message


# --- _foreground_app tolerance branches -----------------------------------------------


def test_app_current_non_dict_is_tolerated():
    class WeirdCurrent(FakeDevice):
        def app_current(self):
            return "com.example"

    session, _ = make_snapshot_session(WeirdCurrent(hierarchy_result=_MINIMAL_XML))

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True  # check skipped, not fatal


def test_app_current_raise_is_tolerated():
    class ExplodingCurrent(FakeDevice):
        def app_current(self):
            raise RuntimeError("shell died")

    session, _ = make_snapshot_session(ExplodingCurrent(hierarchy_result=_MINIMAL_XML))

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True


# --- scroll_into_view validation ------------------------------------------------------


def test_scroll_into_view_requires_selector():
    session, _ = make_session()

    result = session.execute_action("scroll_into_view")

    assert result.success is False
    assert "missing required parameter: selector" in result.message


def test_scroll_into_view_rejects_class_selector():
    session, _ = make_session()

    result = session.execute_action("scroll_into_view", selector="Button", by="class")

    assert result.success is False
    assert "matches snapshots with text/id/description" in result.message


def test_scroll_into_view_rejects_bad_max_swipes():
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view", selector="电池", max_swipes="many"
    )

    assert result.success is False
    assert "max_swipes must be a number" in result.message


def test_scroll_into_view_rejects_negative_duration():
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view", selector="电池", duration=-0.5
    )

    assert result.success is False
    assert "duration must be >= 0" in result.message


def test_scroll_into_view_rejects_bad_distance_ratio():
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view", selector="电池", distance_ratio=None
    )

    assert result.success is False
    assert "distance_ratio must be a number" in result.message


def test_scroll_into_view_rejects_bad_settle():
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view", selector="电池", settle=True  # bool is not a number
    )

    assert result.success is False
    assert "settle must be a number" in result.message


def test_scroll_into_view_rejects_invalid_direction():
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view", selector="电池", direction="sideways"
    )

    assert result.success is False
    assert "invalid scroll direction: sideways" in result.message


def test_scroll_into_view_ref_match_returns_bounds():
    session, device = make_snapshot_session()
    session.execute_action("semantic_snapshot", refresh=True)
    # Clear the cached swipe-free match so the ref lookup is exercised.
    device.calls.clear()

    result = session.execute_action("scroll_into_view", selector="@1", by="ref")

    assert result.success is True
    assert result.data["ref"] == 1
    assert result.data["bounds"] == {"x": 0, "y": 0, "width": 1080, "height": 2400}
    assert result.data["attempts"] == 0


def test_scroll_into_view_text_match_via_first_info_fallback():
    """A matching non-interactable element (no ref) still resolves via the
    first_info fallback and reports its bounds."""
    xml = (
        '<hierarchy rotation="0">'
        '<node text="隐藏文本" bounds="[10,20][110,220]"/>'
        "</hierarchy>"
    )
    session, _ = make_snapshot_session(FakeDevice(hierarchy_result=xml), snapshot_ttl=0)

    result = session.execute_action("scroll_into_view", selector="隐藏文本")

    assert result.success is True
    assert result.data["ref"] is None
    assert result.data["bounds"] == {"x": 10, "y": 20, "width": 100, "height": 200}


# --- scroll swipe capability + artifact writers ----------------------------------------


def test_scroll_into_view_without_swipe_support_fails():
    class NoSwipe(FakeDevice):
        swipe = None

    xml = '<hierarchy rotation="0"><node text="别的" bounds="[0,0][1080,2400]"/></hierarchy>'
    session, _ = make_snapshot_session(
        NoSwipe(hierarchy_result=xml), snapshot_dump_attempts=1
    )
    # First snapshot finds no match, then the swipe capability check hits.
    result = session.execute_action("scroll_into_view", selector="不存在")

    assert result.success is False
    assert "does not support swipe" in result.message


def test_scroll_into_view_exhausts_swipes_and_reports():
    """Target never appears: bounded swipes then the exhaustion message."""
    xml = '<hierarchy rotation="0"><node text="别的" bounds="[0,0][1080,2400]"/></hierarchy>'
    session, device = make_snapshot_session(
        FakeDevice(hierarchy_result=xml),
        snapshot_dump_attempts=1,
        snapshot_dump_interval=0.0,
    )

    result = session.execute_action(
        "scroll_into_view", selector="不存在", max_swipes=2, settle=0.0
    )

    assert result.success is False
    assert "not visible after 2 swipe(s): 不存在" in result.message
    swipes = [c for c in device.calls if c[0] == "swipe"]
    assert len(swipes) == 2


def test_capture_artifact_hierarchy_dump_non_string(tmp_path):
    class BadDump(FakeDevice):
        def dump_hierarchy(self):
            return 12345

    session, _ = make_session(BadDump())

    with pytest.raises(AdapterArtifactError, match="hierarchy dump is not a string"):
        session.capture_artifact("page_source", "dump.xml")


def test_capture_artifact_hierarchy_dump_raises(tmp_path):
    class ExplodingDump(FakeDevice):
        def dump_hierarchy(self):
            raise RuntimeError("usb reset")

    session, _ = make_session(ExplodingDump())

    with pytest.raises(AdapterArtifactError, match="hierarchy dump failed"):
        session.capture_artifact("page_source", "dump.xml")


def test_capture_artifact_hierarchy_no_dump_capability(tmp_path):
    class NoDump(FakeDevice):
        dump_hierarchy = None

    session, _ = make_session(NoDump())

    with pytest.raises(AdapterArtifactError, match="does not provide a UI hierarchy"):
        session.capture_artifact("page_source", "dump.xml")


def test_capture_artifact_screenshot_not_saveable(tmp_path):
    session, _ = make_session(FakeDevice(screenshot_result=object()))

    with pytest.raises(AdapterArtifactError, match="not saveable"):
        session.capture_artifact("screenshot", "shot.png")


def test_capture_artifact_semantic_snapshot_failure(tmp_path):
    class NoDump(FakeDevice):
        dump_hierarchy = None

    session, _ = make_session(NoDump())

    with pytest.raises(AdapterArtifactError, match="does not provide a UI hierarchy"):
        session.capture_artifact("semantic_snapshot", "snap.md")


def test_capture_artifact_rejects_unknown_type(tmp_path):
    session, _ = make_session()

    with pytest.raises(AdapterArtifactError, match="unsupported uia2 artifact type"):
        session.capture_artifact("video", "clip.mp4")


# --- _run_action + number validation ------------------------------------------------


def test_run_action_wraps_device_exception():
    class ExplodingClick(FakeDevice):
        def click(self, x, y):
            raise RuntimeError("inject failed")

    session, _ = make_session(ExplodingClick())

    result = session.execute_action("tap", x=5, y=5)

    assert result.success is False
    assert "tap failed: inject failed" in result.message


def test_number_parameter_rejects_negative_and_bool():
    session, _ = make_session()

    for kwargs in (
        {"x": -3, "y": 5},
        {"x": True, "y": 5},
    ):
        result = session.execute_action("tap", **kwargs)
        assert result.success is False


# --- find_element contract (ElementLookupSession) -------------------------------


def test_find_element_contract_success_and_keyerror():
    session, device = make_session()

    handle = session.find_element("text", "登录")

    assert handle is not None
    assert device.calls == [("selector", {"text": "登录"})]

    with pytest.raises(KeyError, match="unsupported by: rune"):
        session.find_element("rune", "登录")


def test_find_element_dict_selector_requires_uiautomator_by():
    session, _ = make_session()

    with pytest.raises(KeyError, match="selector must be a non-empty string"):
        session.find_element("text", {"text": "登录"})


# --- element_bounds malformed dict shapes ----------------------------------------


def test_element_bounds_non_dict_bounds_attr_unavailable():
    device = FakeDevice(
        elements={("text", "口味"): FakeUiObject("text=口味", info=None)}
    )
    session, _ = make_session(device)

    result = session.execute_action("element_bounds", selector="口味")

    assert result.success is False
    assert "element bounds unavailable" in result.message


def test_element_bounds_keyerror_values_unavailable():
    device = FakeDevice(
        elements={
            ("text", "口味"): FakeUiObject(
                "text=口味", info={"bounds": {"x": 1, "y": 2, "left": 9}}
            )
        }
    )
    session, _ = make_session(device)

    result = session.execute_action("element_bounds", selector="口味")

    assert result.success is False
    assert "element bounds unavailable" in result.message


# --- descriptor lookup raise with retry_lookup -------------------------------------


def test_descriptor_lookup_raise_with_retry_lookup_re_raises():
    class ExplodingLookup(FakeDevice):
        def __call__(self, **kwargs):
            raise RuntimeError("device vanished")

    session, _ = make_session(ExplodingLookup())

    # Direct call with retry_lookup=True: the raise must propagate
    # (wait_for_element's retry loop relies on it folding into timeout).
    with pytest.raises(RuntimeError, match="device vanished"):
        session._resolve_element(
            selector={"text": "登录"}, by="uiautomator", retry_lookup=True
        )


# --- ref resolve with broken snapshot + foreground without capability ---------------


def test_ref_resolve_when_snapshot_capture_fails():
    class NoDump(FakeDevice):
        dump_hierarchy = None

    session, _ = make_session(NoDump())

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "does not provide a UI hierarchy" in result.message


def test_foreground_app_missing_capability_returns_none_pair():
    class NoCurrent(FakeDevice):
        app_current = None

    session, _ = make_session(NoCurrent())

    assert session._foreground_app() == (None, None)


def test_scroll_into_view_bad_by_gates_before_alias_check():
    session, _ = make_session()

    result = session.execute_action("scroll_into_view", selector="x", by=123)

    assert result.success is False
    assert "by must be a string" in result.message


# --- missing-parameter single shots (round 2) --------------------------------------


def test_terminate_app_reports_missing_app_id():
    session, _ = make_session()

    result = session.execute_action("terminate_app")

    assert result.success is False
    assert "missing required parameter: app_id" in result.message


def test_type_text_selector_error_propagates():
    session, _ = make_session()

    result = session.execute_action("type_text", selector="x", text="hi", by="base64")

    assert result.success is False
    assert "unsupported by: base64" in result.message


def test_swipe_bad_duration_is_rejected():
    session, device = make_session()

    result = session.execute_action(
        "swipe", start_x=0, start_y=0, end_x=10, end_y=10, duration="slow"
    )

    assert result.success is False
    assert "duration must be a number" in result.message
    assert device.calls == []


def test_coordinate_pair_bad_y_rejected():
    session, _ = make_session()

    result = session.execute_action("tap", x=10, y="mid")

    assert result.success is False
    assert "y must be a number" in result.message


def test_element_bounds_resolve_error_propagates():
    session, _ = make_session()

    result = session.execute_action("element_bounds", selector="x", by="regex")

    assert result.success is False
    assert "unsupported by: regex" in result.message


def test_wait_for_element_requires_selector():
    session, _ = make_session()

    result = session.execute_action("wait_for_element")

    assert result.success is False
    assert "missing required parameter: selector" in result.message


def test_wait_for_element_rejects_bad_interval():
    session, _ = make_session()

    result = session.execute_action(
        "wait_for_element", selector="登录", interval=-1
    )

    assert result.success is False
    assert "interval must be >= 0" in result.message


def test_scroll_into_view_capture_error_propagates():
    session, _ = make_snapshot_session(FakeDevice(hierarchy_result=None))

    result = session.execute_action("scroll_into_view", selector="x")

    assert result.success is False
    assert "hierarchy" in result.message


def test_capture_artifact_screenshot_without_capability(tmp_path):
    class NoShot(FakeDevice):
        screenshot = None

    session, _ = make_session(NoShot())

    with pytest.raises(AdapterArtifactError, match="does not support screenshot"):
        session.capture_artifact("screenshot", "shot.png")


# --- dump-raise in _capture_snapshot propagates as snapshot error --------------------


def test_capture_snapshot_dump_raise_message():
    class ExplodingDump(FakeDevice):
        def dump_hierarchy(self):
            raise RuntimeError("shell gone")

    session = Uia2Session(ExplodingDump(), snapshot_dump_attempts=1)

    result = session.execute_action("semantic_snapshot")

    assert result.success is False
    assert "hierarchy dump failed: shell gone" in result.message


def test_capture_snapshot_dump_retry_then_success():
    class FlakyDump(FakeDevice):
        def __init__(self):
            super().__init__(hierarchy_result=None)
            self.dump_count = 0

        def dump_hierarchy(self):
            self.dump_count += 1
            if self.dump_count < 2:
                raise RuntimeError("transient")
            return _MINIMAL_XML

    session = Uia2Session(FlakyDump(), snapshot_dump_attempts=3, snapshot_dump_interval=0)

    result = session.execute_action("semantic_snapshot")

    assert result.success is True


def test_capture_snapshot_overlay_only_degrades_after_retries():
    xml = '<hierarchy rotation="0" package="com.other.systemui"><node text="x" bounds="[0,0][1,1]"/></hierarchy>'
    attempts = []
    device = FakeDevice(current_result={"package": "com.target.app"})

    def flaky_dump():
        attempts.append(1)
        return xml

    device.hierarchy_result = flaky_dump
    session = Uia2Session(
        device, snapshot_dump_attempts=2, snapshot_dump_interval=0
    )

    result = session.execute_action("semantic_snapshot")

    # Graceful degradation: succeeds on the last dump after exhausting retries.
    assert result.success is True
    assert len(attempts) == 2


# --- final 4 lines: defense-in-depth branches ---------------------------------------


def test_find_element_missing_selector_keyerror():
    """find_element surfaces resolver errors as KeyError; its `element is
    None` guard (line 181) is defense-in-depth — resolvers always pair
    (element, error) — pinned here via the ref path on a missing index."""
    session, _ = make_snapshot_session(snapshot_ttl=0)
    session.execute_action("semantic_snapshot", refresh=True)

    with pytest.raises(KeyError, match="ref @9 not in current snapshot"):
        session.find_element("compact", "@9")


def test_element_bounds_missing_bounds_keys_unavailable():
    """bounds dict with partial keys hits the KeyError branch (341-342)."""
    device = FakeDevice(
        elements={
            ("text", "口味"): FakeUiObject(
                "text=口味", info={"bounds": {"x": 1, "y": 2}}
            )
        }
    )
    session, _ = make_session(device)

    result = session.execute_action("element_bounds", selector="口味")

    assert result.success is False
    assert "element bounds unavailable" in result.message


def test_descriptor_lookup_no_retry_reports_lookup_failed():
    """retry_lookup=False descriptor failure returns the error (line 453)."""

    class ExplodingLookup(FakeDevice):
        def __call__(self, **kwargs):
            raise RuntimeError("device vanished")

    session, _ = make_session(ExplodingLookup())

    result = session.execute_action(
        "tap", selector={"text": "登录"}, by="uiautomator"
    )

    assert result.success is False
    assert "element lookup failed" in result.message


def test_element_bounds_coercion_guard_is_upstream_defense():
    """Uia2Element normalizes info into int bounds upstream (bad values
    coerce → None), so the int() coercion guard inside _element_bounds
    (lines 341-342) is defense-in-depth, not reachable via real drivers.
    The upstream normalization contract is pinned here instead."""
    from adapters.uia2.element import Uia2Element

    device = FakeDevice(
        elements={("text", "口味"): FakeUiObject("text=口味", info={"bounds": []})}
    )
    session, _ = make_session(device)
    element, _ = session._resolve_element(selector="口味", by="text")

    assert isinstance(element, Uia2Element)
    assert element.bounds is None

    result = session.execute_action("element_bounds", selector="口味")

    assert result.success is False
    assert "element bounds unavailable" in result.message
