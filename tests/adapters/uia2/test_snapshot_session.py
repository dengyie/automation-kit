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
        "scroll_into_view", selector="关于本机", by="text", settle=0.0
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
        "scroll_into_view", selector="不存在", by="text", max_swipes=2, settle=0.0
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
        "scroll_into_view", selector="about_entry", by="id", settle=0.0
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


def _partial_button_xml():
    return "".join(
        [
            '<hierarchy rotation="0">',
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    text="贴边按钮",
                    cls="android.widget.Button",
                    clickable=True,
                    bounds="[0,2350][540,2600]",
                ),
            ),
            "</hierarchy>",
        ]
    )


def test_tap_by_ref_taps_visible_region_centre_for_partial_element():
    session, device = make_session(device=SnapshotDevice(hierarchy=_partial_button_xml()))

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    # Full-bounds centre (270, 2475) is below the 2400px viewport; the tap
    # lands at the centre of the visible region instead.
    assert ("click", 270, 2375) in device.calls


def test_tap_by_ref_reports_dispatch_failure():
    session, device = make_session(device=SnapshotDevice())

    def failing_click(x, y):
        raise RuntimeError("injection failed")

    device.click = failing_click

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "ref element click failed" in result.message


def test_scroll_directions_swipe_geometry():
    expected = {
        # direction: (start_x, start_y, end_x, end_y) at 1080x2400, ratio 0.5
        "down": (540, 600, 540, 1800),
        "left": (810, 1200, 270, 1200),
        "right": (270, 1200, 810, 1200),
    }
    for direction, geometry in expected.items():
        device = SwitchingHierarchyDevice(
            [SNAPSHOT_XML, _single_button_xml(text="关于本机")]
        )
        session, _ = make_session(device=device)

        result = session.execute_action(
            "scroll_into_view",
            selector="关于本机",
            by="text",
            direction=direction,
            settle=0.0,
        )

        swipes = [call for call in device.calls if call[0] == "swipe"]
        assert result.success is True, direction
        assert len(swipes) == 1, direction
        assert swipes[0][1:5] == geometry, direction


def test_scroll_settles_after_each_swipe(monkeypatch):
    sleeps = []
    monkeypatch.setattr(
        "adapters.uia2.session.time.sleep", lambda seconds: sleeps.append(seconds)
    )
    device = SwitchingHierarchyDevice([SNAPSHOT_XML, _single_button_xml(text="关于本机")])
    session, _ = make_session(device=device)

    result = session.execute_action("scroll_into_view", selector="关于本机", by="text")

    assert result.success is True
    assert sleeps == [0.3]


def test_semantic_snapshot_tolerates_bad_device_metadata():
    session, _ = make_session(device=SnapshotDevice(current="not-a-dict"))

    result = session.execute_action("semantic_snapshot")

    assert result.success is True
    assert "package_name" not in result.data
    assert "activity_name" not in result.data


# --- foreground-coverage guard (cloud-phone dump flap, 2026-11-06) ----------

# Raw fixture: unlike `_node`, the package attribute is com.android.systemui
# so the dump carries NO foreground (com.example) evidence.
SYSTEMUI_XML = (
    "<hierarchy rotation=\"0\">"
    '<node index="0" text="" resource-id="com.android.systemui:id/navigation_bar_frame" '
    'class="android.widget.FrameLayout" package="com.android.systemui" '
    'checkable="false" clickable="false" enabled="true" scrollable="false" '
    'bounds="[0,2218][1080,2376]" />'
    "</hierarchy>"
)


class OverlayThenForegroundDevice(FakeDevice):
    """First dump is overlay-only (the observed Redroid flap), then good."""

    def __init__(self, **kwargs):
        super().__init__(hierarchy_result=SCREEN_XML, **kwargs)
        self.dump_count = 0

    def dump_hierarchy(self):
        self.dump_count += 1
        if self.dump_count == 1:
            return SYSTEMUI_XML
        return self.hierarchy_result


class PersistentOverlayDevice(FakeDevice):
    def __init__(self, **kwargs):
        super().__init__(hierarchy_result=SYSTEMUI_XML, **kwargs)
        self.dump_count = 0

    def dump_hierarchy(self):
        self.dump_count += 1
        return SYSTEMUI_XML


def test_snapshot_retries_until_foreground_dump_arrives(tmp_path):
    device = OverlayThenForegroundDevice()
    device.current_result = {"package": "com.example", "activity": ".Home"}
    session = Uia2Session(device, artifact_root=tmp_path, snapshot_dump_interval=0.0)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 2, "the overlay-only dump must be retried"
    # Elements come from the foreground dump (search EditText), not the
    # systemui navigation bar.
    assert any(
        "search_src_text" in (e.get("resource_id") or "")
        for e in result.data["elements"]
    )


def test_snapshot_degrades_after_exhausted_retries(tmp_path):
    device = PersistentOverlayDevice()
    device.current_result = {"package": "com.example", "activity": ".Home"}
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_attempts=3,
        snapshot_dump_interval=0.0,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    # Graceful degradation: the overlay-only dump still distills.
    assert result.success is True
    assert device.dump_count == 3


