from automation_core.drivers import ActionResult, SessionInfo
from automation_runner import WorkflowRunner


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(
            driver_name="fake",
            platform="test",
            identifier="run-1",
        )

    def start(self):
        raise AssertionError("workflow owns session lifecycle")

    def stop(self):
        raise AssertionError("workflow owns session lifecycle")

    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type, name):
        raise AssertionError("not used")


def test_workflow_runner_creates_session_lazily_and_returns_workflow_result():
    created = []

    def session_factory():
        session = FakeSession()
        created.append(session)
        return session

    def workflow(session):
        return session.info

    runner = WorkflowRunner(session_factory=session_factory, workflow=workflow)

    assert created == []
    assert runner.run() == SessionInfo(
        driver_name="fake",
        platform="test",
        identifier="run-1",
    )
    assert len(created) == 1


def test_workflow_runner_accepts_driver_session_factory_protocol():
    class FakeFactory:
        def __init__(self):
            self.created = []

        def create(self):
            session = FakeSession()
            self.created.append(session)
            return session

    factory = FakeFactory()
    runner = WorkflowRunner(
        session_factory=factory,
        workflow=lambda session: session.info.identifier,
    )

    assert runner.run() == "run-1"
    assert len(factory.created) == 1
