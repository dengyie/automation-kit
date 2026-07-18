from automation_core.execution import ExecutionContext, WorkflowStatus
from automation_runner.collector import ReportCollector


def test_collector_assigns_stable_sequence_independent_of_completion_order():
    collector = ReportCollector(
        ExecutionContext(run_id="run-1", task_id=None, workflow_name="smoke")
    )

    collector.record_event({"event_id": "a", "event_type": "step.start"})
    collector.record_event({"event_id": "b", "event_type": "step.end"})
    report = collector.finalize(status=WorkflowStatus.SUCCEEDED)

    assert [event["sequence"] for event in report["events"]] == [1, 2]
    assert [event["event_type"] for event in report["events"]] == [
        "step.start",
        "step.end",
    ]
