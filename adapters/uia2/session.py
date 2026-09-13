from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from adapters.errors import AdapterArtifactError, AdapterStartupError
from adapters.uia2.element import Uia2Element
from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.retries import RetryPolicy, retry_until


DriverFactory = Callable[[], Any]

# Locator vocabulary mapped onto uiautomator2 selector kwargs. ``by=None``
# defaults to ``text`` (the most common uiautomator2 shorthand); ``xpath``
# is dispatched through ``Device.xpath``. Contains variants mirror the
# native ``textContains``/``descriptionContains`` uiautomator2 kwargs.
SUPPORTED_BY: Dict[str, str] = {
    "id": "resourceId",
    "text": "text",
    "description": "description",
    "class": "className",
    "xpath": "xpath",
    "text-contains": "textContains",
    "description-contains": "descriptionContains",
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


class Uia2Session:
    """DriverSession implementation for uiautomator2 device drivers."""

    SUPPORTED_ARTIFACT_TYPES = frozenset({"screenshot", "page_source", "ui_tree"})

    def __init__(
        self,
        driver: Any,
        identifier: str = "uia2-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver = driver
        self.info = SessionInfo(
            driver_name="uia2",
            platform="android",
            identifier=identifier,
        )
        self.artifact_store = ArtifactStore(artifact_root or Path("artifacts"))
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
        if action_name == "wait_for_element":
            return self._wait_for_element(**kwargs)

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
    ) -> Tuple[Optional[Uia2Element], Optional[ActionResult]]:
        if not isinstance(selector, str) or not selector.strip():
            return None, ActionResult(False, "selector must be a non-empty string")
        resolved_by, error = _normalize_by(by)
        if error is not None:
            return None, error
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

    def _run_action(self, action_name: str, action: Callable[[], Any]) -> ActionResult:
        try:
            result = action()
        except Exception as exc:
            return ActionResult(False, f"{action_name} failed: {exc}")
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


class Uia2SessionFactory:
    """Factory that delays concrete uiautomator2 device construction."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        identifier: str = "uia2-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver_factory = driver_factory
        self.identifier = identifier
        self.artifact_root = artifact_root

    def create(self) -> Uia2Session:
        try:
            driver = self.driver_factory()
        except Exception as exc:
            raise AdapterStartupError("failed to create uia2 device") from exc
        return Uia2Session(
            driver=driver,
            identifier=self.identifier,
            artifact_root=self.artifact_root,
        )


def _number_parameter(value: Any, name: str) -> Tuple[float, Optional[ActionResult]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0, ActionResult(False, f"{name} must be a number")
    if value < 0:
        return 0.0, ActionResult(False, f"{name} must be >= 0")
    return float(value), None
