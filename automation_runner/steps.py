from dataclasses import dataclass, field
from typing import Dict, Optional

from automation_core.capabilities import CapabilityRequest
from automation_runner.policies import CapabilityPolicy


def validate_step_name(name: str, label: str) -> str:
    """Validate a workflow step name and return its normalized form.

    The name must reduce to a single safe path component; the normalized
    value (not the raw input) is what callers should store and report.
    """
    if not isinstance(name, str):
        raise ValueError(f"invalid workflow {label} name")
    cleaned = name.replace("\\", "/").split("/")[-1].strip()
    if cleaned in {"", ".", ".."}:
        raise ValueError(f"invalid workflow {label} name")
    return cleaned


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
            name=validate_step_name(name, "action"),
            parameters=parameters,
        )

    @classmethod
    def artifact(
        cls,
        artifact_type: str,
        name: str,
        *,
        capture_on: str = "always",
    ) -> "WorkflowStep":
        """Declare an artifact capture step.

        ``capture_on="always"`` (default) preserves the historical shape and
        timing exactly; ``capture_on="failure"`` defers the capture until a
        preceding step fails - the runtime executes it during the failure
        branch while the session is still alive. The key is omitted for the
        default so existing step-parameter assertions stay stable.
        """
        normalized = str(capture_on or "").strip().lower()
        if normalized not in ("always", "failure"):
            raise ValueError("artifact capture_on must be 'always' or 'failure'")
        parameters = {"name": validate_step_name(name, "artifact")}
        if normalized != "always":
            parameters["capture_on"] = normalized
        return cls(
            kind="artifact",
            name=validate_step_name(artifact_type, "artifact"),
            parameters=parameters,
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
            name=validate_step_name(name, "capability"),
            request=request,
            policy=policy or CapabilityPolicy(),
        )
