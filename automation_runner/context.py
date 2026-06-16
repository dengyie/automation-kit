from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    live: bool
    workflow_factory: Optional[str] = None
    session_factory: Optional[str] = None

    def to_dict(self):
        return {
            "workflow_name": self.workflow_name,
            "live": self.live,
            "workflow_factory": self.workflow_factory,
            "session_factory": self.session_factory,
        }


@dataclass(frozen=True)
class WorkflowOptions:
    url: Optional[str] = None
    app_id: Optional[str] = None
    emit_json: bool = False
    report_file: Optional[str] = None

    def to_dict(self):
        return {
            "url": self.url,
            "app_id": self.app_id,
            "emit_json": self.emit_json,
            "report_file": self.report_file,
        }
