import pytest
from pathlib import Path

from adapters.errors import AdapterArtifactError, AdapterStartupError
from adapters.phone_playwright import (
    PhonePlaywrightElement,
    PhonePlaywrightSession,
    PhonePlaywrightSessionFactory,
)
from automation_core.drivers import DriverSession, ElementHandle, ElementLookupSession
from tests.adapters.phone_playwright._fakes import (
    FakeActionResult,
    FakePhoneLocator,
    FakePhonePage,
    FakePhoneSnapshot,
)


def make_session(**kwargs):
    page = kwargs.pop("page", None) or FakePhonePage()
    return PhonePlaywrightSession(page, **kwargs), page


def make_isolated_session(tmp_path, **kwargs):
    page = kwargs.pop("page", None) or FakePhonePage()
    return PhonePlaywrightSession(page, artifact_root=tmp_path, **kwargs), page


def test_session_info_reports_phone_playwright_android():
    session, _ = make_session()

    assert session.info.driver_name == "phone_playwright"
    assert session.info.platform == "android"
    assert session.info.identifier == "phone_playwright-session"


def test_session_implements_contracts():
    session, _ = make_session()

    assert isinstance(session, DriverSession)
    assert isinstance(session, ElementLookupSession)


def test_find_element_success():
    session, page = make_session()

    el = session.find_element(by="text", selector="设置")

    assert isinstance(el, ElementHandle)
    assert isinstance(el, PhonePlaywrightElement)
    assert ("locator", "text=设置") in page.calls


def test_find_element_by_compact_ref():
    session, page = make_session()

    el = session.find_element(by="compact", selector="5")

    assert isinstance(el, ElementHandle)
    assert ("locator", "@5") in page.calls


def test_find_element_raises_on_invalid_selector():
    session, _ = make_session()

    with pytest.raises(KeyError) as exc_info:
        session.find_element(by="text", selector="")

    assert "non-empty string" in str(exc_info.value)


def test_find_element_raises_when_missing():
    page = FakePhonePage(missing=("text=消失",))
    session, _ = make_session(page=page)

    with pytest.raises(KeyError) as exc_info:
        session.find_element(by="text", selector="消失")

    assert "locator not found" in str(exc_info.value)


def test_launch_app_success():
    session, page = make_session()

    res = session.execute_action("launch_app", app_id="com.tencent.mm")

    assert res.success is True
    assert ("app_start", "com.tencent.mm") in page.calls


def test_launch_app_requires_app_id():
    session, _ = make_session()

    res = session.execute_action("launch_app")

    assert res.success is False
    assert "app_id" in res.message


def test_terminate_app_success():
    session, page = make_session()

    res = session.execute_action("terminate_app", app_id="com.tencent.mm")

    assert res.success is True
    assert ("app_stop", "com.tencent.mm") in page.calls


def test_terminate_app_requires_app_id():
    session, _ = make_session()

    res = session.execute_action("terminate_app")

    assert res.success is False
    assert "app_id" in res.message


def test_tap_by_selector():
    session, page = make_session()

    res = session.execute_action("tap", selector="确认", by="text")

    assert res.success is True
    assert ("locator", "text=确认") in page.calls
    assert page.locators["text=确认"].clicked == 1


def test_click_alias():
    session, page = make_session()

    res = session.execute_action("click", selector="确认")

    assert res.success is True
    assert ("locator", "text=确认") in page.calls
    assert page.locators["text=确认"].clicked == 1


def test_tap_by_coordinates():
    session, page = make_session()

    res = session.execute_action("tap", x=120, y=340)

    assert res.success is True
    assert ("click", 120.0, 340.0) in page.calls


def test_tap_missing_parameters():
    session, _ = make_session()

    res = session.execute_action("tap")

    assert res.success is False
    assert "selector or x/y" in res.message


def test_type_text_success():
    session, page = make_session()

    res = session.execute_action("type_text", selector="输入框", text="搜索关键词")

    assert res.success is True
    assert page.locators["text=输入框"].filled == ["搜索关键词"]


def test_type_text_missing_parameters():
    session, _ = make_session()

    res = session.execute_action("type_text", selector="输入框")
    assert res.success is False
    assert "text" in res.message

    res2 = session.execute_action("type_text", text="foo")
    assert res2.success is False
    assert "selector" in res2.message


