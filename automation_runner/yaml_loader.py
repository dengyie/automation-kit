"""Declarative YAML flow loader (schema v1, Maestro-style authoring).

A flow YAML is a thin description layer: it maps onto the exact same
``WorkflowStep`` objects Python workflows build, and execution semantics
remain 100% ``WorkflowRuntime`` - there is no second execution engine.

YAML cannot hold live objects (pages, sessions), so capability steps use
builder references: ``builder: <id>`` resolves against a builder registry
injected by the composition root (``--capability-builders module:attr``).
PyYAML is an optional dependency (``automation-kit[yaml]``); a missing
install is a clear assembly error, not a crash.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from automation_core.capabilities import CapabilityRequest
from automation_runner.flow_schema import FlowError, validate_flow_document
from automation_runner.policies import CapabilityPolicy
from automation_runner.steps import WorkflowStep

FLOW_SCHEMA_VERSION = "1"

_INTERPOLATION_RE = re.compile(r"\$\{(param|env)[:.]([^}]+)\}")

CapabilityBuilder = Callable[..., CapabilityRequest]
CapabilityBuilders = Dict[str, CapabilityBuilder]


@dataclass(frozen=True)
class LoadedFlow:
    workflow_name: str
    steps: List[WorkflowStep]
    schema_version: str = FLOW_SCHEMA_VERSION


def _load_yaml_text(text: str) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise FlowError(
            "PyYAML is required to load YAML flows; "
            "install automation-kit[yaml] or 'pip install pyyaml'"
        ) from exc
    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise FlowError(f"invalid YAML: {exc}") from exc


def _coerce_param(value: Any) -> str:
    return value if isinstance(value, str) else str(value)


def _resolve_value(
    value: Any,
    parameters: Mapping[str, str],
    env: Mapping[str, str],
) -> Any:
    if isinstance(value, dict):
        return {
            key: _resolve_value(item, parameters, env)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_value(item, parameters, env) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: "re.Match[str]") -> str:
        kind, key = match.group(1), match.group(2).strip()
        if kind == "param":
            if key not in parameters:
                raise FlowError(f"unknown flow parameter: {key}")
            return parameters[key]
        if key not in env:
            raise FlowError(f"unknown environment variable: {key}")
        return env[key]

    return _INTERPOLATION_RE.sub(replace, value)


def _build_action(step: Dict[str, Any], index: int, ctx: "_LoadContext") -> WorkflowStep:
    name = step["action"]
    raw_params = {key: value for key, value in step.items() if key != "action"}
    try:
        return WorkflowStep.action(
            name,
            **_resolve_value(raw_params, ctx.parameters, ctx.env),
        )
    except ValueError as exc:
        raise FlowError(f"flow step #{index}: {exc}") from exc


def _build_artifact(step: Dict[str, Any], index: int, ctx: "_LoadContext") -> WorkflowStep:
    body = step["artifact"]
    try:
        return WorkflowStep.artifact(
            str(body["type"]),
            str(body["name"]),
            capture_on=str(body.get("capture_on", "always")),
        )
    except (KeyError, ValueError) as exc:
        raise FlowError(f"flow step #{index}: {exc}") from exc


def _build_capability(
    step: Dict[str, Any], index: int, ctx: "_LoadContext"
) -> WorkflowStep:
    body = step["capability"]
    builder_id = str(body["builder"])
    builder = ctx.capability_builders.get(builder_id)
    if builder is None:
        raise FlowError(
            f"flow step #{index}: unknown capability builder '{builder_id}' "
            "(register it via --capability-builders)"
        )
    raw_params = body.get("params") or {}
    resolved = _resolve_value(raw_params, ctx.parameters, ctx.env)
    try:
        request = builder(**resolved)
    except TypeError as exc:
        raise FlowError(
            f"flow step #{index}: capability builder '{builder_id}' "
            f"rejected params: {exc}"
        ) from exc
    except Exception as exc:
        raise FlowError(
            f"flow step #{index}: capability builder '{builder_id}' failed: {exc}"
        ) from exc
    if not isinstance(request, CapabilityRequest):
        raise FlowError(
            f"flow step #{index}: capability builder '{builder_id}' must return "
            f"CapabilityRequest, got {type(request).__name__}"
        )
    policy = _build_policy(body.get("policy"), index)
    name = str(body.get("name") or builder_id)
    try:
        return WorkflowStep.capability(name, request=request, policy=policy)
    except ValueError as exc:
        raise FlowError(f"flow step #{index}: {exc}") from exc


def _build_policy(raw: Optional[Dict[str, Any]], index: int) -> Optional[CapabilityPolicy]:
    if raw is None:
        return None
    try:
        return CapabilityPolicy(
            timeout=raw["timeout"] if "timeout" in raw else None,
            max_attempts=raw["max_attempts"] if "max_attempts" in raw else 1,
            backoff=raw["backoff"] if "backoff" in raw else 0.0,
        )
    except (TypeError, ValueError) as exc:
        raise FlowError(f"flow step #{index}: invalid policy: {exc}") from exc


def _build_assert(step: Dict[str, Any], index: int, ctx: "_LoadContext") -> WorkflowStep:
    body = step["assert"]
    spec = body["element_present"]
    resolved = _resolve_value(spec, ctx.parameters, ctx.env)
    action_params: Dict[str, Any] = {"selector": resolved.get("selector")}
    for field in ("by", "timeout", "interval"):
        if field in resolved:
            action_params[field] = resolved[field]
    try:
        return WorkflowStep.action("wait_for_element", **action_params)
    except ValueError as exc:
        raise FlowError(f"flow step #{index}: {exc}") from exc


class _LoadContext:
    __slots__ = ("parameters", "env", "capability_builders")

    def __init__(
        self,
        parameters: Mapping[str, str],
        env: Mapping[str, str],
        capability_builders: CapabilityBuilders,
    ):
        self.parameters = parameters
        self.env = env
        self.capability_builders = capability_builders


_STEP_BUILDERS = {
    "action": _build_action,
    "artifact": _build_artifact,
    "capability": _build_capability,
    "assert": _build_assert,
}


def load_flow(
    flow_path: str,
    *,
    parameters: Optional[Mapping[str, str]] = None,
    capability_builders: Optional[CapabilityBuilders] = None,
    env: Optional[Mapping[str, str]] = None,
) -> LoadedFlow:
    """Load and validate a YAML flow into runtime ``WorkflowStep`` objects."""
    path = Path(flow_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FlowError(f"could not read flow file: {path}") from exc

    document = _load_yaml_text(text)
    validate_flow_document(document)

    declared_params = {
        key: _coerce_param(value)
        for key, value in (document.get("params") or {}).items()
    }
    merged: Dict[str, str] = {**declared_params, **dict(parameters or {})}
    load_env = dict(os.environ if env is None else env)
    context = _LoadContext(merged, load_env, dict(capability_builders or {}))

    steps: List[WorkflowStep] = []
    for index, raw_step in enumerate(document["steps"], start=1):
        marker = next(
            key for key in ("action", "artifact", "capability", "assert") if key in raw_step
        )
        builder = _STEP_BUILDERS[marker]
        steps.append(builder(raw_step, index, context))

    return LoadedFlow(workflow_name=str(document["workflow"]).strip(), steps=steps)
