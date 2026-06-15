from automation_runner.context import WorkflowContext, WorkflowOptions


def test_workflow_context_records_runner_metadata():
    context = WorkflowContext(
        workflow_name="tests.runner.fixtures:create_context_workflow",
        live=True,
        workflow_factory="tests.runner.fixtures:create_context_workflow",
        session_factory="tests.runner.fixtures:make_session",
    )

    assert context.workflow_name == "tests.runner.fixtures:create_context_workflow"
    assert context.live is True
    assert context.workflow_factory == "tests.runner.fixtures:create_context_workflow"
    assert context.session_factory == "tests.runner.fixtures:make_session"


def test_workflow_options_records_runner_inputs():
    options = WorkflowOptions(
        url="https://example.test/damai",
        app_id="cn.damai",
        emit_json=True,
        report_file="reports/run.json",
    )

    assert options.url == "https://example.test/damai"
    assert options.app_id == "cn.damai"
    assert options.emit_json is True
    assert options.report_file == "reports/run.json"
