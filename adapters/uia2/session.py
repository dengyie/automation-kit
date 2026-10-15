import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from adapters.errors import AdapterArtifactError, AdapterStartupError
from adapters.uia2.distill import HierarchyDistillError, distill_snapshot
from adapters.uia2.element import RefElement, Uia2Element
from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.observations import ScreenElement, ScreenSnapshot
from automation_core.retries import RetryPolicy, retry_until


DriverFactory = Callable[[], Any]

# Locator vocabulary mapped onto uiautomator2 selector kwargs. ``by=None``
# defaults to ``text`` (the most common uiautomator2 shorthand); ``xpath``
# is dispatched through ``Device.xpath``. Contains variants mirror the
# native ``textContains``/``descriptionContains`` uiautomator2 kwargs.
# ``ref``/``compact`` resolve against the latest distilled semantic
# snapshot (``@N`` element indices) instead of a live UiObject lookup.
SUPPORTED_BY: Dict[str, str] = {
    "id": "resourceId",
    "text": "text",
    "description": "description",
    "class": "className",
    "xpath": "xpath",
    "text-contains": "textContains",
    "description-contains": "descriptionContains",
    "ref": "",
    "compact": "",
}

_REF_ALIASES = ("ref", "compact")

# Snapshot selectors distillation can match on its own; xpath/class need a
# live UiObject and are rejected for snapshot-scoped operations.
_SNAPSHOT_MATCH_ALIASES = ("text", "description", "text-contains", "description-contains", "id", "resource-id")

DEFAULT_SNAPSHOT_TTL = 1.0


def _normalize_by(by: Optional[str]) -> Tuple[str, Optional[ActionResult]]:
    if by is None:
        return "text", None
    if not isinstance(by, str):
        return "", ActionResult(False, "by must be a string when provided")
    normalized = by.strip().lower()
    if normalized not in SUPPORTED_BY:
        supported = ", ".join(sorted(SUPPORTED_BY))
        return "", ActionResult(
            False,
            f"unsupported by: {by} (supported: {supported})",
        )
    return normalized, None


