"""Deep-coverage tests for PhonePlaywrightSession artifact writing and
parameter-validation edge paths.

The artifact writer duck-types four locator generations for screenshots
(bytes / file path / base64 / PIL-style .save) and three hierarchy
sources (dump_raw_tree > dump_hierarchy > page_source, then a snapshot
JSON fallback); every branch and every failure exit is pinned here.

Note on doubles: BaseFakePhonePage always defines the full method surface,
so "driver does not support X" paths use genuinely bare pages, and
lower-priority hierarchy sources need the higher one silenced with a
class-level ``= None`` override (the writer's ``or`` chain skips None).
"""

import base64
from pathlib import Path

import pytest

from adapters.errors import AdapterArtifactError
from adapters.phone_playwright import PhonePlaywrightSession
from tests.adapters.phone_playwright._fakes import (
    BaseFakePhonePage,
    FakePhoneLocator,
    FakePhoneSnapshot,
)


class Bare:
    """A driver with none of the optional surface (platform only)."""

    platform = "android"


class StaticPage(BaseFakePhonePage):
    """Base page whose injectable results can be replaced per-test."""


def make(page, tmp_path, name="art"):
    return PhonePlaywrightSession(page, artifact_root=tmp_path / name)


# --- screenshot writer matrix -------------------------------------------------


def test_screenshot_written_from_file_path(tmp_path):
    src = tmp_path / "src.png"
    src.write_bytes(b"\x89PNGpath-sourced")
    page = StaticPage()
    page.screenshot_result = str(src)

    artifact = make(page, tmp_path).capture_artifact("screenshot", "shot")

    assert artifact.path.read_bytes() == b"\x89PNGpath-sourced"


def test_screenshot_written_from_base64_string(tmp_path):
    page = StaticPage()
    page.screenshot_result = base64.b64encode(b"b64-png-bytes").decode("ascii")

    artifact = make(page, tmp_path).capture_artifact("screenshot", "shot")

    assert artifact.path.read_bytes() == b"b64-png-bytes"


def test_screenshot_base64_invalid_string_falls_through_to_error(tmp_path):
    """A non-path, non-decodable string hits the .save/raise tail."""

    class Unsaveable:
        pass

    page = StaticPage()
    page.screenshot_result = Unsaveable()

    with pytest.raises(AdapterArtifactError) as e:
        make(page, tmp_path).capture_artifact("screenshot", "shot")
    assert "not saveable" in str(e.value)


def test_screenshot_pil_style_save(tmp_path):
    calls = []

    class FakePIL:
        def save(self, target):
            calls.append(target)
            Path(target).write_bytes(b"pil-saved")

    page = StaticPage()
    page.screenshot_result = FakePIL()

    artifact = make(page, tmp_path).capture_artifact("screenshot", "shot")

    assert artifact.path.read_bytes() == b"pil-saved"
    assert len(calls) == 1


def test_screenshot_unsaveable_object_raises(tmp_path):
    page = StaticPage()
    page.screenshot_result = 42

    with pytest.raises(AdapterArtifactError) as e:
        make(page, tmp_path).capture_artifact("screenshot", "shot")
    assert "not saveable" in str(e.value)


def test_screenshot_capture_raises(tmp_path):
    def boom():
        raise RuntimeError("usb stall")

    page = StaticPage()
    page.screenshot_result = boom

    with pytest.raises(AdapterArtifactError) as e:
        make(page, tmp_path).capture_artifact("screenshot", "shot")
    assert "screenshot capture failed" in str(e.value)


def test_screenshot_no_capture_method_raises(tmp_path):
    with pytest.raises(AdapterArtifactError) as e:
        make(Bare(), tmp_path).capture_artifact("screenshot", "shot")
    assert "does not support screenshot capture" in str(e.value)


def test_screenshot_fallback_methods_screenshot_then_save_screenshot(tmp_path):
    class ScreenshotOnly:
        platform = "android"

        def screenshot(self):
            return b"via-screenshot"

    class SaveScreenshotOnly:
        platform = "android"

        def save_screenshot(self):
            return b"via-save-screenshot"

    for page, expected in (
        (ScreenshotOnly(), b"via-screenshot"),
        (SaveScreenshotOnly(), b"via-save-screenshot"),
    ):
        artifact = make(page, tmp_path, name="art2").capture_artifact(
            "screenshot", "shot"
        )
        assert artifact.path.read_bytes() == expected


# --- hierarchy writer matrix ---------------------------------------------------


