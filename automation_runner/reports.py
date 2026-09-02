from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from automation_core.execution import WorkflowResult as ExecutionWorkflowResult
from automation_runner.collector import ReportCollector


@dataclass(frozen=True)
class RunnerReportV2:
    """Machine-facing report built from an execution-model ``WorkflowResult``.

    The serialized shape is pinned by ``automation_runner/schemas/report-schema-v2.json``.
    """

    schema_version: str
    context: Dict[str, Any]
    status: str
    success: bool
    steps: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    failure: Optional[Dict[str, Any]]
    providers: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_report_v2(result: ExecutionWorkflowResult) -> RunnerReportV2:
    collector = ReportCollector(result.context)
    for step in result.steps:
        collector.record_step(step)
    for artifact in result.artifacts:
        collector.attach_artifact(artifact)
    for event in result.events:
        if isinstance(event, dict):
            collector.record_event(event)
        elif hasattr(event, "to_dict"):
            collector.record_event(event.to_dict())
    payload = collector.finalize(status=result.status, failure=result.failure)
    return RunnerReportV2(**payload)
