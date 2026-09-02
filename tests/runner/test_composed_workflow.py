import asyncio

from automation_core.drivers import ActionResult, SessionInfo
from automation_runner.runtime import WorkflowRuntime
from automation_runner.workflows import ComposedWorkflow, WorkflowStep


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(driver_name="fake", platform="web", identifier="s-1")
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def execute_action(self, action_name, **kwargs):
        return ActionResult(success=True, message=action_name)


def _workflow(session):
    runtime = WorkflowRuntime(
        session_factory=lambda: session,
        workflow_name="composed",
    )
    return ComposedWorkflow(runtime, [WorkflowStep.action("open")])


def test_composed_workflow_exposes_runtime_name_and_steps():
    session = FakeSession()
    workflow = _workflow(session)

    assert workflow.name == "composed"
    assert [step.name for step in workflow.steps] == ["open"]
    assert workflow.runtime.workflow_name == "composed"


def test_composed_workflow_run_returns_execution_result():
    session = FakeSession()
    workflow = _workflow(session)

    result = workflow.run()

    assert result.status.value == "succeeded"
    assert [step.step_name for step in result.steps] == ["open"]
    assert session.started is True
    assert session.stopped is True


def test_composed_workflow_arun_returns_execution_result():
    session = FakeSession()
    workflow = _workflow(session)

    result = asyncio.run(workflow.arun())

    assert result.status.value == "succeeded"
