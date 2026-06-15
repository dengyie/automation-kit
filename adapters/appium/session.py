from pathlib import Path
from typing import Any, Callable, Optional

from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo


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
        elif artifact_type == "page_source":
            page_source = getattr(self.driver, "page_source", None)
            if isinstance(page_source, str):
                record.path.parent.mkdir(parents=True, exist_ok=True)
                record.path.write_text(page_source, encoding="utf-8")
        return ArtifactHandle(artifact_type=artifact_type, path=record.path)


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
        return AppiumSession(
            driver=self.driver_factory(),
            identifier=self.identifier,
            artifact_root=self.artifact_root,
        )
