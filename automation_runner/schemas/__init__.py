import json
from importlib import resources
from typing import Dict


REPORT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_RESOURCE = "report-schema-v1.json"


def load_report_schema(version: str = REPORT_SCHEMA_VERSION) -> Dict[str, object]:
    if version != REPORT_SCHEMA_VERSION:
        raise ValueError(f"unsupported report schema version: {version}")
    schema_text = resources.read_text(
        __package__,
        REPORT_SCHEMA_RESOURCE,
        encoding="utf-8",
    )
    return json.loads(schema_text)
