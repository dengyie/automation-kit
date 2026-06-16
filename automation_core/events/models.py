from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from automation_core.retries import RetryAttemptSnapshot


class EventType(str, Enum):
    TASK_START = "task.start"
    TASK_END = "task.end"
    RETRY_ATTEMPT = "retry.attempt"
    ERROR = "error"
    ARTIFACT = "artifact"


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str = field(default_factory=lambda: uuid4().hex)
    event_type: str = ""
    task_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = str(self.event_type)
        data["payload"] = dict(self.payload)
        return data


def _payload(event: object) -> Dict[str, Any]:
    return asdict(event)


@dataclass(frozen=True)
class TaskStartEvent:
    task_name: str
    task_id: str

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=EventType.TASK_START.value,
            task_id=self.task_id,
            payload=_payload(self),
        )


@dataclass(frozen=True)
class TaskEndEvent:
    task_name: str
    task_id: str
    outcome: str

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=EventType.TASK_END.value,
            task_id=self.task_id,
            payload=_payload(self),
        )


@dataclass(frozen=True)
class RetryAttemptEvent:
    task_name: str
    task_id: str
    attempt: int
    elapsed: float

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=EventType.RETRY_ATTEMPT.value,
            task_id=self.task_id,
            payload=_payload(self),
        )


def retry_attempt_event_from_snapshot(
    *,
    task_name: str,
    task_id: str,
    snapshot: RetryAttemptSnapshot,
) -> RetryAttemptEvent:
    return RetryAttemptEvent(
        task_name=task_name,
        task_id=task_id,
        attempt=snapshot.attempt,
        elapsed=snapshot.elapsed,
    )


@dataclass(frozen=True)
class ErrorEvent:
    task_name: str
    task_id: str
    message: str
    error_type: str

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=EventType.ERROR.value,
            task_id=self.task_id,
            payload=_payload(self),
        )


@dataclass(frozen=True)
class ArtifactEvent:
    task_name: str
    task_id: str
    artifact_type: str
    path: str

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=EventType.ARTIFACT.value,
            task_id=self.task_id,
            payload=_payload(self),
        )
