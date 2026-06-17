import json
from pathlib import Path

import pytest

from automation_core.actions import ActionBatchResult, ActionRequest
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.events import TaskStartEvent
from automation_core.state import RunState
from automation_runner.context import WorkflowContext
from automation_runner.reports import build_report
from automation_runner.schemas import load_report_schema
from examples.workflows import ExampleWorkflowResult


SCHEMA_PATH = Path("docs/report-schema-v1.json")


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sample_report():
    run_state = RunState(run_id="run-1", started_at=1.25)
    run_state.succeed(finished_at=2.5)
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=True,
        actions=[
            ActionResult(success=True, message="open"),
        ],
        artifacts=[
            ArtifactHandle(
                artifact_type="screenshot",
                path=Path("artifacts/run-1/screenshot/home.png"),
                metadata={"source": "driver"},
            ),
        ],
        events=[
            TaskStartEvent(
                task_name="damai-web-smoke",
                task_id="run-1",
            ).to_envelope()
        ],
        batch_result=ActionBatchResult(
            results=[
                ActionResult(success=True, message="open"),
            ],
            skipped=[
                ActionRequest(name="click_buy"),
            ],
        ),
    )
    return build_report(
        "damai-web-smoke",
        result,
        run_state=run_state,
        live=True,
        workflow_factory="pkg:create_workflow",
        session_factory="pkg:create_session",
        workflow_context=WorkflowContext(
            workflow_name="damai-web-smoke",
            live=True,
            workflow_factory="pkg:create_workflow",
            session_factory="pkg:create_session",
        ),
        elapsed_seconds=0.5,
    ).to_dict()


def _documented_report_fields():
    content = Path("docs/adding-a-workflow.md").read_text(encoding="utf-8")
    start = content.index("JSON reports currently include:")
    end = content.index("Each artifact entry contains:", start)
    fields = []
    for line in content[start:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            fields.append(stripped.removeprefix("- `").removesuffix("`"))
    return fields


def test_report_schema_v1_matches_current_top_level_report_contract():
    schema = _load_schema()
    report = _sample_report()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "Automation Kit Runner Report v1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "1"
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)


def test_workflow_guide_documents_current_top_level_report_fields():
    report = _sample_report()

    assert set(_documented_report_fields()) == set(report)


def test_report_schema_v1_documents_safe_nested_report_sections():
    schema = _load_schema()
    properties = schema["properties"]

    assert properties["status"]["enum"] == [
        "succeeded",
        "failed",
        "cancelled",
    ]
    assert properties["session"]["required"] == [
        "driver_name",
        "platform",
        "identifier",
    ]
    assert properties["run_state"]["required"] == [
        "run_id",
        "status",
        "started_at",
        "finished_at",
        "outcome",
    ]
    assert properties["actions"]["items"]["required"] == [
        "success",
        "message",
    ]
    assert "data" not in properties["actions"]["items"]["properties"]
    assert properties["artifacts"]["items"]["required"] == [
        "artifact_type",
        "path",
        "metadata",
    ]
    action_batch_schema = properties["action_batch"]["anyOf"][1]
    assert action_batch_schema["required"] == [
        "results",
        "skipped",
        "success",
    ]
    skipped_properties = action_batch_schema["properties"]["skipped"]["items"][
        "properties"
    ]
    assert "parameters" not in skipped_properties


def test_packaged_report_schema_matches_docs_schema():
    assert load_report_schema("1") == _load_schema()


def test_unknown_report_schema_version_raises_clear_error():
    with pytest.raises(ValueError, match="unsupported report schema version: 2"):
        load_report_schema("2")


def test_packaged_report_schema_loader_supports_python_38_resources(monkeypatch):
    import automation_runner.schemas as schemas

    monkeypatch.delattr(schemas.resources, "files")

    assert schemas.load_report_schema("1") == _load_schema()


def test_pyproject_includes_packaged_report_schema_resource():
    content = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'path = "automation_runner/schemas/report-schema-v1.json"' in content
    assert 'format = ["sdist", "wheel"]' in content
