"""Task lifecycle primitives for automation workflows."""

from automation_core.tasks.lifecycle import TaskLifecycle, TaskState, TaskTransitionError
from automation_core.tasks.runner import TaskResult, TaskRunner

__all__ = [
    "TaskLifecycle",
    "TaskResult",
    "TaskRunner",
    "TaskState",
    "TaskTransitionError",
]
