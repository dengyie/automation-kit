import json
from pathlib import Path

import pytest

from automation_core.artifacts import ArtifactRecord, ArtifactStore


def test_artifact_record_serializes_metadata():
    record = ArtifactRecord(
        artifact_type="trace",
        name="trace.json",
        path=Path("/artifacts/run-1/trace/trace.json"),
        task_id="task-1",
        metadata={"source": "driver", "ok": "true"},
    )

    assert record.metadata_json() == json.dumps(
        {"ok": "true", "source": "driver"},
        sort_keys=True,
    )
    assert record.to_dict()["path"] == "/artifacts/run-1/trace/trace.json"


def test_artifact_store_rejects_invalid_name():
    store = ArtifactStore(Path("/artifacts"))

    with pytest.raises(ValueError, match="invalid artifact name"):
        store.build_path("run-1", "screenshot", "..")


def test_artifact_store_rejects_invalid_run_id():
    store = ArtifactStore(Path("/artifacts"))

    with pytest.raises(ValueError, match="invalid run_id"):
        store.build_path("..", "screenshot", "home.png")


def test_artifact_store_rejects_invalid_artifact_type():
    store = ArtifactStore(Path("/artifacts"))

    with pytest.raises(ValueError, match="invalid artifact_type"):
        store.build_path("run-1", "..", "home.png")


def test_artifact_store_normalizes_name():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path("run-1", "screenshot", "home screen.png")

    assert str(path) == "/artifacts/run-1/screenshot/home_screen.png"


def test_artifact_store_sanitizes_run_and_type_components():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path(
        "../run 42",
        "../page source",
        "../startup.xml",
    )

    assert str(path) == "/artifacts/run_42/page_source/startup.xml"


def test_artifact_store_uses_run_and_type_namespaces():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path("run-42", "ui_tree", "startup.json")

    assert str(path) == "/artifacts/run-42/ui_tree/startup.json"
