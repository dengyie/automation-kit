import base64
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from adapters.errors import AdapterArtifactError, AdapterStartupError
from adapters.phone_playwright.element import PhonePlaywrightElement
from automation_core.artifacts import ArtifactStore
from automation_core.drivers import (
    ActionResult,
    ArtifactHandle,
    DriverSession,
    ElementHandle,
    ElementLookupSession,
    SessionInfo,
)
from automation_core.retries import RetryPolicy, retry_until

DriverFactory = Callable[[], Any]

SUPPORTED_BY: Dict[str, str] = {
    "text": "text=",
    "id": "resource-id=",
    "resource-id": "resource-id=",
    "role": "role=",
    "compact": "@",
    "ref": "@",
    "raw": "",
    "xpath": "xpath=",
}


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


def _driver_platform(driver: Any) -> str:
    platform = getattr(driver, "platform", None)
    if isinstance(platform, str) and platform.strip():
        return platform.strip().lower()
    capabilities = getattr(driver, "capabilities", None)
    if isinstance(capabilities, dict):
        p_name = capabilities.get("platformName")
        if isinstance(p_name, str) and p_name.strip():
            return p_name.strip().lower()
    return "android"


def _number_parameter(value: Any, name: str) -> Tuple[float, Optional[ActionResult]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0, ActionResult(False, f"{name} must be a number")
    if value < 0:
        return 0.0, ActionResult(False, f"{name} must be >= 0")
    return float(value), None


class PhonePlaywrightSession:
    """DriverSession and ElementLookupSession for phone-playwright drivers."""

    SUPPORTED_ARTIFACT_TYPES = frozenset(
        {"screenshot", "page_source", "ui_tree", "semantic_snapshot"}
    )

    def __init__(
        self,
        driver: Any,
        identifier: str = "phone_playwright-session",
        artifact_root: Optional[Path] = None,
    ) -> None:
        self.driver = driver
        self.info = SessionInfo(
            driver_name="phone_playwright",
            platform=_driver_platform(driver),
            identifier=identifier,
        )
        self.artifact_store = ArtifactStore(artifact_root or Path("artifacts"))
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        for close_name in ("close", "disconnect", "quit"):
            close_method = getattr(self.driver, close_name, None)
            if callable(close_method):
                close_method()
                break
        self._started = False

    def find_element(self, by: Optional[str], selector: str) -> ElementHandle:
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
        if action_name == "scroll_into_view":
            return self._scroll_into_view(**kwargs)
        if action_name == "element_bounds":
            return self._element_bounds(**kwargs)
        if action_name == "wait_for_element":
            return self._wait_for_element(**kwargs)
        if action_name == "semantic_snapshot":
            return self._semantic_snapshot(**kwargs)
        if action_name == "press_back":
            fn = getattr(self.driver, "press_back", None)
            if not callable(fn):
                return ActionResult(False, "driver does not support press_back")
            return self._run_action("press_back", fn)
        if action_name == "press_home":
            fn = getattr(self.driver, "press_home", None)
            if not callable(fn):
                return ActionResult(False, "driver does not support press_home")
            return self._run_action("press_home", fn)

        action = getattr(self.driver, action_name, None)
        if not callable(action):
            return ActionResult(
                success=False,
                message=f"unsupported phone_playwright action: {action_name}",
            )
        return self._run_action(action_name, lambda: action(**kwargs))

    def _launch_app(self, **kwargs: Any) -> ActionResult:
        app_id = kwargs.get("app_id")
        if app_id is None:
            return ActionResult(False, "missing required parameter: app_id")
        app_start = (
            getattr(self.driver, "app_start", None)
            or getattr(self.driver, "launch_app", None)
            or getattr(self.driver, "activate_app", None)
        )
        if not callable(app_start):
            return ActionResult(False, "driver does not support app launch")
        return self._run_action("launch_app", lambda: app_start(app_id))

    def _terminate_app(self, **kwargs: Any) -> ActionResult:
        app_id = kwargs.get("app_id")
        if app_id is None:
            return ActionResult(False, "missing required parameter: app_id")
        app_stop = (
            getattr(self.driver, "app_stop", None)
            or getattr(self.driver, "terminate_app", None)
        )
        if not callable(app_stop):
            return ActionResult(False, "driver does not support app termination")
        return self._run_action("terminate_app", lambda: app_stop(app_id))

    def _tap(self, action_name: str = "tap", **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is not None:
            element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
            if error is not None:
                return error
            if element is None:
                return ActionResult(False, f"element not found: {selector}")
            return self._run_action(action_name, element.click)

        x = kwargs.get("x")
        y = kwargs.get("y")
        if x is None or y is None:
            return ActionResult(False, "missing required parameter: selector or x/y")
        coordinates, error = self._coordinate_pair(x, y)
        if error is not None:
            return error
        if coordinates is None:
            return ActionResult(False, "invalid coordinates")
        device_click = getattr(self.driver, "click", None) or getattr(self.driver, "tap", None)
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
        if element is None:
            return ActionResult(False, f"element not found: {selector}")

        return self._run_action("type_text", lambda: element.input_text(text))

    def _swipe(self, **kwargs: Any) -> ActionResult:
        direction = kwargs.get("direction")
        if direction is not None:
            if direction not in ("up", "down", "left", "right"):
                return ActionResult(False, f"invalid swipe direction: {direction}")
            dist, err = _number_parameter(kwargs.get("distance_ratio", 0.5), "distance_ratio")
            if err is not None:
                return err
            swipe_fn = getattr(self.driver, "swipe", None)
            if not callable(swipe_fn):
                return ActionResult(False, "driver does not support swipe")
            return self._run_action("swipe", lambda: swipe_fn(direction=direction, distance_ratio=dist))

        missing = [
            name
            for name in ("start_x", "start_y", "end_x", "end_y")
            if kwargs.get(name) is None
        ]
        if missing:
            return ActionResult(
                False,
                f"missing required parameter(s): {', '.join(missing)} or direction",
            )
        coordinates = []
        for name in ("start_x", "start_y", "end_x", "end_y"):
            val, err = _number_parameter(kwargs.get(name), name)
            if err is not None:
                return err
            coordinates.append(val)
        duration, err = _number_parameter(kwargs.get("duration", 0.0), "duration")
        if err is not None:
            return err
        device_swipe = getattr(self.driver, "swipe", None)
        if not callable(device_swipe):
            return ActionResult(False, "driver does not support swipe")
        return self._run_action(
            "swipe",
            lambda: device_swipe(*coordinates, duration),
        )

    def _scroll_into_view(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
        if error is not None:
            return error
        if element is None:
            return ActionResult(False, f"element not found: {selector}")

        max_swipes_val, err = _number_parameter(kwargs.get("max_swipes", 5), "max_swipes")
        if err is not None:
            return err
        max_swipes = int(max_swipes_val)

        direction = kwargs.get("direction", "up")
        if direction not in ("up", "down", "left", "right"):
            return ActionResult(False, f"invalid scroll direction: {direction}")

        dist_val, err = _number_parameter(kwargs.get("distance_ratio", 0.5), "distance_ratio")
        if err is not None:
            return err
        distance_ratio = float(dist_val)

        locator = element._locator
        scroll_fn = getattr(locator, "scroll_into_view", None)
        if callable(scroll_fn):
            def do_scroll() -> ActionResult:
                scroll_fn(max_swipes=max_swipes, direction=direction, distance_ratio=distance_ratio)
                if callable(getattr(locator, "is_visible", None)):
                    try:
                        if not locator.is_visible():
                            return ActionResult(
                                False,
                                f"timed out scrolling element into view: {selector}",
                            )
                    except Exception:
                        pass
                return ActionResult(True, "scroll_into_view")

            return self._run_action("scroll_into_view", do_scroll)
        return ActionResult(False, "locator does not support scroll_into_view")

    def _coordinate_pair(
        self,
        x: Any,
        y: Any,
    ) -> Tuple[Optional[Tuple[float, float]], Optional[ActionResult]]:
        x_val, err_x = _number_parameter(x, "x")
        if err_x is not None:
            return None, err_x
        y_val, err_y = _number_parameter(y, "y")
        if err_y is not None:
            return None, err_y
        return (x_val, y_val), None

    def _element_bounds(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
        if error is not None:
            return error
        if element is None:
            return ActionResult(False, f"element not found: {selector}")
        bounds = element.bounds
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
        timeout, error = _number_parameter(kwargs.get("timeout", 5.0), "timeout")
        if error is not None:
            return error
        interval, error = _number_parameter(kwargs.get("interval", 0.25), "interval")
        if error is not None:
            return error
        by = kwargs.get("by")

        # 原生 Playwright wait_for 优先通道
        element, err = self._resolve_element(selector=selector, by=by)
        if err is None and element is not None:
            loc = element._locator
            wait_for_fn = getattr(loc, "wait_for", None)
            if callable(wait_for_fn):
                try:
                    res = wait_for_fn(state="visible", timeout_s=timeout)
                    if hasattr(res, "success"):
                        if res.success:
                            return ActionResult(
                                success=True,
                                message="wait_for_element",
                                data=element.identifier,
                            )
                        return ActionResult(
                            success=False,
                            message=f"timed out waiting for element: {selector}",
                        )
                    return ActionResult(
                        success=True,
                        message="wait_for_element",
                        data=element.identifier,
                    )
                except Exception:
                    return ActionResult(
                        success=False,
                        message=f"timed out waiting for element: {selector}",
                    )

        def lookup() -> Any:
            element, err = self._resolve_element(
                selector=selector,
                by=by,
                retry_lookup=True,
            )
            if err is not None:
                return err
            if element is None:
                return None

            # Verify visibility on lazy locators
            loc = element._locator
            if callable(getattr(loc, "is_visible", None)):
                try:
                    if not loc.is_visible():
                        return None
                except Exception:
                    return None
            return element

        result = retry_until(
            lookup,
            predicate=lambda val: val is not None,
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
                data=getattr(result.value, "identifier", selector),
            )
        return ActionResult(
            success=False,
            message=f"timed out waiting for element: {selector}",
        )

    def _semantic_snapshot(self, **kwargs: Any) -> ActionResult:
        snap_fn = getattr(self.driver, "snapshot", None)
        if not callable(snap_fn):
            return ActionResult(False, "driver does not support semantic snapshot")
        try:
            include_screenshot = bool(kwargs.get("include_screenshot", False))
            use_vision_fallback = bool(kwargs.get("use_vision_fallback", False))
            snap = snap_fn(
                include_screenshot=include_screenshot,
                use_vision_fallback=use_vision_fallback,
            )
            data_md = getattr(snap, "summary_markdown", None) or (
                snap.to_markdown() if callable(getattr(snap, "to_markdown", None)) else str(snap)
            )
            return ActionResult(success=True, message="semantic_snapshot", data=data_md)
        except Exception as exc:
            return ActionResult(False, f"semantic_snapshot failed: {exc}")

    def _resolve_element(
        self,
        selector: str,
        by: Optional[str],
        retry_lookup: bool = False,
    ) -> Tuple[Optional[PhonePlaywrightElement], Optional[ActionResult]]:
        if not isinstance(selector, str) or not selector.strip():
            return None, ActionResult(False, "selector must be a non-empty string")
        resolved_by, error = _normalize_by(by)
        if error is not None:
            return None, error

        # Map to phone-playwright selector syntax
        target_selector = selector
        prefix = SUPPORTED_BY[resolved_by]
        if resolved_by == "text":
            if not any(selector.startswith(p) for p in ("text=", "resource-id=", "id=", "role=", "@", "xpath=")):
                target_selector = f"text={selector}"
        elif resolved_by in ("compact", "ref"):
            target_selector = f"@{selector.lstrip('@')}"
        elif prefix and not selector.startswith(prefix):
            target_selector = f"{prefix}{selector}"

        try:
            if callable(getattr(self.driver, "locator", None)):
                lookup = self.driver.locator(target_selector)
            elif callable(self.driver):
                lookup = self.driver(target_selector)
            else:
                return None, ActionResult(False, "driver does not support element lookup")
        except Exception as exc:
            if retry_lookup:
                raise
            return None, ActionResult(
                False,
                f"element lookup failed: {selector} ({exc})",
            )

        return PhonePlaywrightElement(f"{resolved_by}={selector}", lookup), None

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
                f"unsupported phone_playwright artifact type: {artifact_type}"
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
            raise AdapterArtifactError(f"artifact was not written: {record.path}")
        return ArtifactHandle(
            artifact_type=artifact_type,
            path=record.path,
            metadata=record.metadata,
        )

    def _write_screenshot(self, path: Path) -> None:
        screenshot_fn = (
            getattr(self.driver, "take_screenshot", None)
            or getattr(self.driver, "screenshot", None)
            or getattr(self.driver, "save_screenshot", None)
        )
        if not callable(screenshot_fn):
            raise AdapterArtifactError("driver does not support screenshot capture")
        try:
            image = screenshot_fn()
        except Exception as exc:
            raise AdapterArtifactError("driver reported screenshot capture failed") from exc

        if isinstance(image, (bytes, bytearray)):
            path.write_bytes(image)
            return

        if isinstance(image, str):
            p = Path(image)
            if p.is_file():
                path.write_bytes(p.read_bytes())
                return
            try:
                raw_bytes = base64.b64decode(image)
                path.write_bytes(raw_bytes)
                return
            except Exception:
                pass

        save = getattr(image, "save", None)
        if callable(save):
            save(str(path))
            return

        raise AdapterArtifactError(
            "driver screenshot is not saveable (expected bytes, base64 or PIL image)"
        )

    def _write_hierarchy(self, path: Path) -> None:
        dump_fn = (
            getattr(self.driver, "dump_raw_tree", None)
            or getattr(self.driver, "dump_hierarchy", None)
            or getattr(self.driver, "page_source", None)
        )
        if dump_fn is None:
            snap_fn = getattr(self.driver, "snapshot", None)
            if callable(snap_fn):
                try:
                    snap = snap_fn()
                    content = (
                        snap.model_dump_json(indent=2)
                        if hasattr(snap, "model_dump_json")
                        else str(snap)
                    )
                    path.write_text(content, encoding="utf-8")
                    return
                except Exception as exc:
                    raise AdapterArtifactError("driver reported hierarchy dump failed") from exc
            raise AdapterArtifactError("driver does not provide UI hierarchy")
        try:
            hierarchy = dump_fn() if callable(dump_fn) else dump_fn
        except Exception as exc:
            raise AdapterArtifactError("driver reported hierarchy dump failed") from exc

        if not isinstance(hierarchy, str):
            if hasattr(hierarchy, "model_dump_json"):
                hierarchy = hierarchy.model_dump_json(indent=2)
            else:
                hierarchy = str(hierarchy)
        path.write_text(hierarchy, encoding="utf-8")

    def _write_semantic_snapshot(self, path: Path) -> None:
        snap_fn = getattr(self.driver, "snapshot", None)
        if not callable(snap_fn):
            raise AdapterArtifactError("driver does not support semantic snapshot")
        try:
            snap = snap_fn()
        except Exception as exc:
            raise AdapterArtifactError("driver reported snapshot failed") from exc
        content = (
            getattr(snap, "summary_markdown", None)
            or (snap.to_markdown() if callable(getattr(snap, "to_markdown", None)) else str(snap))
        )
        path.write_text(str(content), encoding="utf-8")


class PhonePlaywrightSessionFactory:
    """Factory that delays concrete phone-playwright device/page construction."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        identifier: str = "phone_playwright-session",
        artifact_root: Optional[Path] = None,
    ) -> None:
        self.driver_factory = driver_factory
        self.identifier = identifier
        self.artifact_root = artifact_root

    def create(self) -> PhonePlaywrightSession:
        try:
            driver = self.driver_factory()
        except Exception as exc:
            raise AdapterStartupError("failed to create phone_playwright driver") from exc
        return PhonePlaywrightSession(
            driver=driver,
            identifier=self.identifier,
            artifact_root=self.artifact_root,
        )
