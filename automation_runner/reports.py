from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from examples.workflows import ExampleWorkflowResult


@dataclass(frozen=True)
class RunnerReport:
    workflow: str
    workflow_factory: Optional[str]
    success: bool
    status: str
    run_id: str
    live: bool
    elapsed_seconds: Optional[float]
    events: List[Dict[str, object]]
    session: Dict[str, str]
    actions: List[Dict[str, object]]
    artifacts: List[Dict[str, str]]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _serialize_session(session: SessionInfo) -> Dict[str, str]:
    return {
        "driver_name": session.driver_name,
        "platform": session.platform,
        "identifier": session.identifier,
    }


def _serialize_actions(actions: List[ActionResult]) -> List[Dict[str, object]]:
    return [
        {
            "success": action.success,
            "message": action.message,
        }
        for action in actions
    ]


def _serialize_artifacts(artifacts: List[ArtifactHandle]) -> List[Dict[str, str]]:
    return [
        {
            "artifact_type": artifact.artifact_type,
            "path": str(artifact.path),
        }
        for artifact in artifacts
    ]


def build_report(
    workflow: str,
    result: ExampleWorkflowResult,
    live: bool = False,
    workflow_factory: Optional[str] = None,
    elapsed_seconds: Optional[float] = None,
    error: Optional[str] = None,
) -> RunnerReport:
    return RunnerReport(
        workflow=workflow,
        workflow_factory=workflow_factory,
        success=result.success,
        status="succeeded" if result.success else "failed",
        run_id=result.session.identifier,
        live=live,
        elapsed_seconds=elapsed_seconds,
        events=[],
        session=_serialize_session(result.session),
        actions=_serialize_actions(result.actions),
        artifacts=_serialize_artifacts(result.artifacts),
        error=error,
    )
