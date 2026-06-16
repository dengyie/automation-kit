from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from automation_core.actions import ActionBatchResult
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.state import RunState
from automation_runner.context import WorkflowContext
from examples.workflows import ExampleWorkflowResult


SENSITIVE_METADATA_TERMS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True)
class RunnerReport:
    workflow: str
    workflow_factory: Optional[str]
    session_factory: Optional[str]
    workflow_context: Dict[str, object]
    success: bool
    status: str
    run_id: str
    run_state: Dict[str, object]
    live: bool
    elapsed_seconds: Optional[float]
    events: List[Dict[str, object]]
    session: Dict[str, str]
    actions: List[Dict[str, object]]
    artifacts: List[Dict[str, object]]
    error: Optional[str] = None
    action_batch: Optional[Dict[str, object]] = None

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


def _serialize_action_batch(batch_result: Optional[ActionBatchResult]) -> Optional[Dict[str, object]]:
    if batch_result is None:
        return None
    return batch_result.to_dict()


def _serialize_metadata(metadata: Dict[str, str]) -> Dict[str, str]:
    safe_metadata = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(term in lowered for term in SENSITIVE_METADATA_TERMS):
            safe_metadata[key] = "[redacted]"
        else:
            safe_metadata[key] = value
    return safe_metadata


def _serialize_artifacts(artifacts: List[ArtifactHandle]) -> List[Dict[str, object]]:
    return [
        {
            "artifact_type": artifact.artifact_type,
            "path": str(artifact.path),
            "metadata": _serialize_metadata(artifact.metadata),
        }
        for artifact in artifacts
    ]


def _serialize_workflow_context(context: WorkflowContext) -> Dict[str, object]:
    return context.to_dict()


def build_report(
    workflow: str,
    result: ExampleWorkflowResult,
    run_state: Optional[RunState] = None,
    live: bool = False,
    workflow_factory: Optional[str] = None,
    session_factory: Optional[str] = None,
    workflow_context: Optional[WorkflowContext] = None,
    elapsed_seconds: Optional[float] = None,
    error: Optional[str] = None,
) -> RunnerReport:
    state = run_state or RunState(run_id=result.session.identifier)
    if run_state is None:
        if result.success:
            state.succeed()
        else:
            state.fail()
    return RunnerReport(
        workflow=workflow,
        workflow_factory=workflow_factory,
        session_factory=session_factory,
        workflow_context=_serialize_workflow_context(
            workflow_context
            or WorkflowContext(
                workflow_name=workflow,
                live=live,
                workflow_factory=workflow_factory,
                session_factory=session_factory,
            )
        ),
        success=result.success,
        status="succeeded" if result.success else "failed",
        run_id=result.session.identifier,
        run_state={
            "run_id": state.run_id,
            "status": state.status.value,
            "started_at": state.started_at,
            "finished_at": state.finished_at,
            "outcome": state.outcome,
        },
        live=live,
        elapsed_seconds=elapsed_seconds,
        events=[envelope.to_dict() for envelope in result.events],
        session=_serialize_session(result.session),
        actions=_serialize_actions(result.actions),
        action_batch=_serialize_action_batch(result.batch_result),
        artifacts=_serialize_artifacts(result.artifacts),
        error=error if error is not None else result.error,
    )
