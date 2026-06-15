from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from examples.workflows import ExampleWorkflow, ExampleWorkflowResult


CREATED_SESSIONS = []
IMPORT_ATTEMPTS = []


class CliFakeSession:
    def __init__(self):
        self.info = SessionInfo(
            driver_name="fake-cli",
            platform="web",
            identifier="cli-run",
        )
        self.started = False
        self.stopped = False
        self.actions = []
        self.artifacts = []
        self.fail_actions = set()

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def execute_action(self, action_name, **kwargs):
        if action_name in self.fail_actions:
            raise RuntimeError(f"{action_name} failed")
        self.actions.append((action_name, kwargs))
        return ActionResult(success=True, message=action_name, data=kwargs)

    def capture_artifact(self, artifact_type, name):
        self.artifacts.append((artifact_type, name))
        return ArtifactHandle(artifact_type=artifact_type, path=Path(name))


def make_session():
    session = CliFakeSession()
    CREATED_SESSIONS.append(session)
    return session


def make_failing_session():
    session = CliFakeSession()
    CREATED_SESSIONS.append(session)
    session.fail_actions.add("get")
    return session


def record_import():
    IMPORT_ATTEMPTS.append("loaded")
    return make_session


def create_custom_workflow(session_factory):
    return ExampleWorkflow(
        name="custom-smoke",
        session_factory=session_factory,
        run_fn=lambda session: ExampleWorkflowResult(
            session=session.info,
            success=True,
            actions=[session.execute_action("custom_action")],
            artifacts=[],
        ),
    )


def create_context_workflow(session_factory, context, options):
    return ExampleWorkflow(
        name=context.workflow_name,
        session_factory=session_factory,
        run_fn=lambda session: ExampleWorkflowResult(
            session=session.info,
            success=True,
            actions=[
                session.execute_action(
                    "context_action",
                    workflow=context.workflow_name,
                    live=context.live,
                    workflow_factory=context.workflow_factory,
                    session_factory=context.session_factory,
                    url=options.url,
                    app_id=options.app_id,
                    emit_json=options.emit_json,
                    report_file=options.report_file,
                )
            ],
            artifacts=[],
        ),
    )


def create_kwargs_context_workflow(session_factory, **kwargs):
    context = kwargs["context"]
    options = kwargs["options"]
    return ExampleWorkflow(
        name=context.workflow_name,
        session_factory=session_factory,
        run_fn=lambda session: ExampleWorkflowResult(
            session=session.info,
            success=True,
            actions=[
                session.execute_action(
                    "kwargs_context_action",
                    workflow=context.workflow_name,
                    url=options.url,
                )
            ],
            artifacts=[],
        ),
    )


def reset():
    CREATED_SESSIONS.clear()
    IMPORT_ATTEMPTS.clear()