def test_hierarchy_from_dump_hierarchy_when_raw_tree_silenced(tmp_path):
    class HierarchyPage(BaseFakePhonePage):
        dump_raw_tree = None  # silence the higher-priority source

        def dump_hierarchy(self):
            return "<hierarchy alt/>"

    artifact = make(HierarchyPage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == "<hierarchy alt/>"


def test_hierarchy_from_page_source_when_both_above_silenced(tmp_path):
    class PageSourcePage(BaseFakePhonePage):
        dump_raw_tree = None
        dump_hierarchy = None

        def page_source(self):
            return "<page-source/>"

    artifact = make(PageSourcePage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == "<page-source/>"


def test_hierarchy_priority_raw_tree_beats_dump_hierarchy(tmp_path):
    class BothPage(BaseFakePhonePage):
        def dump_raw_tree(self):
            return "<raw/>"

        def dump_hierarchy(self):
            return "<alt/>"

    artifact = make(BothPage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == "<raw/>"


def test_hierarchy_non_string_object_serialized_via_model_dump_json(tmp_path):
    class Model:
        def model_dump_json(self, indent=None):
            return '{"model": true}'

    class ObjectDumpPage(BaseFakePhonePage):
        def dump_raw_tree(self):
            return Model()

    artifact = make(ObjectDumpPage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == '{"model": true}'


def test_hierarchy_non_string_plain_object_str_fallback(tmp_path):
    class Plain:
        def __str__(self):
            return "str()-serialized"

    class ObjectDumpPage(BaseFakePhonePage):
        def dump_raw_tree(self):
            return Plain()

    artifact = make(ObjectDumpPage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == "str()-serialized"


def test_hierarchy_snapshot_fallback_with_model_dump_json(tmp_path):
    class BareSnapshotPage:
        platform = "android"

        def snapshot(self):
            class JsonSnapshot(FakePhoneSnapshot):
                def model_dump_json(self, indent=None):
                    return '{"snapshot-json": 1}'

            return JsonSnapshot()

    artifact = make(BareSnapshotPage(), tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == '{"snapshot-json": 1}'


def test_hierarchy_snapshot_fallback_str_plain_snapshot(tmp_path):
    """Plain objects without model_dump_json are str()-serialized."""

    class PlainSnapshot:
        def __str__(self):
            return "plain-snapshot-text"

    class StrOnlySnapshotPage(BaseFakePhonePage):
        dump_raw_tree = None

        def snapshot(self, **kwargs):
            return PlainSnapshot()

    artifact = make(StrOnlySnapshotPage(), tmp_path).capture_artifact(
        "ui_tree", "tree"
    )

    assert artifact.path.read_text(encoding="utf-8") == "plain-snapshot-text"


def test_hierarchy_snapshot_fallback_raises(tmp_path):
    def boom():
        raise RuntimeError("snapshot crashed")

    class SnapshotCrashPage(BaseFakePhonePage):
        dump_raw_tree = None

        def snapshot(self, **kwargs):
            return boom()

    with pytest.raises(AdapterArtifactError) as e:
        make(SnapshotCrashPage(), tmp_path).capture_artifact("ui_tree", "tree")
    assert "hierarchy dump failed" in str(e.value)


def test_hierarchy_no_source_at_all_raises(tmp_path):
    with pytest.raises(AdapterArtifactError) as e:
        make(Bare(), tmp_path).capture_artifact("ui_tree", "tree")
    assert "does not provide UI hierarchy" in str(e.value)


def test_hierarchy_dump_callable_raises(tmp_path):
    def boom():
        raise RuntimeError("dump stalled")

    page = StaticPage()
    page.hierarchy_result = boom

    with pytest.raises(AdapterArtifactError) as e:
        make(page, tmp_path).capture_artifact("ui_tree", "tree")
    assert "hierarchy dump failed" in str(e.value)


def test_hierarchy_static_non_callable_value(tmp_path):
    page = StaticPage()
    page.hierarchy_result = "<static/>"  # dump_fn set but not callable

    artifact = make(page, tmp_path).capture_artifact("ui_tree", "tree")

    assert artifact.path.read_text(encoding="utf-8") == "<static/>"


# --- semantic snapshot writer ---------------------------------------------------


def test_semantic_snapshot_writer_raises_when_driver_cannot(tmp_path):
    with pytest.raises(AdapterArtifactError) as e:
        make(Bare(), tmp_path).capture_artifact("semantic_snapshot", "snap")
    assert "does not support semantic snapshot" in str(e.value)


def test_semantic_snapshot_writer_raises_on_bad_snapshot(tmp_path):
    def boom(**kwargs):
        raise RuntimeError("snapshot broke")

    page = StaticPage()
    page.snapshot_result = boom

    with pytest.raises(AdapterArtifactError) as e:
        make(page, tmp_path).capture_artifact("semantic_snapshot", "snap")
    assert "snapshot failed" in str(e.value)


def test_semantic_snapshot_action_driver_unsupported():
    res = PhonePlaywrightSession(Bare()).execute_action("semantic_snapshot")

    assert res.success is False
    assert "does not support semantic snapshot" in res.message


def test_semantic_snapshot_action_failure_message(tmp_path):
    def boom(**kwargs):
        raise RuntimeError("viewport exploded")

    page = StaticPage()
    page.snapshot_result = boom

    res = PhonePlaywrightSession(page).execute_action(
        "semantic_snapshot", include_screenshot=True
    )

    assert res.success is False
    assert "viewport exploded" in res.message


def test_semantic_snapshot_flags_reach_driver():
    """Flags must reach a raw driver; BaseFakePhonePage.snapshot() swallows
    kwargs, so this pins a driver whose snapshot is the session's target."""

    recorded = {}

    class RecordingSnapshotDriver:
        platform = "android"

        def snapshot(self, include_screenshot=False, use_vision_fallback=False):
            recorded["include_screenshot"] = include_screenshot
            recorded["use_vision_fallback"] = use_vision_fallback
            return FakePhoneSnapshot()

    res = PhonePlaywrightSession(RecordingSnapshotDriver()).execute_action(
        "semantic_snapshot", include_screenshot=True, use_vision_fallback=True
    )

    assert res.success is True
    assert recorded == {"include_screenshot": True, "use_vision_fallback": True}


# --- stop / factory / platform detection edges -----------------------------------


def test_stop_without_start_is_noop():
    page = StaticPage()

    PhonePlaywrightSession(page).stop()

    assert page.calls == []


def test_stop_calls_disconnect_when_no_close():
    class DisconnectOnly:
        platform = "android"

        def __init__(self):
            self.disconnected = 0

        def disconnect(self):
            self.disconnected += 1

    driver = DisconnectOnly()
    session = PhonePlaywrightSession(driver)
    session.start()
    session.stop()
    session.stop()  # second stop is a no-op (_started already False)

    assert driver.disconnected == 1


def test_stop_calls_quit_when_no_close_or_disconnect():
    class QuitOnly:
        platform = "android"

        def __init__(self):
            self.QUIT = 0

        def quit(self):
            self.QUIT += 1

    driver = QuitOnly()
    session = PhonePlaywrightSession(driver)
    session.start()
    session.stop()

    assert driver.QUIT == 1


def test_platform_from_capabilities_platform_name():
    class CapsOnly:
        capabilities = {"platformName": " iOS "}

    assert PhonePlaywrightSession(CapsOnly()).info.platform == "ios"


def test_platform_defaults_android():
    assert PhonePlaywrightSession(Bare()).info.platform == "android"


def test_platform_requires_nonblank_string():
    class BlankPlatform:
        platform = "   "

    assert PhonePlaywrightSession(BlankPlatform()).info.platform == "android"


# --- parameter validation and lookup edges ---------------------------------------


def test_by_validation_errors():
    session = PhonePlaywrightSession(StaticPage())

    res = session.execute_action("tap", selector="x", by=123)
    assert res.success is False
    assert "by must be a string" in res.message

    res2 = session.execute_action("tap", selector="x", by="css")
    assert res2.success is False
    assert "unsupported by: css" in res2.message
    assert "resource-id" in res2.message  # supported list presented


def test_number_parameter_rejects_bool_and_negative():
    session = PhonePlaywrightSession(StaticPage())

    res = session.execute_action("tap", x=True, y=1)
    assert res.success is False
    assert "x must be a number" in res.message

    res2 = session.execute_action("tap", x=-1, y=1)
    assert res2.success is False
    assert "x must be >= 0" in res2.message


def test_tap_no_coordinate_support():
    res = PhonePlaywrightSession(Bare()).execute_action("tap", x=1, y=2)

    assert res.success is False
    assert "does not support coordinate taps" in res.message


def test_tap_uses_tap_method_when_no_click():
    recorded = []

    class TapOnlyPage:
        platform = "android"

        def tap(self, x, y):
            recorded.append((x, y))

    res = PhonePlaywrightSession(TapOnlyPage()).execute_action("tap", x=3, y=4)

    assert res.success is True
    assert recorded == [(3.0, 4.0)]


def test_swipe_requires_swipe_capable_driver():
    session = PhonePlaywrightSession(Bare())

    res_dir = session.execute_action("swipe", direction="up")
    assert res_dir.success is False
    assert "does not support swipe" in res_dir.message

    res_coord = session.execute_action(
        "swipe", start_x=0, start_y=0, end_x=1, end_y=1
    )
    assert res_coord.success is False
    assert "does not support swipe" in res_coord.message


def test_swipe_coordinate_parameter_validation():
    session = PhonePlaywrightSession(StaticPage())

    res_missing = session.execute_action("swipe", start_x=0, start_y=0)
    assert res_missing.success is False
    assert "end_x" in res_missing.message and "direction" in res_missing.message

    res_bad = session.execute_action(
        "swipe", start_x="bad", start_y=0, end_x=1, end_y=1
    )
    assert res_bad.success is False
    assert "start_x must be a number" in res_bad.message

    res_dur = session.execute_action(
        "swipe", start_x=0, start_y=0, end_x=1, end_y=1, duration=-2
    )
    assert res_dur.success is False
    assert "duration must be >= 0" in res_dur.message


def test_launch_and_terminate_without_driver_support():
    session = PhonePlaywrightSession(Bare())

    res_launch = session.execute_action("launch_app", app_id="x")
    assert res_launch.success is False
    assert "does not support app launch" in res_launch.message

    res_term = session.execute_action("terminate_app", app_id="x")
    assert res_term.success is False
    assert "does not support app termination" in res_term.message


def test_launch_app_fallback_methods():
    class LaunchPage(BaseFakePhonePage):
        def launch_app(self, package):
            self.calls.append(("launch_app", package))

    class ActivatePage(BaseFakePhonePage):
        def activate_app(self, package):
            self.calls.append(("activate_app", package))

    class TerminatePage(BaseFakePhonePage):
        def terminate_app(self, package):
            self.calls.append(("terminate_app", package))

    res1 = PhonePlaywrightSession(LaunchPage()).execute_action("launch_app", app_id="a")
    res2 = PhonePlaywrightSession(ActivatePage()).execute_action(
        "launch_app", app_id="b"
    )
    res3 = PhonePlaywrightSession(TerminatePage()).execute_action(
        "terminate_app", app_id="c"
    )

    assert res1.success and res2.success and res3.success


def test_scroll_into_view_locator_without_support():
    class BareLocator:
        text_value = None  # no scroll_into_view

    page = StaticPage()
    page.locators["text=静止"] = BareLocator()

    res = PhonePlaywrightSession(page).execute_action(
        "scroll_into_view", selector="静止"
    )

    assert res.success is False
    assert "does not support scroll_into_view" in res.message


def test_scroll_into_view_visibility_probe_error_is_swallowed():
    """scroll_ok but a raising is_visible() must not fail the action."""

    class ScrollThenExplode(FakePhoneLocator):
        def is_visible(self):
            raise RuntimeError("visibility check broken")

    page = StaticPage()
    page.locators["text=可见"] = ScrollThenExplode("text=可见")

    res = PhonePlaywrightSession(page).execute_action(
        "scroll_into_view", selector="可见"
    )

    assert res.success is True


def test_scroll_invalid_direction():
    res = PhonePlaywrightSession(StaticPage()).execute_action(
        "scroll_into_view", selector="x", direction="sideways"
    )

    assert res.success is False
    assert "invalid scroll direction" in res.message


def test_wait_for_element_timeout_must_be_number():
    session = PhonePlaywrightSession(StaticPage())

    res = session.execute_action("wait_for_element", selector="x", timeout="soon")
    assert res.success is False
    assert "timeout must be a number" in res.message

    res2 = session.execute_action("wait_for_element", selector="x", interval=-1)
    assert res2.success is False
    assert "interval must be >= 0" in res2.message


def test_wait_for_element_locator_wait_for_raises_maps_to_timeout():
    class ExplodingWait(FakePhoneLocator):
        def wait_for(self, state="visible", timeout_s=5.0):
            raise RuntimeError("wait blew up")

    page = StaticPage()
    page.locators["text=炸"] = ExplodingWait("text=炸")

    res = PhonePlaywrightSession(page).execute_action(
        "wait_for_element", selector="炸", timeout=0.2
    )

    assert res.success is False
    assert "timed out waiting for element" in res.message


def test_wait_for_element_blank_selector_times_out():
    """A blank selector resolves to an error result inside the retry loop;
    the ActionResult satisfies the not-None predicate and is surfaced."""

    res = PhonePlaywrightSession(StaticPage()).execute_action(
        "wait_for_element", selector="   ", timeout=0.1
    )

    assert res.success is False
    assert "non-empty string" in res.message


def test_wait_for_element_surfaces_resolution_error():
    res = PhonePlaywrightSession(StaticPage()).execute_action(
        "wait_for_element", selector="x", by="css", timeout=0.1
    )

    # The unsupported-by error object returned from lookup() satisfies the
    # not-None predicate and is returned as the action result.
    assert res.success is False
    assert res.message.startswith("unsupported by")


def test_wait_for_element_lookup_raises_folds_into_timeout():
    """retry_lookup=True re-raises into retry_until, whose default policy
    retries all Exceptions — a persistently dead driver therefore surfaces
    as a timeout, not a crash (documents the masking contract)."""

    class ExplodingLocator:
        platform = "android"

        def locator(self, s):
            raise RuntimeError("driver dead")

    session = PhonePlaywrightSession(ExplodingLocator())

    res = session.execute_action(
        "wait_for_element", selector="x", timeout=0.1, interval=0.03
    )

    assert res.success is False
    assert "timed out waiting for element" in res.message


def test_find_element_via_callable_driver():
    class CallableDriver:
        platform = "android"

        def __call__(self, selector):
            return FakePhoneLocator(selector)

    el = PhonePlaywrightSession(CallableDriver()).find_element("text", "通过调用")

    assert el.identifier == "text=通过调用"


def test_unsupported_driver_shape_reports_lookup_gap():
    res = PhonePlaywrightSession(Bare()).execute_action("tap", selector="x")

    assert res.success is False
    assert "does not support element lookup" in res.message


def test_resolve_element_locator_raises_non_retry_path():
    class ExplodingLocator:
        platform = "android"

        def locator(self, s):
            raise RuntimeError("driver dead")

    res = PhonePlaywrightSession(ExplodingLocator()).execute_action(
        "tap", selector="x"
    )

    assert res.success is False
    assert "element lookup failed" in res.message


def test_missing_selector_reports_lookup_failure():
    """locator() raising KeyError surfaces as a failed lookup (the retry
    loop's raise path); the wording carries the original locator error."""

    page = StaticPage(missing=("text=无",))
    session = PhonePlaywrightSession(page)

    res_tap = session.execute_action("tap", selector="无")
    assert res_tap.success is False
    assert "element lookup failed" in res_tap.message
    assert "locator not found" in res_tap.message

    res_type = session.execute_action("type_text", selector="无", text="x")
    assert res_type.success is False

    res_bounds = session.execute_action("element_bounds", selector="无")
    assert res_bounds.success is False


def test_element_bounds_unavailable_when_locator_has_none():
    page = StaticPage()
    page.locators["text=无界"] = FakePhoneLocator("text=无界", bounds=None)

    res = PhonePlaywrightSession(page).execute_action(
        "element_bounds", selector="无界"
    )

    assert res.success is False
    assert "element bounds unavailable" in res.message


def test_artifact_record_not_lifecycle_gated(tmp_path):
    """capture_artifact works before start(); documents current behavior —
    recording is session-scope, not lifecycle-gated."""

    page = StaticPage()
    page.screenshot_result = b"raw"
    session = PhonePlaywrightSession(
        page, identifier="pre-start", artifact_root=tmp_path / "art"
    )

    artifact = session.capture_artifact("screenshot", "shot")

    assert "pre-start" in str(artifact.path)


def test_raw_action_passthrough_with_kwargs():
    class ExtraActionPage(BaseFakePhonePage):
        def set_immo(self, value=None):
            self.calls.append(("set_immo", value))
            return {"done": True}

    res = PhonePlaywrightSession(ExtraActionPage()).execute_action(
        "set_immo", value=7
    )

    assert res.success is True
    assert res.message == "set_immo"
    assert res.data == {"done": True}


def test_raw_action_raises():
    class ExplodingActionPage(BaseFakePhonePage):
        def explode(self):
            raise RuntimeError("boom")

    res = PhonePlaywrightSession(ExplodingActionPage()).execute_action("explode")

    assert res.success is False
    assert "explode failed: boom" in res.message
