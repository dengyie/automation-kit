from pathlib import Path

from automation_core.capabilities import CapabilityResult
from automation_core.drivers import ActionResult, ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)
from automation_runner.reports import RunnerReportV2, build_report_v2


def _context():
    return ExecutionContext(
        run_id="run-1",
        task_id=None,
        workflow_name="smoke",
        metadata={"live": True, "x5sec": "leak"},
    )


def _step(step_id, **overrides):
    values = dict(
        step_id=step_id,
        step_name=f"step-{step_id}",
        kind=StepKind.ACTION,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=5,
        context=_context().for_step(step_id),
        action_result=ActionResult(
            success=True,
            message="open",
            data={"url": "https://example.test", "cookie": "leak"},
        ),
    )
    values.update(overrides)
    return StepExecutionResult(**values)


def test_build_report_v2_round_trips_a_runtime_result():
    result = WorkflowResult(
        context=_context(),
        status=WorkflowStatus.SUCCEEDED,
        steps=[_step("step-1")],
    )

    report = build_report_v2(result)
    payload = report.to_dict()

    assert isinstance(report, RunnerReportV2)
    assert payload["schema_version"] == "2"
    assert payload["status"] == "succeeded"
    assert payload["success"] is True
    assert payload["failure"] is None
    assert payload["steps"][0]["action_result"]["data"] == {
        "url": "https://example.test",
        "cookie": "[redacted]",
    }


def test_build_report_v2_redacts_metadata_and_artifact_metadata():
    capability_result = CapabilityResult(
        success=True,
        provider="slidex",
        artifacts=[
            ArtifactHandle(
                artifact_type="telemetry",
                path=Path("artifacts/run-1/telemetry.json"),
                metadata={"x5secdata": "leak", "source": "unit"},
            )
        ],
    )
    step = StepExecutionResult(
        step_id="step-1",
        step_name="step-step-1",
        kind=StepKind.CAPABILITY,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=5,
        context=_context().for_step("step-1"),
        capability_result=capability_result,
    )
    result = WorkflowResult(
        context=_context(),
        status=WorkflowStatus.SUCCEEDED,
        steps=[step],
        artifacts=list(step.capability_result.artifacts),
    )

    payload = build_report_v2(result).to_dict()

    assert payload["context"]["metadata"]["x5sec"] == "[redacted]"
    assert payload["steps"][0]["capability_result"]["artifacts"][0]["metadata"] == {
        "x5secdata": "[redacted]",
        "source": "unit",
    }
    assert payload["artifacts"][0]["metadata"] == {
        "x5secdata": "[redacted]",
        "source": "unit",
    }
    assert payload["providers"] == [
        {"provider": "slidex", "step_id": "step-1", "success": True}
    ]


def test_build_report_v2_keeps_failure_and_sequence():
    failing_step = _step(
        "step-1",
        status=StepStatus.FAILED,
        action_result=ActionResult(success=False, message="open"),
    )
    from automation_core.execution import ExecutionFailure, FailureCategory

    result = WorkflowResult(
        context=_context(),
        status=WorkflowStatus.FAILED,
        steps=[failing_step],
        failure=ExecutionFailure(
            category=FailureCategory.BUSINESS,
            code="action_failed",
            message="action failed: open",
            retryable=False,
            source="action",
        ),
    )

    payload = build_report_v2(result).to_dict()

    assert payload["status"] == "failed"
    assert payload["success"] is False
    assert payload["failure"]["category"] == "business"
    assert payload["failure"]["code"] == "action_failed"
    sequences = [event["sequence"] for event in payload["events"]]
    assert sequences == sorted(sequences)
