from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from adapters.errors import AdapterStartupError
from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.retries import RetryPolicy, retry_until


DriverFactory = Callable[[], Any]


class SeleniumSession:
    """DriverSession implementation for Selenium-like browser drivers."""

    def __init__(
        self,
        driver: Any,
        identifier: str = "selenium-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver = driver
        self.info = SessionInfo(
            driver_name="selenium",
            platform="web",
            identifier=identifier,
        )
        self.artifact_store = ArtifactStore(artifact_root or Path("artifacts"))
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        quit_method = getattr(self.driver, "quit", None)
        if callable(quit_method):
            quit_method()
        self._started = False

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        if action_name == "open":
            return self._open(**kwargs)
        if action_name == "click":
            return self._click(**kwargs)
        if action_name == "type_text":
            return self._type_text(**kwargs)
        if action_name == "wait_for_element":
            return self._wait_for_element(**kwargs)

        action = getattr(self.driver, action_name, None)
        if not callable(action):
            return ActionResult(
                success=False,
                message=f"unsupported selenium action: {action_name}",
            )
        return self._run_action(action_name, lambda: action(**kwargs))

    def _open(self, **kwargs: Any) -> ActionResult:
        url = kwargs.get("url")
        if url is None:
            return ActionResult(False, "missing required parameter: url")
        return self._run_action("open", lambda: self.driver.get(url))

    def _click(self, **kwargs: Any) -> ActionResult:
        selector = kwargs.get("selector")
        if selector is None:
            return ActionResult(False, "missing required parameter: selector")
        element, error = self._resolve_element(selector=selector, by=kwargs.get("by"))
        if error is not None:
            return error
        return self._run_action("click", element.click)

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

        def type_into_element():
            if clear and callable(clear_method):
                clear_method()
            return element.send_keys(text)

        return self._run_action("type_text", type_into_element)

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
            return find_element(by or "css selector", selector), None
        except Exception:
            if retry_lookup:
                raise
            return None, ActionResult(
                False,
                f"element lookup failed: {selector}",
            )

    def _run_action(self, action_name: str, action: Callable[[], Any]) -> ActionResult:
        try:
            result = action()
        except Exception as exc:
            return ActionResult(False, f"{action_name} failed: {exc}")
        return ActionResult(success=True, message=action_name, data=result)

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


class SeleniumSessionFactory:
    """Factory that delays concrete Selenium driver construction."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        identifier: str = "selenium-session",
        artifact_root: Optional[Path] = None,
    ):
        self.driver_factory = driver_factory
        self.identifier = identifier
        self.artifact_root = artifact_root

    def create(self) -> SeleniumSession:
        try:
            driver = self.driver_factory()
        except Exception as exc:
            raise AdapterStartupError("failed to create selenium driver") from exc
        return SeleniumSession(
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
