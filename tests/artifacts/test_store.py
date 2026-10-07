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
    assert Path(record.to_dict()["path"]).as_posix() == "/artifacts/run-1/trace/trace.json"


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

    assert path.as_posix() == "/artifacts/run-1/screenshot/home_screen.png"


def test_artifact_store_sanitizes_run_and_type_components():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path(
        "../run 42",
        "../page source",
        "../startup.xml",
    )

    assert path.as_posix() == "/artifacts/run_42/page_source/startup.xml"


def test_artifact_store_uses_run_and_type_namespaces():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path("run-42", "ui_tree", "startup.json")

    assert path.as_posix() == "/artifacts/run-42/ui_tree/startup.json"


def test_artifact_store_scrubs_windows_unsafe_characters():
    store = ArtifactStore(Path("artifacts"))

    path = store.build_path("192.168.1.9:43427", "screenshot", "startup.png")

    assert path.relative_to(store.root).as_posix() == (
        "192.168.1.9_43427/screenshot/startup.png"
    )


def test_artifact_store_reserved_device_name_gets_prefix():
    store = ArtifactStore(Path("artifacts"))

    path = store.build_path("CON", "screenshot", "startup.png")

    assert path.relative_to(store.root).as_posix() == "_CON/screenshot/startup.png"


def test_artifact_store_trailing_dots_and_spaces_are_dropped():
    store = ArtifactStore(Path("artifacts"))

    path = store.build_path("run 1 . ", "screenshot", "shot .png")

    assert path.relative_to(store.root).as_posix() == "run_1/screenshot/shot_.png"


def test_artifact_store_record_writes_sanitized_directory(tmp_path):
    store = ArtifactStore(tmp_path)

    record = store.record(
        run_id="10.0.2.2:5555",
        artifact_type="page_source",
        name="startup.xml",
        metadata={"ok": "true"},
    )

    record.path.parent.mkdir(parents=True, exist_ok=True)
    record.path.write_text("<hierarchy/>", encoding="utf-8")
    assert record.path.read_text(encoding="utf-8") == "<hierarchy/>"
    assert record.metadata_json() == '{"ok": "true"}'
