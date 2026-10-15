"""Semantic snapshot, ref dispatch, scroll and key action tests."""

import pytest

from adapters.uia2 import RefElement, Uia2Session
from tests.adapters.uia2._fakes import FakeDevice
from tests.adapters.uia2.test_distill import SCREEN_XML, _node
from tests.adapters.uia2.test_session import make_isolated_session, make_session


SNAPSHOT_XML = "".join(
    [
        '<hierarchy rotation="0">',
        _node(
            cls="android.widget.FrameLayout",
            bounds="[0,0][1080,2400]",
            children="".join(
                [
                    _node(
                        text="设置",
                        cls="android.widget.Button",
                        clickable=True,
                        bounds="[440,100][640,160]",
                    ),
                    _node(
                        resource_id="com.example:id/search_src_text",
                        cls="android.widget.EditText",
                        clickable=True,
                        bounds="[40,300][1040,400]",
                        children=_node(text="搜索我的订单", bounds="[60,320][400,380]"),
                    ),
                ]
            ),
        ),
        "</hierarchy>",
    ]
)


class SnapshotDevice(FakeDevice):
    """FakeDevice with hierarchy dumps; counts them for warm-cache asserts."""

    def __init__(self, hierarchy=SNAPSHOT_XML, current=None, **kwargs):
        if current is None:
            current = {"package": "com.example", "activity": ".Home"}
        super().__init__(hierarchy_result=hierarchy, current_result=current, **kwargs)
        self.dump_count = 0

    def dump_hierarchy(self):
        self.dump_count += 1
        return FakeDevice.dump_hierarchy(self)


class SwitchingHierarchyDevice(SnapshotDevice):
    """Returns a different hierarchy dump per call (scroll simulation)."""

    def __init__(self, hierarchies, **kwargs):
        super().__init__(hierarchy=hierarchies[0], **kwargs)
        self.hierarchies = list(hierarchies)

    def dump_hierarchy(self):
        index = min(self.dump_count, len(self.hierarchies) - 1)
        self.dump_count += 1
        return self.hierarchies[index]


def _single_button_xml(text="关于本机", resource_id=""):
    return "".join(
        [
            '<hierarchy rotation="0">',
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    text=text,
                    resource_id=resource_id,
                    cls="android.widget.Button",
                    clickable=True,
                    bounds="[200,1000][880,1200]",
                ),
            ),
            "</hierarchy>",
        ]
    )


def test_semantic_snapshot_returns_structured_data():
    session, device = make_session(device=SnapshotDevice())

    result = session.execute_action("semantic_snapshot")

    assert result.success is True
    assert result.data["viewport_width"] == 1080
    assert result.data["viewport_height"] == 2400
    assert result.data["package_name"] == "com.example"
    assert result.data["activity_name"] == ".Home"
    assert result.data["markdown"].startswith("# Device Viewport: 1080x2400")
    assert '[@1] button: "设置"' in result.data["markdown"]
    assert '[@2] input: "搜索我的订单"' in result.data["markdown"]
    assert device.dump_count == 1


def test_semantic_snapshot_reuses_warm_cache():
    session, device = make_session(device=SnapshotDevice())

    session.execute_action("semantic_snapshot")
    second = session.execute_action("semantic_snapshot")

    assert second.success is True
    assert device.dump_count == 1


def test_semantic_snapshot_refresh_forces_new_dump():
    session, device = make_session(device=SnapshotDevice())

    session.execute_action("semantic_snapshot")
    session.execute_action("semantic_snapshot", refresh=True)

    assert device.dump_count == 2


def test_semantic_snapshot_fails_without_hierarchy_support():
    session, _ = make_session()

    result = session.execute_action("semantic_snapshot")

    assert result.success is False
    assert "hierarchy" in result.message


def test_semantic_snapshot_fails_on_malformed_xml():
    session, _ = make_session(device=SnapshotDevice(hierarchy="<broken"))

    result = session.execute_action("semantic_snapshot")

    assert result.success is False
    assert "semantic snapshot failed" in result.message


