import json
from importlib import resources
from typing import Dict


REPORT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_RESOURCE = "report-schema-v1.json"

_SCHEMA_RESOURCES = {
    "1": "report-schema-v1.json",
    "2": "report-schema-v2.json",
}


def load_report_schema(version: str = REPORT_SCHEMA_VERSION) -> Dict[str, object]:
    resource = _SCHEMA_RESOURCES.get(version)
    if resource is None:
        raise ValueError(f"unsupported report schema version: {version}")
    schema_text = resources.read_text(
        __package__,
        resource,
        encoding="utf-8",
    )
    return json.loads(schema_text)