class Uia2Session:
    """DriverSession implementation for uiautomator2 device drivers."""

    SUPPORTED_ARTIFACT_TYPES = frozenset(
        {"screenshot", "page_source", "ui_tree", "semantic_snapshot"}
    )

    def __init__(
        self,
        driver: Any,
        identifier: str = "uia2-session",
        artifact_root: Optional[Path] = None,
        snapshot_ttl: float = DEFAULT_SNAPSHOT_TTL,
    ):
        self.driver = driver
        self.info = SessionInfo(
            driver_name="uia2",
            platform="android",
            identifier=identifier,
        )
        self.artifact_store = ArtifactStore(artifact_root or Path("artifacts"))
        # Warm-cache window for ref-based dispatch: a ``tap`` right after a
        # ``semantic_snapshot`` reuses the distilled snapshot instead of
        # paying a second hierarchy dump.
        self.snapshot_ttl = snapshot_ttl
        self._snapshot: Optional[ScreenSnapshot] = None
        self._snapshot_at: float = -1.0
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        # A uiautomator2 device needs no teardown, but an injected wrapper may
        # own the adb/uiautomator connection; honor exactly one close hook.
        for close_name in ("disconnect", "quit"):
            close_method = getattr(self.driver, close_name, None)
            if callable(close_method):
                close_method()
                break
        self._started = False

    def find_element(self, by: Optional[str], selector: str) -> Any:
        """Resolve a selector or snapshot ref to an ElementHandle.

        Implements the ``ElementLookupSession`` contract, mirroring the
        Selenium/Appium/phone_playwright sessions.
        """
        element, error = self._resolve_element(selector=selector, by=by)
        if error is not None:
            raise KeyError(error.message)
        if element is None:
            raise KeyError(f"element not found: {selector}")
        return element

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        if action_name == "launch_app":
            return self._launch_app(**kwargs)
        if action_name == "terminate_app":
            return self._terminate_app(**kwargs)
        if action_name == "tap":
            return self._tap(**kwargs)
        if action_name == "click":
            return self._tap(action_name="click", **kwargs)
        if action_name == "type_text":
            return self._type_text(**kwargs)
        if action_name == "swipe":
            return self._swipe(**kwargs)
        if action_name == "element_bounds":
            return self._element_bounds(**kwargs)
        if action_name == "wait_for_element":
            return self._wait_for_element(**kwargs)
        if action_name == "semantic_snapshot":
            return self._semantic_snapshot(**kwargs)
        if action_name == "scroll_into_view":
            return self._scroll_into_view(**kwargs)
        if action_name == "press_back":
            return self._press_key("back")
        if action_name == "press_home":
            return self._press_key("home")

        action = getattr(self.driver, action_name, None)
        if not callable(action):
            return ActionResult(
                success=False,
                message=f"unsupported uia2 action: {action_name}",
            )
        return self._run_action(action_name, lambda: action(**kwargs))

    def _launch_app(self, **kwargs: Any) -> ActionResult:
        app_id = kwargs.get("app_id")
        if app_id is None:
            return ActionResult(False, "missing required parameter: app_id")
        app_start = getattr(self.driver, "app_start", None)
        if not callable(app_start):
            return ActionResult(False, "driver does not support app launch")
        return self._run_action("launch_app", lambda: app_start(app_id))

    def _terminate_app(self, **kwargs: Any) -> ActionResult:
        app_id = kwargs.get("app_id")
        if app_id is None:
            return ActionResult(False, "missing required parameter: app_id")
        app_stop = getattr(self.driver, "app_stop", None)
        if not callable(app_stop):
            return ActionResult(False, "driver does not support app termination")
        return self._run_action("terminate_app", lambda: app_stop(app_id))

    def _tap(self, action_name: str = "tap", **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is not None:
            element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
            if error is not None:
                return error
            return self._run_action(action_name, element.click)

        x = kwargs.get("x")
        y = kwargs.get("y")
        if x is None or y is None:
            return ActionResult(
                False,
                "missing required parameter: selector or x/y",
            )
        coordinates, error = self._coordinate_pair(x, y)
        if error is not None:
            return error
        device_click = getattr(self.driver, "click", None)
        if not callable(device_click):
            return ActionResult(False, "driver does not support coordinate taps")
        return self._run_action(
            action_name,
            lambda: device_click(coordinates[0], coordinates[1]),
        )

    def _type_text(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        text = kwargs.get("text")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        if text is None:
            return ActionResult(False, "missing required parameter: text")
        element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
        if error is not None:
            return error
        clear = kwargs.get("clear", True)

        if isinstance(element, RefElement):
            return self._run_action(
                "type_text",
                lambda: element.input_text(text, clear=clear),
            )

        def type_into_element():
            return element.type_text(text, clear=clear)

        return self._run_action("type_text", type_into_element)

    def _swipe(self, **kwargs: Any) -> ActionResult:
        missing = [
            name
            for name in ("start_x", "start_y", "end_x", "end_y")
            if kwargs.get(name) is None
        ]
        if missing:
            return ActionResult(
                False,
                f"missing required parameter(s): {', '.join(missing)}",
            )
        coordinates = []
        for name in ("start_x", "start_y", "end_x", "end_y"):
            value, error = _number_parameter(kwargs.get(name), name)
            if error is not None:
                return error
            coordinates.append(value)
        duration, error = _number_parameter(kwargs.get("duration", 0.0), "duration")
        if error is not None:
            return error
        device_swipe = getattr(self.driver, "swipe", None)
        if not callable(device_swipe):
            return ActionResult(False, "driver does not support swipe")
        return self._run_action(
            "swipe",
            lambda: device_swipe(*coordinates, duration),
        )

    def _coordinate_pair(
        self,
        x: Any,
        y: Any,
    ) -> Tuple[Optional[Tuple[float, float]], Optional[ActionResult]]:
        x_value, error = _number_parameter(x, "x")
        if error is not None:
            return None, error
        y_value, error = _number_parameter(y, "y")
        if error is not None:
            return None, error
        return (x_value, y_value), None

    def _element_bounds(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
        if error is not None:
            return error
        bounds = getattr(element, "bounds", None)
        if not isinstance(bounds, dict):
            return ActionResult(False, "element bounds unavailable")
        try:
            x = int(bounds["x"])
            y = int(bounds["y"])
            width = int(bounds["width"])
            height = int(bounds["height"])
        except (KeyError, TypeError, ValueError):
            return ActionResult(False, "element bounds unavailable")
        return ActionResult(
            True,
            "element_bounds",
            data={"x": x, "y": y, "width": width, "height": height},
        )

    def _wait_for_element(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        by = kwargs.get("by")
        if isinstance(by, str) and by.strip().lower() in _REF_ALIASES:
            return ActionResult(
                False,
                "wait_for_element does not support ref selectors: refs are "
                "positional against a distilled snapshot, use text/id instead",
            )
        timeout, error = _number_parameter(kwargs.get("timeout", 5.0), "timeout")
        if error is not None:
            return error
        interval, error = _number_parameter(kwargs.get("interval", 0.25), "interval")
        if error is not None:
            return error
        by = kwargs.get("by")

        def lookup():
            element, error = self._resolve_element(
                selector=selector,
                by=by,
                retry_lookup=True,
            )
            if error is not None:
                return error
            return element

        result = retry_until(
            lookup,
            predicate=lambda value: value is not None,
            policy=RetryPolicy(
                max_duration=timeout,
                interval=interval,
            ),
        )
        if result.success:
            if isinstance(result.value, ActionResult):
                return result.value
            return ActionResult(
                success=True,
                message="wait_for_element",
                data=result.value.identifier,
            )
        return ActionResult(
            success=False,
            message=f"timed out waiting for element: {selector}",
        )

    def _resolve_element(
        self,
        selector: str,
        by: Optional[str],
        retry_lookup: bool = False,
    ) -> Tuple[Optional[Any], Optional[ActionResult]]:
        if not isinstance(selector, str) or not selector.strip():
            return None, ActionResult(False, "selector must be a non-empty string")
        resolved_by, error = _normalize_by(by)
        if error is not None:
            return None, error
        if resolved_by in _REF_ALIASES:
            return self._resolve_ref(selector)
        try:
            if resolved_by == "xpath":
                lookup = self.driver.xpath(selector)
            else:
                lookup = self.driver(**{SUPPORTED_BY[resolved_by]: selector})
        except Exception:
            if retry_lookup:
                raise
            return None, ActionResult(
                False,
                f"element lookup failed: {selector}",
            )
        return Uia2Element(f"{resolved_by}={selector}", lookup), None

    def _resolve_ref(
        self,
        selector: str,
    ) -> Tuple[Optional[RefElement], Optional[ActionResult]]:
        """Resolve an ``@N`` compact ref against the distilled snapshot.

        Falls back to a fresh hierarchy dump when the warm cache is expired
        (snapshot_ttl); interaction then dispatches at the cached bounds
        without touching the driver again.
        """
        ref_text = selector.strip()
        if ref_text.startswith("@"):
            ref_text = ref_text[1:]
        if not ref_text.isdigit():
            return None, ActionResult(
                False,
                f"invalid ref selector: {selector} (expected '@N' or N)",
            )
        snapshot, error = self._snapshot_for_refs()
        if error is not None:
            return None, error
        element = snapshot.element(int(ref_text))
        if element is None:
            count = len(snapshot.interactable())
            return None, ActionResult(
                False,
                f"ref @{ref_text} not in current snapshot "
                f"({count} interactable elements)",
            )
        dispatch_click = self._coordinate_dispatcher()
        if dispatch_click is None:
            return None, ActionResult(False, "driver does not support coordinate taps")
        return RefElement(
            snapshot_element=element,
            dispatch_click=dispatch_click,
            send_text=getattr(self.driver, "send_keys", None),
            clear_text=getattr(self.driver, "clear_text", None),
            viewport=(snapshot.viewport_width, snapshot.viewport_height),
        ), None

    def _coordinate_dispatcher(self) -> Optional[Callable[[int, int], Any]]:
        click = getattr(self.driver, "click", None) or getattr(self.driver, "tap", None)
        return click if callable(click) else None

    def _snapshot_for_refs(self) -> Tuple[Optional[ScreenSnapshot], Optional[ActionResult]]:
        now = time.monotonic()
        # Strict comparison: ttl=0 means "always refresh" even when the
        # monotonic clock granularity makes the delta read as exactly 0.
        if self._snapshot is not None and (now - self._snapshot_at) < self.snapshot_ttl:
            return self._snapshot, None
        return self._capture_snapshot()

    def _capture_snapshot(self) -> Tuple[Optional[ScreenSnapshot], Optional[ActionResult]]:
        dump = getattr(self.driver, "dump_hierarchy", None)
        if not callable(dump):
            return None, ActionResult(False, "driver does not provide a UI hierarchy")
        try:
            hierarchy = dump()
        except Exception as exc:
            return None, ActionResult(False, f"hierarchy dump failed: {exc}")
        if not isinstance(hierarchy, str):
            return None, ActionResult(False, "hierarchy dump is not a string")

        package_name, activity_name = self._foreground_app()
        try:
            snapshot = distill_snapshot(
                hierarchy,
                package_name=package_name,
                activity_name=activity_name,
                device_id=self.info.identifier,
                captured_at=time.time(),
            )
        except HierarchyDistillError as exc:
            return None, ActionResult(False, f"semantic snapshot failed: {exc}")
        self._snapshot = snapshot
        self._snapshot_at = time.monotonic()
        return snapshot, None

    def _foreground_app(self) -> Tuple[Optional[str], Optional[str]]:
        app_current = getattr(self.driver, "app_current", None)
        if not callable(app_current):
            return None, None
        try:
            current = app_current()
        except Exception:
            return None, None
        if not isinstance(current, dict):
            return None, None
        package = current.get("package")
        activity = current.get("activity")
        return (
            package if isinstance(package, str) and package else None,
            activity if isinstance(activity, str) and activity else None,
        )

    def _semantic_snapshot(self, **kwargs: Any) -> ActionResult:
        # ``refresh`` forces a new dump; the default honors the warm-cache
        # TTL so consecutive observation+action steps share one dump.
        if kwargs.get("refresh"):
            snapshot, error = self._capture_snapshot()
        else:
            snapshot, error = self._snapshot_for_refs()
        if error is not None:
            return error
        assert snapshot is not None
        data = snapshot.to_dict()
        data["markdown"] = snapshot.to_markdown()
        return ActionResult(success=True, message="semantic_snapshot", data=data)

    def _scroll_into_view(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        by = kwargs.get("by")
        resolved_by, error = _normalize_by(by)
        if error is not None:
            return error
        if (
            resolved_by not in _SNAPSHOT_MATCH_ALIASES
            and resolved_by not in _REF_ALIASES
        ):
            return ActionResult(
                False,
                "scroll_into_view matches snapshots with text/id/description "
                f"selectors only, got: {by}",
            )
        max_swipes, error = _number_parameter(kwargs.get("max_swipes", 5), "max_swipes")
        if error is not None:
            return error
        duration, error = _number_parameter(kwargs.get("duration", 0.3), "duration")
        if error is not None:
            return error
        distance_ratio, error = _number_parameter(
            kwargs.get("distance_ratio", 0.5), "distance_ratio"
        )
        if error is not None:
            return error
        settle, error = _number_parameter(kwargs.get("settle", 0.3), "settle")
        if error is not None:
            return error
        direction = kwargs.get("direction", "up")
        if direction not in ("up", "down", "left", "right"):
            return ActionResult(False, f"invalid scroll direction: {direction}")

        attempts = 0
        while True:
            snapshot, error = self._capture_snapshot()
            if error is not None:
                return error
            assert snapshot is not None
            match = self._match_in_snapshot(snapshot, selector, resolved_by)
            if match is not None:
                return ActionResult(
                    success=True,
                    message="scroll_into_view",
                    data={
                        "ref": match.ref,
                        "attempts": attempts,
                        "bounds": match.bounds.to_dict(),
                    },
                )
            if attempts >= int(max_swipes):
                return ActionResult(
                    False,
                    f"element not visible after {attempts} swipe(s): {selector}",
                )
            swipe_error = self._scroll_swipe(snapshot, direction, distance_ratio, duration)
            if swipe_error is not None:
                return swipe_error
            attempts += 1
            # Let the scroll animation settle before the next dump; dumping
            # mid-animation would miss the target and overshoot the list.
            if settle > 0:
                time.sleep(settle)

    def _match_in_snapshot(
        self,
        snapshot: ScreenSnapshot,
        selector: str,
        resolved_by: str,
    ) -> Optional[ScreenElement]:
        needle = selector.strip()
        if resolved_by in _REF_ALIASES:
            if needle.startswith("@"):
                needle = needle[1:]
            return snapshot.element(int(needle)) if needle.isdigit() else None

        def matches(element: ScreenElement) -> bool:
            if resolved_by in ("id", "resource-id"):
                if not element.resource_id:
                    return False
                return (
                    element.resource_id == needle
                    or element.resource_id.endswith("/" + needle)
                    or element.resource_id.endswith(":" + needle)
                )
            return needle in element.text

        first_info: Optional[ScreenElement] = None
        for element in snapshot.elements:
            if not matches(element):
                continue
            if element.ref is not None:
                return element
            if first_info is None:
                first_info = element
        return first_info

    def _scroll_swipe(
        self,
        snapshot: ScreenSnapshot,
        direction: str,
        distance_ratio: float,
        duration: float,
    ) -> Optional[ActionResult]:
        swipe = getattr(self.driver, "swipe", None)
        if not callable(swipe):
            return ActionResult(False, "driver does not support swipe")
        vertical_dx = 0
        vertical_dy = int(snapshot.viewport_height * distance_ratio)
        horizontal_dx = int(snapshot.viewport_width * distance_ratio)
        horizontal_dy = 0
        dx, dy = {
            "up": (vertical_dx, -vertical_dy),
            "down": (vertical_dx, vertical_dy),
            "left": (-horizontal_dx, horizontal_dy),
            "right": (horizontal_dx, horizontal_dy),
        }[direction]
        center_x = snapshot.viewport_width // 2
        center_y = snapshot.viewport_height // 2
        swipe(
            center_x - dx // 2,
            center_y - dy // 2,
            center_x + dx // 2,
            center_y + dy // 2,
            duration,
        )
        return None

    def _press_key(self, key: str) -> ActionResult:
        press = getattr(self.driver, "press", None)
        if callable(press):
            return self._run_action(f"press_{key}", lambda: press(key))
        dedicated = getattr(self.driver, f"press_{key}", None)
        if callable(dedicated):
            return self._run_action(f"press_{key}", dedicated)
        return ActionResult(False, "driver does not support key presses")

    def _run_action(self, action_name: str, action: Callable[[], Any]) -> ActionResult:
        try:
            result = action()
        except Exception as exc:
            return ActionResult(False, f"{action_name} failed: {exc}")
        if isinstance(result, ActionResult):
            return result
        return ActionResult(success=True, message=action_name, data=result)

    def capture_artifact(self, artifact_type: str, name: str) -> ArtifactHandle:
        if artifact_type not in self.SUPPORTED_ARTIFACT_TYPES:
            raise AdapterArtifactError(
                f"unsupported uia2 artifact type: {artifact_type}"
            )
        record = self.artifact_store.record(
            run_id=self.info.identifier,
            artifact_type=artifact_type,
            name=name,
        )
        record.path.parent.mkdir(parents=True, exist_ok=True)
        if artifact_type == "screenshot":
            self._write_screenshot(record.path)
        elif artifact_type == "semantic_snapshot":
            self._write_semantic_snapshot(record.path)
        else:
            self._write_hierarchy(record.path)
        if not record.path.is_file():
            raise AdapterArtifactError(
                f"artifact was not written: {record.path}"
            )
        return ArtifactHandle(
            artifact_type=artifact_type,
            path=record.path,
            metadata=record.metadata,
        )

    def _write_screenshot(self, path: Path) -> None:
        screenshot = getattr(self.driver, "screenshot", None)
        if not callable(screenshot):
            raise AdapterArtifactError("driver does not support screenshot capture")
        try:
            image = screenshot()
        except Exception as exc:
            raise AdapterArtifactError(
                "driver reported screenshot capture failed"
            ) from exc
        if isinstance(image, (bytes, bytearray)):
            path.write_bytes(image)
            return
        save = getattr(image, "save", None)
        if not callable(save):
            raise AdapterArtifactError(
                "driver screenshot is not saveable (expected PIL image or bytes)"
            )
        save(str(path))

    def _write_hierarchy(self, path: Path) -> None:
        dump = getattr(self.driver, "dump_hierarchy", None)
        if not callable(dump):
            raise AdapterArtifactError("driver does not provide a UI hierarchy")
        try:
            hierarchy = dump()
        except Exception as exc:
            raise AdapterArtifactError(
                "driver reported hierarchy dump failed"
            ) from exc
        if not isinstance(hierarchy, str):
            raise AdapterArtifactError("driver hierarchy dump is not a string")
        path.write_text(hierarchy, encoding="utf-8")

    def _write_semantic_snapshot(self, path: Path) -> None:
        snapshot, error = self._capture_snapshot()
        if error is not None or snapshot is None:
            raise AdapterArtifactError(
                error.message if error is not None else "semantic snapshot unavailable"
            )
        path.write_text(snapshot.to_markdown(), encoding="utf-8")


class Uia2SessionFactory:
    """Factory that delays concrete uiautomator2 device construction."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        identifier: str = "uia2-session",
        artifact_root: Optional[Path] = None,
        snapshot_ttl: float = DEFAULT_SNAPSHOT_TTL,
    ):
        self.driver_factory = driver_factory
        self.identifier = identifier
        self.artifact_root = artifact_root
        self.snapshot_ttl = snapshot_ttl

    def create(self) -> Uia2Session:
        try:
            driver = self.driver_factory()
        except Exception as exc:
            raise AdapterStartupError("failed to create uia2 device") from exc
        return Uia2Session(
            driver=driver,
            identifier=self.identifier,
            artifact_root=self.artifact_root,
            snapshot_ttl=self.snapshot_ttl,
        )


def _number_parameter(value: Any, name: str) -> Tuple[float, Optional[ActionResult]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0, ActionResult(False, f"{name} must be a number")
    if value < 0:
        return 0.0, ActionResult(False, f"{name} must be >= 0")
    return float(value), None
