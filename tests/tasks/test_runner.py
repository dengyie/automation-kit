import pytest

from automation_core.tasks import TaskCancelledError, TaskResult, TaskRunner


def test_task_runner_returns_success_result_and_events():
    runner = TaskRunner(task_name="open-home", task_id="task-1")

    result = runner.run(lambda: "ok")

    assert isinstance(result, TaskResult)
    assert result.success is True
    assert result.value == "ok"
    assert result.error is None
    assert [event.event_type for event in result.events] == [
        "task.start",
        "task.end",
    ]
    assert result.events[0].payload == {
        "task_name": "open-home",
        "task_id": "task-1",
    }
    assert result.events[-1].payload["outcome"] == "succeeded"


def test_task_runner_returns_failure_result_and_error_event():
    runner = TaskRunner(task_name="open-home", task_id="task-1")

    def fail():
        raise RuntimeError("navigation failed")

    result = runner.run(fail)

    assert result.success is False
    assert result.value is None
    assert result.error == "RuntimeError: navigation failed"
    assert [event.event_type for event in result.events] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert result.events[1].payload == {
        "task_name": "open-home",
        "task_id": "task-1",
        "message": "navigation failed",
        "error_type": "RuntimeError",
    }
    assert result.events[-1].payload["outcome"] == "failed"


def test_task_runner_returns_cancelled_result_and_terminal_events():
    runner = TaskRunner(task_name="stop-now", task_id="task-1")

    def cancel():
        raise TaskCancelledError("user requested stop")

    result = runner.run(cancel)

    assert isinstance(result, TaskResult)
    assert result.success is False
    assert result.state.value == "cancelled"
    assert result.value is None
    assert result.error is None
    assert [event.event_type for event in result.events] == [
        "task.start",
        "task.end",
    ]
    assert result.events[-1].payload["outcome"] == "cancelled"


def test_task_runner_does_not_swallow_keyboard_interrupt():
    runner = TaskRunner(task_name="interrupt", task_id="task-1")

    def interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        runner.run(interrupt)
