from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    live: bool
    workflow_factory: Optional[str] = None
    session_factory: Optional[str] = None


@dataclass(frozen=True)
class WorkflowOptions:
    url: Optional[str] = None
    app_id: Optional[str] = None
    emit_json: bool = False
    report_file: Optional[str] = None
