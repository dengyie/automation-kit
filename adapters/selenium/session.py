from pathlib import Path
from typing import Any, Callable, Optional

from automation_core.artifacts import ArtifactStore
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo


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
        quit_method = getattr(self.driver, "quit", None)
        if callable(quit_method):
            quit_method()
        self._started = False

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        action = getattr(self.driver, action_name, None)
        if not callable(action):
            return ActionResult(
                success=False,
                message=f"unsupported selenium action: {action_name}",
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
        return ArtifactHandle(artifact_type=artifact_type, path=record.path)


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
        return SeleniumSession(
            driver=self.driver_factory(),
            identifier=self.identifier,
            artifact_root=self.artifact_root,
        )
