from dataclasses import dataclass
from typing import Callable, List, Optional

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
    error: Optional[str] = None


@dataclass(frozen=True)
class ExampleWorkflow:
    session_factory: Callable[[], DriverSession]
    run_fn: Callable[[DriverSession], ExampleWorkflowResult]

    def run(self) -> ExampleWorkflowResult:
        session = self.session_factory()
        try:
            return self.run_fn(session)
        except Exception as exc:
            return ExampleWorkflowResult(
                session=session.info,
                success=False,
                actions=[],
                artifacts=[],
                error=f"{type(exc).__name__}: {exc}",
            )
