from dataclasses import dataclass
from typing import List

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo


@dataclass(frozen=True)
class ExampleWorkflowResult:
    session: SessionInfo
    success: bool
    actions: List[ActionResult]
    artifacts: List[ArtifactHandle]
