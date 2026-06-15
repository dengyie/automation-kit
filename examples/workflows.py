from dataclasses import dataclass
from typing import Callable, List

from automation_core.drivers import (
    ActionResult,
    ArtifactHandle,
    DriverSession,
    SessionInfo,
)


@dataclass(frozen=True)
class ExampleWorkflowResult:
    session: SessionInfo
    success: bool
    actions: List[ActionResult]
    artifacts: List[ArtifactHandle]


@dataclass(frozen=True)
class ExampleWorkflow:
    session_factory: Callable[[], DriverSession]
    run_fn: Callable[[DriverSession], ExampleWorkflowResult]

    def run(self) -> ExampleWorkflowResult:
        session = self.session_factory()
        return self.run_fn(session)
