from automation_core.drivers import ActionResult, ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowStatus,
)
from automation_runner.collector import ReportCollector


def test_collector_records_steps_events_and_deduplicates_event_ids():
    context = ExecutionContext(run_id="run-1", task_id=None, workflow_name="smoke")
    step_context = context.for_step("step-1")
    collector = ReportCollector(context)

    collector.record_event({"event_id": "e1", "event_type": "workflow.start"})
    collector.record_event({"event_id": "e1", "event_type": "workflow.start"})
    collector.record_step(
        StepExecutionResult(
            step_id="step-1",
            step_name="open",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=5,
            context=step_context,
            action_result=ActionResult(success=True, message="open"),
        )
    )
    collector.attach_artifact(
        ArtifactHandle(artifact_type="screenshot", path="home.png", metadata={"token": "x"})
    )

    report = collector.finalize(status=WorkflowStatus.SUCCEEDED)

    assert len(report["events"]) == 1
    assert report["events"][0]["sequence"] == 1
    assert report["steps"][0]["step_id"] == "step-1"
    assert report["artifacts"][0]["metadata"]["token"] == "[redacted]"
    assert report["schema_version"] == "2"
