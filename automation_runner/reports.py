from dataclasses import asdict, dataclass
from typing import Dict, List

from examples.workflows import ExampleWorkflowResult


@dataclass(frozen=True)
class RunnerReport:
    workflow: str
    success: bool
    session: Dict[str, str]
    actions: List[Dict[str, object]]
    artifacts: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def build_report(workflow: str, result: ExampleWorkflowResult) -> RunnerReport:
    return RunnerReport(
        workflow=workflow,
        success=result.success,
        session={
            "driver_name": result.session.driver_name,
            "platform": result.session.platform,
            "identifier": result.session.identifier,
        },
        actions=[
            {
                "success": action.success,
                "message": action.message,
            }
            for action in result.actions
        ],
        artifacts=[
            {
                "artifact_type": artifact.artifact_type,
                "path": str(artifact.path),
            }
            for artifact in result.artifacts
        ],
    )
