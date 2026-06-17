from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from automation_core.events import ErrorEvent, EventEnvelope, TaskEndEvent, TaskStartEvent
from automation_core.tasks.lifecycle import TaskLifecycle, TaskState


T = TypeVar("T")


class TaskCancelledError(RuntimeError):
    """Raised when a task is cancelled intentionally."""


@dataclass(frozen=True)
class TaskResult(Generic[T]):
    task_id: str
    task_name: str
    state: TaskState
    success: bool
    value: Optional[T]
    error: Optional[str]
    events: List[EventEnvelope]


class TaskRunner:
    def __init__(self, task_name: str, task_id: str):
        self.task_name = task_name
        self.task_id = task_id

    def run(self, task: Callable[[], T]) -> TaskResult[T]:
        lifecycle = TaskLifecycle()
        events = [
            TaskStartEvent(
                task_name=self.task_name,
                task_id=self.task_id,
            ).to_envelope()
        ]
        lifecycle.start()
        try:
            value = task()
        except TaskCancelledError:
            lifecycle.cancel()
            events.append(
                TaskEndEvent(
                    task_name=self.task_name,
                    task_id=self.task_id,
                    outcome="cancelled",
                ).to_envelope()
            )
            return TaskResult(
                task_id=self.task_id,
                task_name=self.task_name,
                state=TaskState.CANCELLED,
                success=False,
                value=None,
                error=None,
                events=events,
            )
        except Exception as exc:
            lifecycle.fail()
            events.append(
                ErrorEvent(
                    task_name=self.task_name,
                    task_id=self.task_id,
                    message=str(exc),
                    error_type=type(exc).__name__,
                ).to_envelope()
            )
            events.append(
                TaskEndEvent(
                    task_name=self.task_name,
                    task_id=self.task_id,
                    outcome="failed",
                ).to_envelope()
            )
            return TaskResult(
                task_id=self.task_id,
                task_name=self.task_name,
                state=TaskState.FAILED,
                success=False,
                value=None,
                error=f"{type(exc).__name__}: {exc}",
                events=events,
            )

        lifecycle.succeed()
        events.append(
            TaskEndEvent(
                task_name=self.task_name,
                task_id=self.task_id,
                outcome="succeeded",
            ).to_envelope()
        )
        return TaskResult(
            task_id=self.task_id,
            task_name=self.task_name,
            state=TaskState.SUCCEEDED,
            success=True,
            value=value,
            error=None,
            events=events,
        )
