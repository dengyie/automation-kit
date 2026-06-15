from pathlib import Path
from typing import Any, List, Tuple

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo


class DryRunSession:
    def __init__(self, workflow_name: str):
        self.info = SessionInfo(
            driver_name="dry-run",
            platform="dry",
            identifier=f"{workflow_name}-dry-run",
        )
        self.actions: List[Tuple[str, dict]] = []
        self.artifacts: List[Tuple[str, str]] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        self.actions.append((action_name, kwargs))
        return ActionResult(success=True, message=action_name)

    def capture_artifact(self, artifact_type: str, name: str) -> ArtifactHandle:
        self.artifacts.append((artifact_type, name))
        return ArtifactHandle(
            artifact_type=artifact_type,
            path=Path("artifacts") / self.info.identifier / artifact_type / name,
        )
