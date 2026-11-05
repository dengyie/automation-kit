"""Composite ``uiautomator`` descriptor selector: dispatch, validation, scope.

The descriptor by accepts a whitelisted multi-kwarg dict and dispatches it
as one ``Device(**kwargs)`` lookup, mirroring combined native UiSelector
chains (``resourceId(...).instance(N)``). Snapshot-scoped operations
(scroll_into_view / ref resolution) intentionally stay single-key.
"""

from tests.adapters.uia2._fakes import FakeDevice, FakeUiObject

from adapters.uia2 import Uia2Session


def make_session(device=None):
    device = device or FakeDevice()
    return Uia2Session(device), device


def test_tap_composite_descriptor_dispatches_multi_kwarg_lookup():
    session, device = make_session()

    result = session.execute_action(
        "tap",
        by="uiautomator",
        selector={"resourceId": "com.dianping:id/img", "instance": 2},
    )

    assert result.success is True
    assert (
        "selector",
        {"resourceId": "com.dianping:id/img", "instance": 2},
    ) in device.calls


def test_tap_composite_descriptor_clicks_resolved_element():
    device = FakeDevice()
    target = FakeUiObject("composite")
    device.elements[("resourceId", "com.example:id/tile")] = target
    session, _ = make_session(device)

    result = session.execute_action(
        "tap",
        by="uiautomator",
        selector={"resourceId": "com.example:id/tile", "instance": 0},
    )

    assert result.success is True
    assert target.clicked == 1


def test_type_text_composite_descriptor():
    device = FakeDevice()
    field = FakeUiObject("composite-field")
    device.elements[("className", "android.widget.EditText")] = field
    session, _ = make_session(device)

    result = session.execute_action(
        "type_text",
        by="uiautomator",
        selector={"className": "android.widget.EditText", "textContains": "点评"},
        text="hello",
    )

    assert result.success is True
    assert field.clicked == 1
    assert field.cleared == 1
    assert field.sent == [("hello", False)]


def test_element_bounds_composite_descriptor():
    device = FakeDevice()
    tile = FakeUiObject(
        "composite-bounds",
        info={"bounds": {"left": 10, "top": 20, "right": 110, "bottom": 220}},
    )
    device.elements[("resourceId", "com.example:id/tile")] = tile
    session, _ = make_session(device)

    result = session.execute_action(
        "element_bounds",
        by="uiautomator",
        selector={"resourceId": "com.example:id/tile", "instance": 1},
    )

    assert result.success is True
    assert result.data == {"x": 10, "y": 20, "width": 100, "height": 200}


def test_find_element_composite_descriptor_returns_handle():
    session, _ = make_session()

    element = session.find_element(
        "uiautomator",
        {"description": "商家", "instance": 0},
    )

    assert element.identifier.startswith("uiautomator=")
    assert element.exists is True


def test_wait_for_element_composite_descriptor():
    session, device = make_session()

    result = session.execute_action(
        "wait_for_element",
        by="uiautomator",
        selector={"resourceId": "com.example:id/marker"},
        timeout=0.5,
        interval=0.1,
    )

    assert result.success is True
    assert (
        "selector",
        {"resourceId": "com.example:id/marker"},
    ) in device.calls


def test_descriptor_requires_non_empty_dict():
    session, _ = make_session()

    # ``None`` is the "missing selector" path in _tap; non-dict and empty
    # dicts must land on the descriptor validation error.
    for selector in ([], "resourceId=x", {}):
        result = session.execute_action(
            "tap", by="uiautomator", selector=selector
        )
        assert result.success is False, selector
        assert "descriptor dict" in result.message


def test_descriptor_rejects_unknown_keys():
    session, _ = make_session()

    result = session.execute_action(
        "tap",
        by="uiautomator",
        selector={"resourceId": "x", "fromParent": True},
    )

    assert result.success is False
    assert "fromParent" in result.message
    assert "unsupported uiautomator descriptor key" in result.message


def test_descriptor_rejects_bad_string_values():
    session, _ = make_session()

    result = session.execute_action(
        "tap",
        by="uiautomator",
        selector={"resourceId": ""},
    )

    assert result.success is False
    assert "non-empty string" in result.message


def test_descriptor_rejects_bad_instance_values():
    session, _ = make_session()

    for instance in (-1, 1.5, True, "2", None):
        result = session.execute_action(
            "tap",
            by="uiautomator",
            selector={"resourceId": "x", "instance": instance},
        )
        assert result.success is False, instance
        assert "non-negative integer" in result.message


def test_dict_selector_requires_uiautomator_by():
    session, _ = make_session()

    for by in (None, "text", "id"):
        result = session.execute_action(
            "tap", by=by, selector={"resourceId": "x"}
        )
        assert result.success is False, by
        assert "by='uiautomator'" in result.message


def test_scroll_into_view_rejects_composite_descriptor():
    """Snapshot-scoped operations stay single-key by design."""
    session, _ = make_session()

    result = session.execute_action(
        "scroll_into_view",
        by="uiautomator",
        selector={"resourceId": "x"},
    )

    assert result.success is False
    assert "scroll_into_view matches snapshots" in result.message


def test_unsupported_by_message_lists_uiautomator():
    session, _ = make_session()

    result = session.execute_action("tap", by="nonsense", selector="x")

    assert result.success is False
    assert "uiautomator" in result.message
