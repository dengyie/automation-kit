import pytest

from automation_core.drivers import ActionResult, ArtifactHandle
from automation_core.execution import (
    ExecutionContext,
    ExecutionFailure,
    FailureCategory,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)


def test_step_result_requires_exactly_one_result_kind():
    context = ExecutionContext(run_id="run-1", task_id="step-1", workflow_name="smoke")
    action = ActionResult(success=True, message="open")

    result = StepExecutionResult(
        step_id="step-1",
        step_name="open-home",
        kind=StepKind.ACTION,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=10,
        context=context,
        action_result=action,
    )

    assert result.to_dict()["action_result"] == {
        "success": True,
        "message": "open",
        "data": None,
    }

    with pytest.raises(ValueError, match="exactly one"):
        StepExecutionResult(
            step_id="step-1",
            step_name="invalid",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=0,
            context=context,
        )


def test_workflow_result_steps_are_source_of_truth_and_legacy_views_are_derived():
    context = ExecutionContext(run_id="run-1", task_id=None, workflow_name="smoke")
    step_context = context.for_step("step-1")
    action = ActionResult(success=True, message="open")
    artifact = ArtifactHandle(artifact_type="screenshot", path="home.png")
    step = StepExecutionResult(
        step_id="step-1",
        step_name="open-home",
        kind=StepKind.ACTION,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=10,
        context=step_context,
        action_result=action,
    )
    workflow = WorkflowResult(
        context=context,
        status=WorkflowStatus.SUCCEEDED,
        steps=(step,),
        artifacts=(artifact,),
    )

    assert workflow.success is True
    assert workflow.actions == (action,)
    assert workflow.capabilities == ()
    assert workflow.artifacts == (artifact,)
    assert workflow.to_dict()["steps"][0]["step_id"] == "step-1"


def test_failed_workflow_requires_failure_or_failed_step():
    context = ExecutionContext(run_id="run-1", task_id=None, workflow_name="smoke")
    failure = ExecutionFailure(
        category=FailureCategory.CLEANUP,
        code="cleanup_failed",
        message="cleanup failed",
        retryable=False,
        source="runtime",
    )

    with pytest.raises(ValueError, match="failure"):
        WorkflowResult(
            context=context,
            status=WorkflowStatus.FAILED,
            steps=(),
        )

    result = WorkflowResult(
        context=context,
        status=WorkflowStatus.FAILED,
        steps=(),
        failure=failure,
    )
    assert result.success is False
