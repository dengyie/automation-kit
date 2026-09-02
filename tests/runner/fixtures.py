import asyncio
from pathlib import Path

from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_runner.runtime import WorkflowRuntime
from automation_runner.workflows import ComposedWorkflow, WorkflowStep


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
        self.cancel_actions = set()

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def execute_action(self, action_name, **kwargs):
        if action_name in self.fail_actions:
            raise RuntimeError("driver socket closed")
        if action_name in self.cancel_actions:
            raise asyncio.CancelledError()
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
    session.fail_actions.add("open")
    return session


def make_cancelling_session():
    session = CliFakeSession()
    CREATED_SESSIONS.append(session)
    session.cancel_actions.add("open")
    return session


def record_import():
    IMPORT_ATTEMPTS.append("loaded")
    return make_session


def raise_session_startup():
    raise RuntimeError("session startup failed")


def _context_metadata(context):
    return {
        "live": context.live,
        "workflow_factory": context.workflow_factory,
        "session_factory": context.session_factory,
    }


def _runtime(session_factory, context):
    return WorkflowRuntime(
        session_factory=session_factory,
        workflow_name=context.workflow_name,
        metadata=_context_metadata(context),
    )


def create_custom_workflow(session_factory, context, options):
    return ComposedWorkflow(
        _runtime(session_factory, context),
        [WorkflowStep.action("custom_action")],
    )


def create_context_workflow(session_factory, context, options):
    return ComposedWorkflow(
        _runtime(session_factory, context),
        [
            WorkflowStep.action(
                "context_action",
                workflow=context.workflow_name,
                live=context.live,
                workflow_factory=context.workflow_factory,
                session_factory=context.session_factory,
                url=options.url,
                app_id=options.app_id,
                emit_json=options.emit_json,
                report_file=options.report_file,
                parameters=options.parameters,
            )
        ],
    )


def create_kwargs_context_workflow(session_factory, **kwargs):
    context = kwargs["context"]
    options = kwargs["options"]
    return ComposedWorkflow(
        _runtime(session_factory, context),
        [
            WorkflowStep.action(
                "kwargs_context_action",
                workflow=context.workflow_name,
                url=options.url,
            )
        ],
    )


def create_raising_workflow(session_factory):
    raise RuntimeError("workflow construction failed")


def create_invalid_result_workflow(session_factory, context, options):
    class NotAResult:
        success = False

    class Workflow:
        def run(self):
            return NotAResult()

    return Workflow()


def create_cancelling_workflow(session_factory, context, options):
    return ComposedWorkflow(
        _runtime(make_cancelling_session, context),
        [WorkflowStep.action("open")],
    )


def reset():
    CREATED_SESSIONS.clear()
    IMPORT_ATTEMPTS.clear()
