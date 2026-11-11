# -*- coding: utf-8 -*-
"""Stale-ref guard tests (device-confirmed 2026-11-11).

Real-device evidence (cloud phone 2, SM-F900F): a ref issued by one dump
silently rebound to a DIFFERENT node after the warm cache expired and the
screen changed -- the Settings search box ``@1`` resolved, on the launcher,
to the clock widget, and ``element_bounds`` reported success. A mis-tap on
an unrelated node is worse than a failed step, so a stale ref now fails
closed unless the fresh dump provably describes the same node.
"""
from adapters.uia2 import Uia2Session
from tests.adapters.uia2.test_distill import _node
from tests.adapters.uia2.test_snapshot_session import SnapshotDevice, make_session


def _screen(entries):
    """Hierarchy XML whose interactable children are the given entries."""
    children = "".join(
        _node(
            text=entry["text"],
            resource_id=entry.get("resource_id", ""),
            cls=entry.get("cls", "android.widget.TextView"),
            clickable=True,
            bounds=entry["bounds"],
        )
        for entry in entries
    )
    return "".join(
        [
            '<hierarchy rotation="0">',
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=children,
            ),
            "</hierarchy>",
        ]
    )


_SETTINGS = _screen(
    [
        {"text": "搜索", "resource_id": "com.android.settings:id/search_action_bar",
         "bounds": "[32,164][796,252]"},
        {"text": "我的设备", "bounds": "[0,426][827,549]"},
    ]
)

_LAUNCHER = _screen(
    [
        {"text": "数字时钟 11月11日", "resource_id": "com.android.launcher3.adapt:id/workspace",
         "bounds": "[0,0][827,1792]"},
        {"text": "应用宝", "bounds": "[0,300][400,500]"},
    ]
)


class TwoScreenDevice(SnapshotDevice):
    """First dump is the Settings screen, every later dump is the launcher."""

    def __init__(self, **kwargs):
        super().__init__(hierarchy=_SETTINGS, **kwargs)
        self._first = True

    def dump_hierarchy(self):
        if self._first:
            self._first = False
            return _SETTINGS
        return _LAUNCHER


def test_stale_ref_fails_closed_after_the_screen_changed():
    """Device-confirmed defect: @1 issued on Settings must not resolve to
    the launcher's clock widget once the screen changed."""
    device = TwoScreenDevice()
    session, _ = make_session(device=device, snapshot_ttl=0)

    snapshot = session.execute_action("semantic_snapshot", refresh=True)
    assert snapshot.success is True

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "stale" in result.message
    assert not any(call[0] == "click" for call in device.calls)


def test_stale_ref_failure_is_reported_by_element_bounds():
    device = TwoScreenDevice()
    session, _ = make_session(device=device, snapshot_ttl=0)

    session.execute_action("semantic_snapshot", refresh=True)

    result = session.execute_action("element_bounds", selector="@1", by="ref")

    assert result.success is False
    assert "stale" in result.message
    assert result.data is None


def test_ref_stays_valid_when_the_same_node_is_still_on_screen():
    """The guard must not fire when the fresh dump shows the same widget
    (same resource-id) -- that is the normal observation/action pattern."""
    device = SnapshotDevice(hierarchy=_SETTINGS)
    session, _ = make_session(device=device, snapshot_ttl=0)

    session.execute_action("semantic_snapshot", refresh=True)
    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    assert ("click", 414, 208) in device.calls


def test_ref_survives_a_scroll_that_moves_the_row():
    """A scrolled list row keeps its text but moves: same role + text and
    unique in the snapshot means the same target, so the ref still works."""

    class ScrollingDevice(SnapshotDevice):
        def __init__(self):
            super().__init__(hierarchy=_SETTINGS)
            self._dumps = 0

        def dump_hierarchy(self):
            self._dumps += 1
            if self._dumps == 1:
                return _SETTINGS
            return _screen(
                [
                    {"text": "搜索", "resource_id": "com.android.settings:id/search_action_bar",
                     "bounds": "[32,64][796,152]"},
                    {"text": "我的设备", "bounds": "[0,300][827,423]"},
                ]
            )

    device = ScrollingDevice()
    session, _ = make_session(device=device, snapshot_ttl=0)

    session.execute_action("semantic_snapshot", refresh=True)
    result = session.execute_action("tap", selector="@2", by="ref")

    assert result.success is True
    assert ("click", 413, 361) in device.calls


def test_ref_issued_by_a_snapshot_is_pinned_to_that_snapshot():
    """Two snapshots in a row: the ref is validated against the one that
    issued it, not against whichever dump happens to be warm."""
    device = TwoScreenDevice()
    session, _ = make_session(device=device, snapshot_ttl=0)

    session.execute_action("semantic_snapshot", refresh=True)
    # A second observation re-issues the refs against the launcher screen.
    session.execute_action("semantic_snapshot", refresh=True)

    result = session.execute_action("tap", selector="@1", by="ref")

    # @1 now legitimately denotes the launcher's clock widget -- the
    # issuer and the current dump agree, so the tap is allowed.
    assert result.success is True
    assert ("click", 413, 896) in device.calls


def test_ref_without_a_prior_observation_resolves_against_the_current_screen():
    """A ref that no observation ever handed out means "position N in the
    current dump" -- there is no earlier expectation to contradict, so it
    stays usable (the kit's ``find_element`` contract relies on it)."""
    device = SnapshotDevice(hierarchy=_SETTINGS)
    session, _ = make_session(device=device, snapshot_ttl=0)

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is True
    assert ("click", 414, 208) in device.calls


def test_scroll_ref_is_usable_after_the_scroll():
    """``scroll_into_view`` hands a ref back to the caller; that ref must
    stay usable for the tap that follows (the documented scroll->tap flow)."""
    device = SnapshotDevice(hierarchy=_SETTINGS)
    session, _ = make_session(device=device, snapshot_ttl=0)

    scroll = session.execute_action("scroll_into_view", selector="我的设备", by="text")
    assert scroll.success is True

    result = session.execute_action("tap", selector="@%d" % scroll.data["ref"], by="ref")

    assert result.success is True
    assert ("click", 413, 487) in device.calls


def test_ref_fails_closed_when_the_foreground_app_changed():
    """Two apps can show the same label; the foreground package is the
    decisive signal that the ref crossed a screen boundary."""
    device = SnapshotDevice(hierarchy=_SETTINGS)
    session, _ = make_session(device=device, snapshot_ttl=0)

    session.execute_action("semantic_snapshot", refresh=True)
    device.current_result = {"package": "com.android.launcher3.adapt", "activity": ".Launcher"}

    result = session.execute_action("tap", selector="@1", by="ref")

    assert result.success is False
    assert "foreground app changed" in result.message
    assert not any(call[0] == "click" for call in device.calls)
