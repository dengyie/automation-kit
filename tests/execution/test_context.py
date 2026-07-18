import pytest

from automation_core.execution import ExecutionContext


def test_root_context_derives_step_identity_without_mutating_root():
    root = ExecutionContext(
        run_id="run-1",
        task_id=None,
        workflow_name="smoke",
        correlation_id="trace-1",
        deadline=123.0,
        metadata={"token": "private", "scene": "home"},
    )

    step = root.for_step("step-1")

    assert root.task_id is None
    assert step.task_id == "step-1"
    assert step.run_id == root.run_id
    assert step.workflow_name == root.workflow_name
    assert step.correlation_id == root.correlation_id
    assert step.deadline == root.deadline
    assert root.metadata == {"token": "private", "scene": "home"}
    assert step.metadata == root.metadata


def test_context_rejects_invalid_identity_and_reserved_metadata():
    with pytest.raises(ValueError, match="run_id"):
        ExecutionContext(
            run_id="",
            task_id=None,
            workflow_name="smoke",
        )

    with pytest.raises(ValueError, match="task_id"):
        ExecutionContext(
            run_id="run-1",
            task_id="",
            workflow_name="smoke",
        )

    with pytest.raises(ValueError, match="reserved"):
        ExecutionContext(
            run_id="run-1",
            task_id=None,
            workflow_name="smoke",
            metadata={"run_id": "spoof"},
        )


def test_context_is_immutable_and_serialization_redacts_unsafe_values():
    context = ExecutionContext(
        run_id="run-1",
        task_id=None,
        workflow_name="smoke",
        metadata={"authorization": "secret", "page": object()},
    )

    with pytest.raises((AttributeError, TypeError)):
        context.run_id = "run-2"

    assert context.to_dict() == {
        "run_id": "run-1",
        "task_id": None,
        "workflow_name": "smoke",
        "correlation_id": None,
        "deadline": None,
        "metadata": {
            "authorization": "[redacted]",
            "page": "<object>",
        },
    }