def test_snapshot_skips_validation_without_app_current(tmp_path):
    """The app_current tolerance contract: no metadata -> no validation, a
    single dump is taken even when it would look 'uncovered'."""
    device = PersistentOverlayDevice()
    device.current_result = None
    session = Uia2Session(device, artifact_root=tmp_path, snapshot_dump_interval=0.0)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 1
    assert "package_name" not in result.data


def test_snapshot_attempts_one_disables_retry(tmp_path):
    device = PersistentOverlayDevice()
    device.current_result = {"package": "com.example", "activity": ".Home"}
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_attempts=1,
        snapshot_dump_interval=0.0,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 1


def test_session_factory_threads_dump_guard_params(tmp_path):
    from adapters.uia2 import Uia2SessionFactory

    device = PersistentOverlayDevice()
    device.current_result = {"package": "com.example", "activity": ".Home"}
    factory = Uia2SessionFactory(
        lambda: device,
        artifact_root=tmp_path,
        snapshot_dump_attempts=2,
        snapshot_dump_interval=0.0,
    )
    session = factory.create()

    assert session.snapshot_dump_attempts == 2
    assert session.snapshot_dump_interval == 0.0
    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 2


# --- adb transport stall guard (driver_call_timeout) ----------------------


class StallingOnceDevice(SnapshotDevice):
    """First dump blocks forever (the measured ~60s adb TCP stall)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stall_started = False

    def dump_hierarchy(self):
        self.dump_count += 1
        if self.dump_count == 1:
            self.stall_started = True
            import threading

            threading.Event().wait()  # blocks until process exit
        return FakeDevice.dump_hierarchy(self)


class AlwaysStallingDevice(SnapshotDevice):
    def dump_hierarchy(self):
        self.dump_count += 1
        import threading

        threading.Event().wait()
        return FakeDevice.dump_hierarchy(self)  # unreachable


class StallingAppCurrentDevice(SnapshotDevice):
    def app_current(self):
        import threading

        threading.Event().wait()
        return {"package": "com.example", "activity": ".Home"}  # unreachable


def test_stalled_dump_is_abandoned_and_retried(tmp_path):
    """A blocked dump() is abandoned at the timeout and the retry succeeds."""
    device = StallingOnceDevice()
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_attempts=3,
        snapshot_dump_interval=0.0,
        driver_call_timeout=0.3,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 2, "the stalled dump must be retried"
    assert len(session._stall_events) == 1
    assert session._stall_events[0]["op"] == "dump"
    assert session._stall_events[0]["timeout_s"] == 0.3
    assert any(
        "search_src_text" in (e.get("resource_id") or "")
        for e in result.data.get("elements", [])
    )


def test_persistent_stall_degrades_after_exhausted_retries(tmp_path):
    device = AlwaysStallingDevice()
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_attempts=2,
        snapshot_dump_interval=0.0,
        driver_call_timeout=0.2,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is False
    assert "timed out" in result.message
    assert device.dump_count == 2
    assert len(session._stall_events) == 2
    assert all(e["op"] == "dump" for e in session._stall_events)


def test_stalled_app_current_keeps_tolerance_contract(tmp_path):
    """A blocked app_current() degrades to (None, None): check skipped,
    single dump succeeds, stall recorded for observability."""
    device = StallingAppCurrentDevice()
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_interval=0.0,
        driver_call_timeout=0.2,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 1
    assert len(session._stall_events) == 1
    assert session._stall_events[0]["op"] == "app_current"
    assert result.data.get("package_name") is None


def test_driver_call_timeout_zero_disables_guard(tmp_path):
    """timeout=0 restores the legacy synchronous call path."""
    device = SnapshotDevice()
    session = Uia2Session(device, artifact_root=tmp_path, driver_call_timeout=0.0)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert session._stall_events == []


def test_session_factory_threads_driver_call_timeout(tmp_path):
    from adapters.uia2 import Uia2SessionFactory

    device = SnapshotDevice()
    factory = Uia2SessionFactory(lambda: device, driver_call_timeout=5.0)
    session = factory.create()

    assert session.driver_call_timeout == 5.0


# --- foreground shell fast path (small-payload app_current) ----------------


FOCUS_LINE = (
    "  mCurrentFocus=Window{5b8e2a1 u0 com.example/com.example.HomeActivity}\n"
)
RESUMED_LINE = (
    "  mResumedActivity: ActivityRecord{9a1b2c3 u0 com.example/"
    ".OtherActivity t42}\n"
)


class ShellOutput:
    """uiautomator2 ShellResponse-shaped double (output + returncode)."""

    def __init__(self, output, returncode=0):
        self.output = output
        self.returncode = returncode


class ShellFastPathDevice(SnapshotDevice):
    """Answers device-side grep with a mCurrentFocus line; counts calls."""

    def __init__(self, responses=None, shell_raises=False, **kwargs):
        super().__init__(**kwargs)
        self.shell_commands = []
        self.shell_responses = responses or {}
        self.shell_raises = shell_raises
        self.app_current_calls = 0

    def shell(self, cmdargs, timeout=60):
        self.shell_commands.append(cmdargs)
        if self.shell_raises:
            raise RuntimeError("shell died")
        for needle, response in self.shell_responses.items():
            if needle in cmdargs:
                return response
        return ShellOutput("", returncode=1)

    def app_current(self):
        self.app_current_calls += 1
        return {"package": "com.example", "activity": ".Home"}


def test_shell_fast_path_resolves_foreground_without_app_current(tmp_path):
    device = ShellFastPathDevice(
        responses={"mCurrentFocus": ShellOutput(FOCUS_LINE)}
    )
    session = Uia2Session(device, artifact_root=tmp_path)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.shell_commands == ["dumpsys window windows | grep mCurrentFocus"]
    assert device.app_current_calls == 0
    assert result.data.get("package_name") == "com.example"
    assert session._stall_events == []


def test_shell_fast_path_falls_back_to_resumed_activity(tmp_path):
    device = ShellFastPathDevice(
        responses={"mResumedActivity": ShellOutput(RESUMED_LINE)}
    )
    session = Uia2Session(device, artifact_root=tmp_path)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert len(device.shell_commands) == 2
    assert device.shell_commands[1] == (
        "dumpsys activity activities | grep mResumedActivity"
    )
    assert device.app_current_calls == 0
    assert result.data.get("package_name") == "com.example"


def test_shell_fast_path_falls_back_to_app_current_on_grep_miss(tmp_path):
    """No grep match (empty output) -> the legacy app_current path runs."""
    device = ShellFastPathDevice()
    session = Uia2Session(device, artifact_root=tmp_path)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.app_current_calls == 1
    assert result.data.get("package_name") == "com.example"
    assert session._stall_events == []


def test_shell_fast_path_falls_back_to_app_current_on_exception(tmp_path):
    device = ShellFastPathDevice(shell_raises=True)
    session = Uia2Session(device, artifact_root=tmp_path)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.app_current_calls == 1
    assert result.data.get("package_name") == "com.example"
    assert session._stall_events == []


def test_shell_fast_path_accepts_plain_string_shell(tmp_path):
    """adbutils shell() returns a bare str; both shapes must parse."""
    device = ShellFastPathDevice(responses={"mCurrentFocus": FOCUS_LINE})
    session = Uia2Session(device, artifact_root=tmp_path)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.app_current_calls == 0
    assert result.data.get("package_name") == "com.example"


def test_shell_fast_path_never_used_when_disabled(tmp_path):
    device = ShellFastPathDevice(
        responses={"mCurrentFocus": ShellOutput(FOCUS_LINE)}
    )
    session = Uia2Session(device, artifact_root=tmp_path, foreground_shell_query=False)

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.shell_commands == []
    assert device.app_current_calls == 1


class StallingShellDevice(ShellFastPathDevice):
    def shell(self, cmdargs, timeout=60):
        import threading

        self.shell_commands.append(cmdargs)
        threading.Event().wait()  # blocks until process exit
        return ShellOutput(FOCUS_LINE)  # unreachable


def test_stalled_shell_query_records_stall_and_skips_app_current(tmp_path):
    """A shell query stuck on the transport records the stall and returns
    (None, None) WITHOUT falling back to the 40-140KB app_current payloads:
    the transport is flapping right now, so large payloads would just
    extend the stall."""
    device = StallingShellDevice()
    session = Uia2Session(
        device,
        artifact_root=tmp_path,
        snapshot_dump_interval=0.0,
        driver_call_timeout=0.2,
    )

    result = session.execute_action("semantic_snapshot", refresh=True)

    assert result.success is True
    assert device.dump_count == 1
    assert device.app_current_calls == 0
    assert len(session._stall_events) == 1
    assert session._stall_events[0]["op"] == "app_current_shell"
    assert session._stall_events[0]["timeout_s"] == 0.2
    assert result.data.get("package_name") is None


def test_session_factory_threads_foreground_shell_query(tmp_path):
    from adapters.uia2 import Uia2SessionFactory

    device = SnapshotDevice()
    factory = Uia2SessionFactory(lambda: device, foreground_shell_query=False)
    session = factory.create()

    assert session.foreground_shell_query is False


def test_call_with_timeout_passthrough_and_errors():
    from adapters.uia2.session import _call_with_timeout

    value, error = _call_with_timeout(lambda: 42, 1.0)
    assert value == 42 and error is None

    def boom():
        raise RuntimeError("nope")

    value, error = _call_with_timeout(boom, 1.0)
    assert value is None and "nope" in error
    # Non-positive timeout: synchronous, disabled cap.
    value, error = _call_with_timeout(lambda: 7, 0)
    assert value == 7 and error is None

    def slow_boom():
        import threading

        threading.Event().wait()
        raise RuntimeError("unreachable")

    value, error = _call_with_timeout(slow_boom, 0.1)
    assert value is None and "timed out" in error
