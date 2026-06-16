from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from adapters.errors import AdapterStartupError
from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.retries import RetryPolicy, retry_until


DriverFactory = Callable[[], Any]


class AppiumSession:
    """DriverSession implementation for Appium-like mobile drivers."""

    def __init__(
        self,
        driver: Any,
        identifier: str = "appium-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver = driver
        self.info = SessionInfo(
            driver_name="appium",
            platform="android",
            identifier=identifier,
        )
        self.artifact_store = ArtifactStore(artifact_root or Path("artifacts"))
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        quit_method = getattr(self.driver, "quit", None)
        if callable(quit_method):
            quit_method()
        self._started = False

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        if action_name == "launch_app":
            return self._launch_app(**kwargs)
        if action_name == "tap":
            return self._tap(**kwargs)
        if action_name == "type_text":
            return self._type_text(**kwargs)
        if action_name == "wait_for_element":
            return self._wait_for_element(**kwargs)

        if action_name.startswith("mobile:"):
            execute_script = getattr(self.driver, "execute_script", None)
            if not callable(execute_script):
                return ActionResult(
                    success=False,
                    message="driver does not support mobile script execution",
                )
            result = execute_script(action_name, kwargs)
            return ActionResult(success=True, message=action_name, data=result)

        action = getattr(self.driver, action_name, None)
        if not callable(action):
            return ActionResult(
                success=False,
                message=f"unsupported appium action: {action_name}",
            )
        result = action(**kwargs)
        return ActionResult(success=True, message=action_name, data=result)

    def _launch_app(self, **kwargs: Any) -> ActionResult:
        app_id = kwargs.get("app_id")
        if app_id is None:
            return ActionResult(False, "missing required parameter: app_id")
        activate_app = getattr(self.driver, "activate_app", None)
        if not callable(activate_app):
            return ActionResult(False, "driver does not support app launch")
        result = activate_app(app_id)
        return ActionResult(success=True, message="launch_app", data=result)

    def _tap(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is not None:
            element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
            if error is not None:
                return error
            result = element.click()
            return ActionResult(success=True, message="tap", data=result)

        x = kwargs.get("x")
        y = kwargs.get("y")
        if x is None or y is None:
            return ActionResult(False, "missing required parameter: selector or x/y")
        execute_script = getattr(self.driver, "execute_script", None)
        if not callable(execute_script):
            return ActionResult(
                success=False,
                message="driver does not support mobile script execution",
            )
        result = execute_script("mobile: clickGesture", {"x": x, "y": y})
        return ActionResult(success=True, message="tap", data=result)

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
        clear_method = getattr(element, "clear", None)
        if clear and callable(clear_method):
            clear_method()
        result = element.send_keys(text)
        return ActionResult(success=True, message="type_text", data=result)

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
                data=result.value,
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
        find_element = getattr(self.driver, "find_element", None)
        if not callable(find_element):
            return None, ActionResult(False, "driver does not support element lookup")
        try:
            return find_element(by or "accessibility id", selector), None
        except Exception:
            if retry_lookup:
                raise
            return None, ActionResult(
                False,
                f"element lookup failed: {selector}",
            )

    def capture_artifact(self, artifact_type: str, name: str) -> ArtifactHandle:
        record = self.artifact_store.record(
            run_id=self.info.identifier,
            artifact_type=artifact_type,
            name=name,
        )
        if artifact_type == "screenshot":
            screenshot = getattr(self.driver, "save_screenshot", None)
            if callable(screenshot):
                record.path.parent.mkdir(parents=True, exist_ok=True)
                screenshot(str(record.path))
        elif artifact_type in {"page_source", "ui_tree"}:
            page_source = getattr(self.driver, "page_source", None)
            if isinstance(page_source, str):
                record.path.parent.mkdir(parents=True, exist_ok=True)
                record.path.write_text(page_source, encoding="utf-8")
        return ArtifactHandle(
            artifact_type=artifact_type,
            path=record.path,
            metadata=record.metadata,
        )


class AppiumSessionFactory:
    """Factory that delays concrete Appium driver construction."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        identifier: str = "appium-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver_factory = driver_factory
        self.identifier = identifier
        self.artifact_root = artifact_root

    def create(self) -> AppiumSession:
        try:
            driver = self.driver_factory()
        except Exception as exc:
            raise AdapterStartupError("failed to create appium driver") from exc
        return AppiumSession(
            driver=driver,
            identifier=self.identifier,
            artifact_root=self.artifact_root,
        )


def _number_parameter(value: Any, name: str) -> Tuple[float, Optional[ActionResult]]:
    if not isinstance(value, (int, float)):
        return 0.0, ActionResult(False, f"{name} must be a number")
    if value < 0:
        return 0.0, ActionResult(False, f"{name} must be >= 0")
    return float(value), None