def test_tap_by_ref_dispatches_cached_bounds_without_new_dump():
    session, device = make_session(device=SnapshotDevice())
    session.execute_action("semantic_snapshot")

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    assert ("click", 540, 130) in device.calls
    assert device.dump_count == 1


def test_tap_by_compact_alias_accepts_bare_number():
    session, device = make_session(device=SnapshotDevice())
    session.execute_action("semantic_snapshot")

    result = session.execute_action("click", selector="1", by="compact")

    assert result.success is True
    assert ("click", 540, 130) in device.calls


def test_tap_by_ref_dumps_fresh_when_cache_expired():
    session, device = make_session(device=SnapshotDevice(), snapshot_ttl=0)
    session.execute_action("semantic_snapshot")

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    assert device.dump_count == 2


def test_tap_by_ref_fails_for_stale_ref_without_dispatch():
    session, device = make_session(device=SnapshotDevice())
    session.execute_action("semantic_snapshot")

    result = session.execute_action("tap", selector="@9", by="ref")

    assert result.success is False
    assert "ref @9 not in current snapshot" in result.message
    assert not any(call[0] == "click" for call in device.calls)


def test_tap_by_ref_rejects_non_numeric_selector():
    session, _ = make_session(device=SnapshotDevice())

    result = session.execute_action("tap", selector="@abc", by="ref")

    assert result.success is False
    assert "invalid ref selector" in result.message


def test_find_element_with_ref_returns_ref_element():
    session, _ = make_session(device=SnapshotDevice())

    element = session.find_element("ref", "@2")

    assert isinstance(element, RefElement)
    assert element.identifier == "@2"
    assert element.text() == "搜索我的订单"
    assert element.bounds == {"x": 40, "y": 300, "width": 1000, "height": 100}


def test_find_element_with_ref_raises_for_unknown_ref():
    session, _ = make_session(device=SnapshotDevice())

    with pytest.raises(KeyError):
        session.find_element("@9", "ref")


def test_type_text_by_ref_clicks_clears_and_sends():
    session, device = make_session(device=SnapshotDevice())
    session.execute_action("semantic_snapshot")

    result = session.execute_action(
        "type_text", selector="@2", by="ref", text="大麦"
    )

    assert result.success is True
    assert ("click", 540, 350) in device.calls
    assert ("clear_text",) in device.calls
    assert ("send_keys", "大麦") in device.calls


def test_type_text_by_ref_rejects_non_editable_element():
    session, device = make_session(device=SnapshotDevice())

    result = session.execute_action(
        "type_text", selector="@1", by="ref", text="大麦"
    )

    assert result.success is False
    assert "not an editable input" in result.message
    assert not any(call[0] == "send_keys" for call in device.calls)


def test_element_bounds_by_ref_uses_cached_snapshot():
    session, device = make_session(device=SnapshotDevice())
    session.execute_action("semantic_snapshot")

    result = session.execute_action("element_bounds", selector="@2", by="ref")

    assert result.success is True
    assert result.data == {"x": 40, "y": 300, "width": 1000, "height": 100}
    assert device.dump_count == 1


def test_wait_for_element_rejects_ref_selectors():
    session, device = make_session(device=SnapshotDevice())

    result = session.execute_action(
        "wait_for_element", selector="@1", by="ref", timeout=5
    )

    assert result.success is False
    assert "does not support ref selectors" in result.message
    assert device.dump_count == 0


def test_press_back_and_home_dispatch_key_presses():
    session, device = make_session(device=SnapshotDevice())

    assert session.execute_action("press_back").success is True
    assert session.execute_action("press_home").success is True
    assert ("press", "back") in device.calls
    assert ("press", "home") in device.calls


def test_press_key_falls_back_to_dedicated_method():
    class DedicatedDevice(SnapshotDevice):
        press = None

        def press_back(self):
            self.calls.append(("dedicated_back",))

    session, device = make_session(device=DedicatedDevice())

    result = session.execute_action("press_back")

    assert result.success is True
    assert ("dedicated_back",) in device.calls


