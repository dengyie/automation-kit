import pytest

from automation_core.tasks import TaskLifecycle, TaskState, TaskTransitionError


def test_task_starts_from_pending():
    lifecycle = TaskLifecycle()

    lifecycle.start()

    assert lifecycle.state == TaskState.RUNNING


def test_task_can_succeed_from_running():
    lifecycle = TaskLifecycle()
    lifecycle.start()

    lifecycle.succeed()

    assert lifecycle.state == TaskState.SUCCEEDED


def test_task_can_fail_from_running():
    lifecycle = TaskLifecycle()
    lifecycle.start()

    lifecycle.fail()

    assert lifecycle.state == TaskState.FAILED


def test_task_can_cancel_from_pending():
    lifecycle = TaskLifecycle()

    lifecycle.cancel()

    assert lifecycle.state == TaskState.CANCELLED


def test_task_rejects_invalid_transition():
    lifecycle = TaskLifecycle(state=TaskState.SUCCEEDED)

    with pytest.raises(TaskTransitionError, match="invalid task transition"):
        lifecycle.start()


def test_task_rejects_invalid_initial_state():
    with pytest.raises(ValueError, match="state must be a TaskState"):
        TaskLifecycle(state="pending")


def test_task_rejects_invalid_next_state():
    lifecycle = TaskLifecycle()

    with pytest.raises(ValueError, match="next_state must be a TaskState"):
        lifecycle.transition_to("running")