def test_swipe_direction():
    session, page = make_session()

    res = session.execute_action("swipe", direction="up", distance_ratio=0.6)

    assert res.success is True
    assert any(c[0] == "swipe" and c[2].get("direction") == "up" for c in page.calls)


def test_swipe_coordinates():
    session, page = make_session()

    res = session.execute_action(
        "swipe", start_x=100, start_y=500, end_x=100, end_y=100, duration=0.2
    )

    assert res.success is True
    assert any(c[0] == "swipe" for c in page.calls)


def test_swipe_invalid_direction():
    session, _ = make_session()

    res = session.execute_action("swipe", direction="diagonal")

    assert res.success is False
    assert "invalid swipe direction" in res.message


def test_scroll_into_view_success():
    session, page = make_session()

    res = session.execute_action("scroll_into_view", selector="关于手机", max_swipes=3)

    assert res.success is True
    loc = page.locators["text=关于手机"]
    assert len(loc.scroll_calls) == 1
    assert loc.scroll_calls[0]["max_swipes"] == 3


def test_scroll_into_view_requires_selector():
    session, _ = make_session()

    res = session.execute_action("scroll_into_view")

    assert res.success is False
    assert "selector" in res.message


def test_element_bounds_action():
    page = FakePhonePage()
    page.locators["text=图标"] = FakePhoneLocator(
        "text=图标", bounds={"left": 10, "top": 20, "right": 60, "bottom": 80}
    )
    session, _ = make_session(page=page)

    res = session.execute_action("element_bounds", selector="图标")

    assert res.success is True
    assert res.data == {"x": 10, "y": 20, "width": 50, "height": 60}


def test_wait_for_element_success():
    session, _ = make_session()

    res = session.execute_action("wait_for_element", selector="首页")

    assert res.success is True
    assert res.data == "text=首页"


def test_wait_for_element_timeout():
    page = FakePhonePage(missing=("text=永远不出现",))
    session, _ = make_session(page=page)

    res = session.execute_action(
        "wait_for_element", selector="永远不出现", timeout=0.1, interval=0.05
    )

    assert res.success is False
    assert "timed out waiting for element" in res.message


def test_semantic_snapshot_action():
    session, page = make_session()

    res = session.execute_action("semantic_snapshot")

    assert res.success is True
    assert "Login" in res.data
    assert any(c[0] == "snapshot" for c in page.calls)


def test_press_back_and_home():
    session, page = make_session()

    res_back = session.execute_action("press_back")
    res_home = session.execute_action("press_home")

    assert res_back.success is True
    assert res_home.success is True
    assert ("press_back",) in page.calls
    assert ("press_home",) in page.calls


def test_press_back_unsupported():
    class NoBackPage:
        pass

    session = PhonePlaywrightSession(NoBackPage())
    res = session.execute_action("press_back")

    assert res.success is False
    assert "driver does not support press_back" in res.message


def test_press_home_unsupported():
    class NoHomePage:
        pass

    session = PhonePlaywrightSession(NoHomePage())
    res = session.execute_action("press_home")

    assert res.success is False
    assert "driver does not support press_home" in res.message


def test_scroll_into_view_invalid_max_swipes():
    session, _ = make_session()

    res = session.execute_action("scroll_into_view", selector="target", max_swipes="invalid")

    assert res.success is False
    assert "max_swipes must be a number" in res.message


def test_wait_for_element_respects_visibility_retry():
    calls = 0

    def visibility_state():
        nonlocal calls
        calls += 1
        return calls >= 3

    page = FakePhonePage()
    page.locators["text=延时出现"] = FakePhoneLocator(
        "text=延时出现", visible=visibility_state
    )
    session, _ = make_session(page=page)

    res = session.execute_action(
        "wait_for_element", selector="延时出现", timeout=1.0, interval=0.05
    )

    assert res.success is True
    assert res.data == "text=延时出现"
    assert calls >= 3


