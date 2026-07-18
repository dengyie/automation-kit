from pathlib import Path

import pytest

from automation_core.capabilities import (
    CapabilityManifest,
    CapabilityRequest,
    CapabilityResult,
)
from automation_core.drivers import ArtifactHandle
from automation_core.events import EventEnvelope


def test_manifest_declares_supported_operation_and_platform():
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("web", "android"),
    )

    assert manifest.supports("solve", platform="web") is True
    assert manifest.supports("solve", platform="image") is False
    assert manifest.to_dict()["operations"] == ["solve"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": "", "version": "1.0.0", "operations": ("solve",)}, "name"),
        ({"name": "visual.challenge", "version": "", "operations": ("solve",)}, "version"),
        ({"name": "visual.challenge", "version": "1.0.0", "operations": ()}, "operations"),
        (
            {"name": "Visual Challenge", "version": "1.0.0", "operations": ("solve",)},
            "name",
        ),
    ],
)
def test_manifest_rejects_invalid_contract(kwargs, message):
    with pytest.raises(ValueError, match=message):
        CapabilityManifest(**kwargs)


def test_request_rejects_blank_capability_or_operation():
    with pytest.raises(ValueError, match="capability"):
        CapabilityRequest(capability="", operation="solve")

    with pytest.raises(ValueError, match="operation"):
        CapabilityRequest(capability="visual.challenge", operation=" ")


def test_result_to_dict_redacts_metadata_and_serializes_contract_objects():
    result = CapabilityResult(
        success=True,
        provider="fake-visual",
        data={"path": Path("result.json")},
        artifacts=[
            ArtifactHandle(
                artifact_type="telemetry",
                path=Path("artifacts/run-1/telemetry.json"),
                metadata={"token": "secret", "source": "unit"},
            )
        ],
        events=[
            EventEnvelope(
                event_type="capability.end",
                task_id="task-1",
                payload={"authorization": "secret", "success": True},
            )
        ],
        metadata={"cookie": "secret", "run_id": "run-1"},
    )

    payload = result.to_dict()

    assert payload["data"]["path"] == "result.json"
    assert payload["artifacts"][0]["metadata"]["token"] == "[redacted]"
    assert payload["events"][0]["payload"]["authorization"] == "[redacted]"
    assert payload["metadata"]["cookie"] == "[redacted]"
    assert payload["metadata"]["run_id"] == "run-1"
