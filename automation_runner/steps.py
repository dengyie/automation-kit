from dataclasses import dataclass, field
from typing import Dict, Optional

from automation_core.capabilities import CapabilityRequest
from automation_runner.policies import CapabilityPolicy


def _validate_name(name: str, label: str) -> str:
    if not isinstance(name, str):
        raise ValueError(f"invalid workflow {label} name")
    cleaned = name.replace("\\", "/").split("/")[-1].strip()
    if cleaned in {"", ".", ".."}:
        raise ValueError(f"invalid workflow {label} name")
    return name


@dataclass(frozen=True)
class WorkflowStep:
    kind: str
    name: str
    parameters: Dict[str, object] = field(default_factory=dict)
    request: Optional[CapabilityRequest] = None
    policy: Optional[CapabilityPolicy] = None

    @classmethod
    def action(cls, name: str, **parameters: object) -> "WorkflowStep":
        return cls(
            kind="action",
            name=_validate_name(name, "action"),
            parameters=parameters,
        )

    @classmethod
    def artifact(cls, artifact_type: str, name: str) -> "WorkflowStep":
        return cls(
            kind="artifact",
            name=artifact_type,
            parameters={"name": _validate_name(name, "artifact")},
        )

    @classmethod
    def capability(
        cls,
        name: str,
        *,
        request: CapabilityRequest,
        policy: Optional[CapabilityPolicy] = None,
    ) -> "WorkflowStep":
        if not isinstance(request, CapabilityRequest):
            raise ValueError("capability step requires CapabilityRequest")
        return cls(
            kind="capability",
            name=_validate_name(name, "capability"),
            request=request,
            policy=policy or CapabilityPolicy(),
        )
