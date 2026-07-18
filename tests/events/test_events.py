from automation_core.events import (
    ArtifactEvent,
    CapabilityEndEvent,
    ErrorEvent,
    EventEnvelope,
    EventType,
    RetryAttemptEvent,
    TaskEndEvent,
    TaskStartEvent,
    retry_attempt_event_from_snapshot,
)
from automation_core.retries import RetryAttemptSnapshot


def test_event_envelope_serializes():
    envelope = EventEnvelope(
        event_type="task.start",
        task_id="task-1",
        payload={"task": "bootstrap"},
    )

    data = envelope.to_dict()

    assert data["event_type"] == "task.start"
    assert data["task_id"] == "task-1"
    assert data["payload"] == {"task": "bootstrap"}
    assert isinstance(data["event_id"], str)


def test_task_start_event_converts_to_envelope():
    event = TaskStartEvent(task_name="bootstrap", task_id="task-1")

    envelope = event.to_envelope()
    data = envelope.to_dict()

    assert data["event_type"] == EventType.TASK_START.value
    assert data["task_id"] == "task-1"
    assert data["payload"] == {
        "task_name": "bootstrap",
        "task_id": "task-1",
    }


def test_all_event_types_have_stable_values():
    assert EventType.TASK_START.value == "task.start"
    assert EventType.TASK_END.value == "task.end"
    assert EventType.RETRY_ATTEMPT.value == "retry.attempt"
    assert EventType.ERROR.value == "error"
    assert EventType.ARTIFACT.value == "artifact"
    assert EventType.CAPABILITY_END.value == "capability.end"


def test_task_start_event_fields():
    event = TaskStartEvent(task_name="bootstrap", task_id="task-1")

    assert event.task_name == "bootstrap"
    assert event.task_id == "task-1"


def test_task_end_event_fields():
    event = TaskEndEvent(task_name="bootstrap", task_id="task-1", outcome="succeeded")

    assert event.outcome == "succeeded"
    assert event.to_envelope().event_type == EventType.TASK_END.value


def test_retry_attempt_event_fields():
    event = RetryAttemptEvent(task_name="bootstrap", task_id="task-1", attempt=2, elapsed=1.5)

    assert event.attempt == 2
    assert event.elapsed == 1.5
    assert event.to_envelope().event_type == EventType.RETRY_ATTEMPT.value


def test_retry_attempt_event_can_be_created_from_snapshot():
    snapshot = RetryAttemptSnapshot(
        attempt=3,
        elapsed=1.25,
        value="not-ready",
        exception=None,
        will_retry=True,
    )

    event = retry_attempt_event_from_snapshot(
        task_name="checkout",
        task_id="task-1",
        snapshot=snapshot,
    )
    envelope = event.to_envelope()

    assert event.task_name == "checkout"
    assert event.task_id == "task-1"
    assert event.attempt == 3
    assert event.elapsed == 1.25
    assert envelope.event_type == EventType.RETRY_ATTEMPT.value


def test_error_event_fields():
    event = ErrorEvent(
        task_name="bootstrap",
        task_id="task-1",
        message="failed",
        error_type="RuntimeError",
    )

    assert event.error_type == "RuntimeError"
    assert event.to_envelope().event_type == EventType.ERROR.value


def test_artifact_event_fields():
    event = ArtifactEvent(
        task_name="bootstrap",
        task_id="task-1",
        artifact_type="screenshot",
        path="artifacts/run-1/screen.png",
    )

    assert event.path.endswith("screen.png")
    assert event.to_envelope().event_type == EventType.ARTIFACT.value


def test_capability_end_event_has_capability_scope():
    envelope = CapabilityEndEvent(
        capability="visual.challenge",
        operation="solve",
        provider="slidex",
        success=True,
        task_id="task-1",
    ).to_envelope()

    assert envelope.event_type == EventType.CAPABILITY_END.value
    assert envelope.task_id == "task-1"
    assert envelope.payload == {
        "capability": "visual.challenge",
        "operation": "solve",
        "provider": "slidex",
        "success": True,
        "task_id": "task-1",
        "error_code": None,
    }
