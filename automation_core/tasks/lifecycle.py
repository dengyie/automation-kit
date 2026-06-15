from dataclasses import dataclass
from enum import Enum


class TaskTransitionError(RuntimeError):
    """Raised when a task transition is invalid."""


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS = {
    TaskState.PENDING: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.SUCCEEDED: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}


@dataclass
class TaskLifecycle:
    """Minimal task lifecycle state machine."""

    state: TaskState = TaskState.PENDING

    def __post_init__(self) -> None:
        if not isinstance(self.state, TaskState):
            raise ValueError("state must be a TaskState")

    def transition_to(self, next_state: TaskState) -> None:
        if not isinstance(next_state, TaskState):
            raise ValueError("next_state must be a TaskState")
        if next_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise TaskTransitionError(
                f"invalid task transition: {self.state.value} -> {next_state.value}"
            )
        self.state = next_state

    def start(self) -> None:
        self.transition_to(TaskState.RUNNING)

    def succeed(self) -> None:
        self.transition_to(TaskState.SUCCEEDED)

    def fail(self) -> None:
        self.transition_to(TaskState.FAILED)

    def cancel(self) -> None:
        self.transition_to(TaskState.CANCELLED)
