from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_runner import WorkflowContext, WorkflowOptions
from automation_runner.workflows import (
    ManagedWorkflow,
    WorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)


class FakeSession:
    def __init__(self):
        self.info = SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="public-workflow",
        )
        self.actions = []

    def start(self):
        return None

    def stop(self):
        return None

    def execute_action(self, action_name, **kwargs):
        self.actions.append((action_name, kwargs))
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type, name):
        return ArtifactHandle(artifact_type=artifact_type, path=Path(name))


def test_run_workflow_steps_is_importable_from_automation_runner():
    session = FakeSession()

    result = run_workflow_steps(
        session,
        [WorkflowStep.action("open", url="https://example.test")],
    )

    assert result.success is True
    assert result.actions[0].message == "open"


def test_managed_workflow_wraps_session_factory_without_examples_package():
    session = FakeSession()
    workflow = ManagedWorkflow(
        name="public-smoke",
        session_factory=lambda: session,
        run_fn=lambda current_session: WorkflowResult(
            session=current_session.info,
            success=True,
            actions=[
                current_session.execute_action("open", url="https://example.test")
            ],
            artifacts=[],
        ),
    )

    result = workflow.run()

    assert result.success is True
    assert result.events[0].event_type == "task.start"
    assert result.events[-1].event_type == "task.end"


def test_public_runner_context_and_options_stay_compatible():
    context = WorkflowContext(workflow_name="public-smoke", live=False)
    options = WorkflowOptions(url="https://example.test")

    assert context.to_dict()["workflow_name"] == "public-smoke"
    assert options.to_dict()["url"] == "https://example.test"
