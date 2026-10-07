import pytest

from adapters.errors import AdapterArtifactError, AdapterStartupError
from adapters.uia2 import Uia2Session, Uia2SessionFactory
from tests.adapters.uia2._fakes import (
    FakeDevice,
    FakePilImage,
    FakeUiObject,
    FlakyDevice,
)


def make_session(**kwargs):
    device = kwargs.pop("device", None) or FakeDevice()
    return Uia2Session(device, **kwargs), device


def make_isolated_session(tmp_path, **kwargs):
    device = kwargs.pop("device", None) or FakeDevice()
    return Uia2Session(device, artifact_root=tmp_path, **kwargs), device


def test_session_info_reports_uia2_android():
    session, _ = make_session()

    assert session.info.driver_name == "uia2"
    assert session.info.platform == "android"


def test_launch_app_success():
    session, device = make_session()

    result = session.execute_action("launch_app", app_id="cn.damai")

    assert result.success is True
    assert ("app_start", "cn.damai") in device.calls


def test_launch_app_requires_app_id():
    session, _ = make_session()

    result = session.execute_action("launch_app")

    assert result.success is False
    assert "app_id" in result.message


def test_terminate_app_dispatches_to_device():
    session, device = make_session()

    result = session.execute_action("terminate_app", app_id="cn.damai")

    assert result.success is True
    assert ("app_stop", "cn.damai") in device.calls


def test_tap_by_selector_resolves_element():
    session, device = make_session()

    result = session.execute_action("tap", selector="登录", by="text")

    assert result.success is True
    assert device.calls[0] == ("selector", {"text": "登录"})
    assert device.elements[("text", "登录")].clicked == 1


def test_tap_defaults_to_text_locator():
    session, device = make_session()

    result = session.execute_action("tap", selector="登录")

    assert result.success is True
    assert device.calls[0] == ("selector", {"text": "登录"})


_SNAPSHOT = {"bounds": {"left": 68, "top": 632, "right": 140, "bottom": 674}}


def make_session_with_bounds(info):
    device = FakeDevice(
        elements={("text", "口味"): FakeUiObject("text=口味", info=info)}
    )
    return Uia2Session(device), device


def test_element_bounds_reads_element_snapshot():
    session, _ = make_session_with_bounds(_SNAPSHOT)

    result = session.execute_action("element_bounds", selector="口味", by="text")

    assert result.success is True
    assert result.data == {"x": 68, "y": 632, "width": 72, "height": 42}


def test_element_bounds_reports_unavailable_snapshot():
    session, _ = make_session_with_bounds(None)

    result = session.execute_action("element_bounds", selector="口味", by="text")

    assert result.success is False
    assert "bounds unavailable" in result.message


def test_element_bounds_reports_unavailable_rect():
    session, _ = make_session_with_bounds({"bounds": {}})

    result = session.execute_action("element_bounds", selector="口味", by="text")

    assert result.success is False
    assert "bounds unavailable" in result.message


def test_element_bounds_requires_selector():
    session, _ = make_session()

    result = session.execute_action("element_bounds")

    assert result.success is False
    assert "selector" in result.message


def test_tap_by_coordinate():
    session, device = make_session()

    result = session.execute_action("tap", x=100, y=200)

    assert result.success is True
    assert ("click", 100.0, 200.0) in device.calls


def test_tap_requires_selector_or_coordinates():
    session, _ = make_session()

    result = session.execute_action("tap")

    assert result.success is False
    assert "selector or x/y" in result.message


def test_click_is_alias_of_tap():
    session, device = make_session()

    result = session.execute_action("click", selector="确认", by="id")

    assert result.success is True
    assert device.calls[0] == ("selector", {"resourceId": "确认"})


def test_type_text_clears_then_sends_by_default():
    session, device = make_session()

    result = session.execute_action("type_text", selector="搜索", text="门票")

    assert result.success is True
    element = device.elements[("text", "搜索")]
    assert element.cleared == 1
    assert element.sent == [("门票", False)]


def test_type_text_without_clear_keeps_content():
    session, device = make_session()

    result = session.execute_action(
        "type_text", selector="搜索", text="门票", clear=False
    )

    assert result.success is True
    element = device.elements[("text", "搜索")]
    assert element.cleared == 0


def test_type_text_requires_text():
    session, _ = make_session()

    result = session.execute_action("type_text", selector="搜索")

    assert result.success is False
    assert "text" in result.message


def test_swipe_success():
    session, device = make_session()

    result = session.execute_action(
        "swipe", start_x=1, start_y=2, end_x=3, end_y=4, duration=0.5
    )

    assert result.success is True
    assert ("swipe", 1.0, 2.0, 3.0, 4.0, 0.5) in device.calls


def test_swipe_requires_all_coordinates():
    session, _ = make_session()

    result = session.execute_action("swipe", start_x=1, start_y=2)

    assert result.success is False
    assert "end_x" in result.message


