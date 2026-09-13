"""Structural validation for declarative YAML flow documents (schema v1).

The published machine-readable contract lives in
``automation_runner/schemas/flow-schema-v1.json``; this module is the
hand-written validator that enforces the same shape without pulling a
JSON Schema dependency into the runner. The two must stay in sync - the
schema file is documentation-grade, this validator is authoritative.
"""

import json
from importlib import resources
from typing import Any, Dict, List, Optional

FLOW_SCHEMA_VERSION = "1"
FLOW_SCHEMA_RESOURCE = "flow-schema-v1.json"

STEP_MARKERS = ("action", "artifact", "capability", "assert")


class FlowError(ValueError):
    """Raised when a flow document is invalid; maps to CLI assembly errors."""


def load_flow_schema() -> Dict[str, Any]:
    text = resources.read_text(
        __package__.rsplit(".", 1)[0] + ".schemas",
        FLOW_SCHEMA_RESOURCE,
        encoding="utf-8",
    )
    return json.loads(text)


def _require_mapping(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise FlowError(f"{label} must be a mapping")
    return value


def validate_flow_document(document: Any) -> None:
    """Validate the document shape; raises :class:`FlowError` on violation."""
    doc = _require_mapping(document, "flow document")

    name = doc.get("workflow")
    if not isinstance(name, str) or not name.strip():
        raise FlowError("flow 'workflow' must be a non-blank string")

    params = doc.get("params", {})
    params = _require_mapping(params, "flow 'params'")
    for key, value in params.items():
        if not isinstance(key, str) or not key.strip():
            raise FlowError("flow 'params' keys must be non-blank strings")
        if not isinstance(value, (str, int, float, bool)):
            raise FlowError(
                f"flow param '{key}' must be a scalar (string/number/bool)"
            )

    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        raise FlowError("flow 'steps' must be a non-empty list")

    for index, step in enumerate(steps, start=1):
        _validate_step(step, index)


def _validate_step(step: Any, index: int) -> None:
    label = f"flow step #{index}"
    step_map = _require_mapping(step, label)
    markers = [key for key in STEP_MARKERS if key in step_map]
    if not markers:
        raise FlowError(
            f"{label} must declare exactly one of: {', '.join(STEP_MARKERS)}"
        )
    if len(markers) > 1:
        raise FlowError(
            f"{label} declares multiple step markers: {', '.join(sorted(markers))}"
        )
    marker = markers[0]
    body = step_map[marker]

    if marker == "action":
        if not isinstance(body, str) or not body.strip():
            raise FlowError(f"{label} 'action' must be a non-blank action name")
        return

    body = _require_mapping(body, f"{label} '{marker}'")

    if marker == "artifact":
        for field in ("type", "name"):
            value = body.get(field)
            if not isinstance(value, str) or not value.strip():
                raise FlowError(f"{label} 'artifact' requires a non-blank '{field}'")
        capture_on = body.get("capture_on", "always")
        if capture_on not in ("always", "failure"):
            raise FlowError(
                f"{label} 'artifact' capture_on must be 'always' or 'failure'"
            )
        return

    if marker == "capability":
        builder = body.get("builder")
        if not isinstance(builder, str) or not builder.strip():
            raise FlowError(f"{label} 'capability' requires a non-blank 'builder'")
        step_params = body.get("params", {})
        _require_mapping(step_params, f"{label} 'capability' params")
        policy = body.get("policy")
        if policy is not None:
            policy = _require_mapping(policy, f"{label} 'capability' policy")
            for field in ("timeout", "max_attempts", "backoff"):
                value = policy.get(field)
                if value is None:
                    continue
                if field == "max_attempts":
                    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                        raise FlowError(
                            f"{label} policy 'max_attempts' must be an integer >= 1"
                        )
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                    raise FlowError(
                        f"{label} policy '{field}' must be a number >= 0"
                    )
        return

    # marker == "assert"
    supported = ("element_present",)
    asserted = [key for key in supported if key in body]
    if len(body) != 1 or not asserted:
        raise FlowError(
            f"{label} 'assert' must contain exactly one of: {', '.join(supported)}"
        )
    spec = _require_mapping(body[asserted[0]], f"{label} 'assert' element_present")
    selector = spec.get("selector")
    if not isinstance(selector, str) or not selector.strip():
        raise FlowError(
            f"{label} 'assert.element_present' requires a non-blank 'selector'"
        )


def unknown_marker_keys(
    step: Dict[str, Any], marker: str, allowed: Optional[List[str]] = None
) -> List[str]:
    """Return keys on a step mapping that are not the marker or allowed fields."""
    reserved = {marker} | set(allowed or ())
    return [key for key in step if key not in reserved]
