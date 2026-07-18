import json
from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)
from automation_runner.reports import build_report_v2
from automation_runner.schemas import load_report_schema


def test_report_schema_v2_matches_runtime_result():
    context = ExecutionContext(run_id="run-1", task_id=None, workflow_name="smoke")
    step = StepExecutionResult(
        step_id="step-1",
        step_name="open",
        kind=StepKind.ACTION,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=3,
        context=context.for_step("step-1"),
        action_result=ActionResult(success=True, message="open"),
    )
    result = WorkflowResult(
        context=context,
        status=WorkflowStatus.SUCCEEDED,
        steps=(step,),
        artifacts=(ArtifactHandle(artifact_type="screenshot", path="home.png"),),
    )
    report = build_report_v2(result).to_dict()
    schema = load_report_schema("2")

    assert schema["properties"]["schema_version"]["const"] == "2"
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)
    assert report["steps"][0]["kind"] == "action"


def test_packaged_report_schema_v2_matches_docs_schema():
    docs_schema = json.loads(Path("docs/report-schema-v2.json").read_text(encoding="utf-8"))
    assert load_report_schema("2") == docs_schema
