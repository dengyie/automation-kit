import json
from pathlib import Path

import pytest

from automation_runner.schemas import load_report_schema


ROOT = Path(__file__).resolve().parents[2]
DOC_SCHEMAS = ROOT / "docs"
PACKAGED_SCHEMAS = ROOT / "automation_runner" / "schemas"

V1_FROZEN_TOP_LEVEL_FIELDS = {
    "schema_version",
    "workflow",
    "workflow_factory",
    "session_factory",
    "workflow_context",
    "success",
    "status",
    "run_id",
    "run_state",
    "live",
    "elapsed_seconds",
    "events",
    "session",
    "actions",
    "artifacts",
    "error",
    "action_batch",
}


def test_load_report_schema_defaults_to_v2():
    schema = load_report_schema()

    assert schema["title"] == "Automation Kit Runner Report v2"
    assert schema["properties"]["schema_version"]["const"] == "2"


def test_frozen_v1_schema_fields_are_unchanged():
    schema = load_report_schema("1")

    assert schema["properties"]["schema_version"]["const"] == "1"
    assert set(schema["properties"]) == V1_FROZEN_TOP_LEVEL_FIELDS
    artifact_props = schema["properties"]["artifacts"]["items"]
    assert set(artifact_props["properties"]) == {
        "artifact_type",
        "path",
        "metadata",
    }


def test_packaged_schema_copies_match_docs_resources():
    for name in ("report-schema-v1.json", "report-schema-v2.json"):
        docs = (DOC_SCHEMAS / name).read_text(encoding="utf-8")
        packaged = (PACKAGED_SCHEMAS / name).read_text(encoding="utf-8")
        assert json.loads(docs) == json.loads(packaged)


def test_load_report_schema_rejects_unknown_version():
    with pytest.raises(ValueError, match="unsupported report schema version"):
        load_report_schema("99")