def test_wait_for_element_fails_when_invisible():
    page = FakePhonePage()
    page.locators["text=隐形元素"] = FakePhoneLocator("text=隐形元素", visible=False)
    session, _ = make_session(page=page)

    res = session.execute_action(
        "wait_for_element", selector="隐形元素", timeout=0.1, interval=0.03
    )

    assert res.success is False
    assert "timed out waiting for element" in res.message


def test_unsupported_action():
    session, _ = make_session()

    res = session.execute_action("unknown_magic_action")

    assert res.success is False
    assert "unsupported phone_playwright action" in res.message


def test_capture_artifact_screenshot(tmp_path):
    session, _ = make_isolated_session(tmp_path)

    artifact = session.capture_artifact("screenshot", "main_screen")

    assert artifact.artifact_type == "screenshot"
    assert artifact.path.is_file()
    assert artifact.path.read_bytes() == b"\x89PNG\r\n\x1a\nfake"


def test_capture_artifact_ui_tree(tmp_path):
    session, _ = make_isolated_session(tmp_path)

    artifact = session.capture_artifact("ui_tree", "dom_dump")

    assert artifact.artifact_type == "ui_tree"
    assert artifact.path.is_file()
    assert artifact.path.read_text(encoding="utf-8") == "<hierarchy></hierarchy>"


def test_capture_artifact_semantic_snapshot(tmp_path):
    session, _ = make_isolated_session(tmp_path)

    artifact = session.capture_artifact("semantic_snapshot", "semantic_snap")

    assert artifact.artifact_type == "semantic_snapshot"
    assert artifact.path.is_file()
    assert "Login" in artifact.path.read_text(encoding="utf-8")


def test_capture_artifact_unsupported_type(tmp_path):
    session, _ = make_isolated_session(tmp_path)

    with pytest.raises(AdapterArtifactError) as exc_info:
        session.capture_artifact("video_stream", "screen_rec")

    assert "unsupported phone_playwright artifact type" in str(exc_info.value)


def test_session_factory_create_success():
    factory = PhonePlaywrightSessionFactory(lambda: FakePhonePage())

    session = factory.create()

    assert isinstance(session, PhonePlaywrightSession)
    assert session.info.driver_name == "phone_playwright"


def test_session_factory_create_failure():
    def broken_factory():
        raise ConnectionRefusedError("device offline")

    factory = PhonePlaywrightSessionFactory(broken_factory)

    with pytest.raises(AdapterStartupError) as exc_info:
        factory.create()

    assert "failed to create phone_playwright driver" in str(exc_info.value)


def test_scroll_into_view_fails_when_still_not_visible():
    page = FakePhonePage()
    page.locators["text=深层元素"] = FakePhoneLocator("text=深层元素", visible=False)
    session, _ = make_session(page=page)

    res = session.execute_action("scroll_into_view", selector="深层元素", max_swipes=2)

    assert res.success is False
    assert "timed out scrolling element into view" in res.message


def test_wait_for_element_delegates_to_locator_wait_for():
    class WaitableLocator(FakePhoneLocator):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.wait_for_calls = []

        def wait_for(self, state="visible", timeout_s=5.0):
            self.wait_for_calls.append({"state": state, "timeout_s": timeout_s})
            return FakeActionResult(success=True, verb="wait_for")

    page = FakePhonePage()
    page.locators["text=快捷等待"] = WaitableLocator("text=快捷等待")
    session, _ = make_session(page=page)

    res = session.execute_action("wait_for_element", selector="快捷等待", timeout=3.0)

    assert res.success is True
    assert res.data == "text=快捷等待"
    assert len(page.locators["text=快捷等待"].wait_for_calls) == 1
    assert page.locators["text=快捷等待"].wait_for_calls[0]["timeout_s"] == 3.0


def test_wait_for_element_delegates_to_locator_wait_for_failure():
    class BrokenWaitableLocator(FakePhoneLocator):
        def wait_for(self, state="visible", timeout_s=5.0):
            return FakeActionResult(success=False, verb="wait_for", error="timeout exceeded")

    page = FakePhonePage()
    page.locators["text=等待超时"] = BrokenWaitableLocator("text=等待超时")
    session, _ = make_session(page=page)

    res = session.execute_action("wait_for_element", selector="等待超时", timeout=0.5)

    assert res.success is False
    assert "timed out waiting for element: 等待超时" in res.message

