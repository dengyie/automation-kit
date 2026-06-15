from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class SessionInfo:
    driver_name: str
    platform: str
    identifier: str


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str = ""
    data: Optional[Any] = None


@dataclass(frozen=True)
class ArtifactHandle:
    artifact_type: str
    path: Path


@runtime_checkable
class ElementHandle(Protocol):
    identifier: str

    def click(self) -> ActionResult:
        ...

    def input_text(self, text: str) -> ActionResult:
        ...

    def text(self) -> str:
        ...


@runtime_checkable
class DriverSession(Protocol):
    info: SessionInfo

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        ...

    def capture_artifact(self, artifact_type: str, name: str) -> ArtifactHandle:
        ...


@runtime_checkable
class ElementLookupSession(DriverSession, Protocol):
    def find_element(self, selector: str) -> ElementHandle:
        ...


@runtime_checkable
class DriverSessionFactory(Protocol):
    def create(self) -> DriverSession:
        ...