def test_press_key_fails_without_driver_support():
    session, device = make_session(device=SnapshotDevice())
    device.press = None

    result = session.execute_action("press_back")

    assert result.success is False
    assert "does not support key presses" in result.message


def test_tap_by_ref_reports_disabled_element():
    disabled_xml = "".join(
        [
            '<hierarchy rotation="0">',
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    text="禁用",
                    cls="android.widget.Button",
                    clickable=True,
                    enabled=False,
                    bounds="[0,0][100,100]",
                ),
            ),
            "</hierarchy>",
        ]
    )
    session, device = make_session(device=SnapshotDevice(hierarchy=disabled_xml))

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "disabled" in result.message
    assert not any(call[0] == "click" for call in device.calls)


def test_scroll_into_view_finds_element_after_swipe():
    device = SwitchingHierarchyDevice(
        [SNAPSHOT_XML, _single_button_xml(text="关于本机")]
    )
    session, _ = make_session(device=device)

    result = session.execute_action(
        "scroll_into_view", selector="关于本机", by="text"
    )

    assert result.success is True
    assert result.data["attempts"] == 1
    assert result.data["ref"] == 1
    assert result.data["bounds"] == {
        "x": 200,
        "y": 1000,
        "width": 680,
        "height": 200,
    }
    swipes = [call for call in device.calls if call[0] == "swipe"]
    assert len(swipes) == 1
    # direction=up swipes from the lower half to the upper half of the screen
    assert swipes[0][1] == 540 and swipes[0][2] == 1800
    assert swipes[0][3] == 540 and swipes[0][4] == 600


def test_scroll_into_view_fails_after_exhausting_swipes():
    device = SwitchingHierarchyDevice([SNAPSHOT_XML])
    session, _ = make_session(device=device)

    result = session.execute_action(
        "scroll_into_view", selector="不存在", by="text", max_swipes=2
    )

    assert result.success is False
    assert "not visible after 2 swipe(s)" in result.message
    swipes = [call for call in device.calls if call[0] == "swipe"]
    assert len(swipes) == 2


def test_scroll_into_view_matches_by_resource_id_short_form():
    device = SwitchingHierarchyDevice(
        [SNAPSHOT_XML, _single_button_xml(resource_id="com.example:id/about_entry")]
    )
    session, _ = make_session(device=device)

    result = session.execute_action(
        "scroll_into_view", selector="about_entry", by="id"
    )

    assert result.success is True
    assert result.data["ref"] == 1


def test_scroll_into_view_rejects_xpath_lookups():
    session, _ = make_session(device=SnapshotDevice())

    result = session.execute_action(
        "scroll_into_view", selector="//node", by="xpath"
    )

    assert result.success is False
    assert "text/id/description" in result.message


def test_scroll_into_view_rejects_invalid_direction():
    session, _ = make_session(device=SnapshotDevice())

    result = session.execute_action(
        "scroll_into_view", selector="设置", by="text", direction="diagonal"
    )

    assert result.success is False
    assert "invalid scroll direction" in result.message


def test_semantic_snapshot_artifact_writes_markdown(tmp_path):
    session, _ = make_isolated_session(tmp_path, device=SnapshotDevice())

    handle = session.capture_artifact("semantic_snapshot", "home")

    assert handle.artifact_type == "semantic_snapshot"
    content = handle.path.read_text(encoding="utf-8")
    assert content.startswith("# Device Viewport: 1080x2400")
    assert "[@1] button" in content


def test_sessions_do_not_share_snapshot_cache():
    device = SnapshotDevice()
    first = Uia2Session(device, snapshot_ttl=0)
    first.execute_action("tap", selector="@1", by="ref")
    first.stop()

    second = Uia2Session(device, snapshot_ttl=0)
    result = second.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    assert device.dump_count == 2