def test_swipe_rejects_non_numeric_coordinates():
    session, _ = make_session()

    result = session.execute_action(
        "swipe", start_x="a", start_y=2, end_x=3, end_y=4
    )

    assert result.success is False
    assert "start_x must be a number" in result.message


def test_unknown_action_falls_back_to_device_method():
    session, device = make_session()
    device.toast_message = lambda **kwargs: "shown"

    result = session.execute_action("toast_message", wait=True)

    assert result.success is True


def test_unknown_action_fails_cleanly():
    session, _ = make_session()

    result = session.execute_action("no_such_method")

    assert result.success is False
    assert "unsupported uia2 action" in result.message


def test_wait_for_element_success_after_retry():
    session, _ = make_session()
    session.driver = FlakyDevice(fail_times=2)

    result = session.execute_action(
        "wait_for_element", selector="设置", timeout=5, interval=0
    )

    assert result.success is True
    assert result.data == "text=设置"


def test_wait_for_element_times_out():
    session, device = make_session()
    device.missing.add(("text", "不存在"))

    result = session.execute_action(
        "wait_for_element", selector="不存在", timeout=0.05, interval=0
    )

    assert result.success is False
    assert "timed out" in result.message


def test_wait_for_element_rejects_unknown_by():
    session, _ = make_session()

    result = session.execute_action(
        "wait_for_element", selector="设置", by="uiautomator"
    )

    assert result.success is False
    assert "unsupported by" in result.message


def test_wait_for_element_rejects_empty_selector():
    session, _ = make_session()

    result = session.execute_action("wait_for_element", selector="  ")

    assert result.success is False
    assert "non-empty" in result.message


def test_xpath_lookup_dispatches_to_device_xpath():
    session, device = make_session()

    result = session.execute_action("click", selector="//node", by="xpath")

    assert result.success is True
    assert device.calls[0] == ("xpath", "//node")


def test_contains_locators_map_to_native_kwargs():
    session, device = make_session()

    contains = session.execute_action(
        "tap", selector="搜索", by="text-contains"
    )
    description = session.execute_action(
        "tap", selector="搜索", by="description-contains"
    )

    assert contains.success is True
    assert description.success is True
    assert ("selector", {"textContains": "搜索"}) in device.calls
    assert ("selector", {"descriptionContains": "搜索"}) in device.calls


def test_capture_artifact_screenshot_from_pil_image(tmp_path):
    session, device = make_isolated_session(tmp_path)
    image = FakePilImage()
    device.screenshot_result = image

    handle = session.capture_artifact("screenshot", "home.png")

    assert handle.path.is_file()
    assert image.saved_to == str(handle.path)


def test_capture_artifact_screenshot_from_bytes(tmp_path):
    session, device = make_isolated_session(tmp_path)
    device.screenshot_result = b"raw-png"

    handle = session.capture_artifact("screenshot", "home.png")

    assert handle.path.read_bytes() == b"raw-png"


def test_capture_artifact_screenshot_requires_saveable_image(tmp_path):
    session, device = make_isolated_session(tmp_path)
    device.screenshot_result = object()

    with pytest.raises(AdapterArtifactError):
        session.capture_artifact("screenshot", "home.png")


def test_capture_artifact_screenshot_driver_failure(tmp_path):
    session, device = make_isolated_session(tmp_path)

    def boom():
        raise RuntimeError("device offline")

    device.screenshot_result = boom

    with pytest.raises(AdapterArtifactError):
        session.capture_artifact("screenshot", "home.png")


def test_capture_artifact_ui_tree_writes_hierarchy(tmp_path):
    session, device = make_isolated_session(tmp_path)
    device.hierarchy_result = "<?xml version='1.0'?>"

    handle = session.capture_artifact("ui_tree", "tree.xml")

    assert handle.path.read_text(encoding="utf-8") == "<?xml version='1.0'?>"
    assert handle.artifact_type == "ui_tree"


def test_capture_artifact_rejects_unknown_type(tmp_path):
    session, _ = make_isolated_session(tmp_path)

    with pytest.raises(AdapterArtifactError):
        session.capture_artifact("video", "clip.mp4")


def test_capture_artifact_fails_when_nothing_written(tmp_path):
    session, device = make_isolated_session(tmp_path)
    device.screenshot_result = FakePilImage(persist=False)

    with pytest.raises(AdapterArtifactError):
        session.capture_artifact("screenshot", "home.png")


def test_factory_wraps_startup_failure():
    def broken():
        raise RuntimeError("adb not found")

    factory = Uia2SessionFactory(broken)

    with pytest.raises(AdapterStartupError):
        factory.create()


def test_factory_creates_session():
    device = FakeDevice()
    factory = Uia2SessionFactory(lambda: device)

    session = factory.create()

    assert isinstance(session, Uia2Session)
    assert session.driver is device
