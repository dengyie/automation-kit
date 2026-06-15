from pathlib import Path
from automation_core.artifacts import ArtifactRecord, ArtifactStore
from automation_core.drivers import (
    ActionResult,
    ArtifactHandle,
    DriverSession,
    DriverSessionFactory,
    SessionInfo,
)


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="session-1")
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def execute_action(self, action_name: str, **kwargs):
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type: str, name: str):
        return ArtifactHandle(artifact_type=artifact_type, path=Path("/tmp") / name)


class FakeFactory:
    def create(self):
        return FakeSession()


def test_session_info_fields():
    info = SessionInfo(driver_name="fake", platform="android", identifier="device-1")

    assert info.driver_name == "fake"
    assert info.platform == "android"
    assert info.identifier == "device-1"


def test_action_result_fields():
    result = ActionResult(success=True, message="ok", data={"step": 1})

    assert result.success is True
    assert result.message == "ok"
    assert result.data == {"step": 1}


def test_artifact_handle_fields():
    handle = ArtifactHandle(artifact_type="screenshot", path=Path("/tmp/screen.png"))

    assert handle.artifact_type == "screenshot"
    assert str(handle.path).endswith("screen.png")


def test_fake_session_implements_driver_contract():
    session = FakeSession()

    assert isinstance(session, DriverSession)
    session.start()
    result = session.execute_action("tap", x=1, y=2)

    assert session.started is True
    assert result.success is True
    assert result.message == "tap"
    assert result.data == {"x": 1, "y": 2}
    assert session.capture_artifact("image", "one.png").artifact_type == "image"


def test_fake_factory_creates_sessions():
    factory = FakeFactory()

    session = factory.create()

    assert isinstance(session, FakeSession)
    assert session.info.identifier == "session-1"


def test_artifact_store_builds_namespaced_paths():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path("run-1", "screenshot", "home screen.png")

    assert str(path) == "/artifacts/run-1/screenshot/home_screen.png"


def test_artifact_store_records_metadata():
    store = ArtifactStore(Path("/artifacts"))

    record = store.record(
        run_id="run-1",
        artifact_type="trace",
        name="trace.json",
        task_id="task-1",
        metadata={"source": "driver"},
    )

    assert isinstance(record, ArtifactRecord)
    assert record.task_id == "task-1"
    assert record.metadata == {"source": "driver"}
    assert record.to_dict()["path"] == "/artifacts/run-1/trace/trace.json"
