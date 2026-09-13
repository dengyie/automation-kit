"""Offline single-file HTML viewer for report schema v2 runs.

Pure-local, zero-network rendering: the report JSON plus its referenced
artifact files are folded into one HTML file (steps/events timeline,
failure details, embedded screenshots). Sensitive values are expected to
be already redacted at the report boundary; the viewer never reads the
network and embeds only image artifacts that exist and fit the size cap.
"""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from importlib import resources

MAX_EMBED_BYTES = 5 * 1024 * 1024
TEMPLATE_RESOURCE = "viewer-template.html"
_DATA_PLACEHOLDER = "__REPORT_DATA__"

_EMBEDABLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


class ViewerError(ValueError):
    """Raised when a report cannot be rendered."""


def load_report(report_path: str) -> Dict[str, Any]:
    path = Path(report_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ViewerError(f"could not read report file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ViewerError(f"report file is not valid JSON: {path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("steps"), list):
        raise ViewerError(f"not a report schema v2 document: {path}")
    return payload


def _resolve_artifact_path(raw: str, artifact_root: Optional[Path]) -> Optional[Path]:
    # The artifact root candidate comes first so a same-named file in the
    # current working directory can never shadow the run's own artifacts.
    candidates = []
    if artifact_root is not None:
        candidates.append(artifact_root / raw)
    candidates.append(Path(raw))
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _artifact_entry(
    entry: Dict[str, Any], artifact_root: Optional[Path]
) -> Dict[str, Any]:
    raw = str(entry.get("path") or "")
    resolved = _resolve_artifact_path(raw, artifact_root)
    prepared = {
        "artifact_type": entry.get("artifact_type"),
        "path": raw,
        "metadata": entry.get("metadata") or {},
        "embedded": False,
        "data_uri": None,
        "state": "missing",
        "size_bytes": None,
    }
    if resolved is None:
        return prepared
    prepared["size_bytes"] = resolved.stat().st_size
    within_root = True
    if artifact_root is not None:
        try:
            within_root = artifact_root.resolve() in resolved.parents or (
                resolved == artifact_root.resolve()
            )
        except OSError:
            within_root = False
    suffix = resolved.suffix.lower()
    if not within_root:
        prepared["state"] = "external"
        return prepared
    if suffix not in _EMBEDABLE_SUFFIXES:
        prepared["state"] = "linked"
        return prepared
    if prepared["size_bytes"] > MAX_EMBED_BYTES:
        prepared["state"] = "oversize"
        return prepared
    try:
        encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    except OSError:
        return prepared
    mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else f"image/{suffix.lstrip('.')}"
    prepared["embedded"] = True
    prepared["state"] = "embedded"
    prepared["data_uri"] = f"data:{mime};base64,{encoded}"
    return prepared


def prepare_report(
    report: Dict[str, Any], *, artifact_root: Optional[Path] = None
) -> Dict[str, Any]:
    context = report.get("context") or {}
    failure = report.get("failure") or None
    artifacts_by_path: Dict[str, Dict[str, Any]] = {}
    prepared_artifacts = []
    for entry in report.get("artifacts") or []:
        if not isinstance(entry, dict):
            continue
        prepared = _artifact_entry(entry, artifact_root)
        prepared_artifacts.append(prepared)
        if prepared["path"]:
            artifacts_by_path[prepared["path"]] = prepared

    steps: List[Dict[str, Any]] = []
    for step in report.get("steps") or []:
        if not isinstance(step, dict):
            continue
        artifact_result = step.get("artifact_result") or None
        step_artifacts = []
        if isinstance(artifact_result, dict):
            path = str(artifact_result.get("path") or "")
            step_artifacts.append(
                artifacts_by_path.get(path)
                or _artifact_entry(
                    {
                        "artifact_type": artifact_result.get("artifact_type"),
                        "path": path,
                    },
                    artifact_root,
                )
            )
        error = step.get("error") or None
        steps.append(
            {
                "step_id": step.get("step_id"),
                "step_name": step.get("step_name"),
                "kind": step.get("kind"),
                "status": step.get("status"),
                "attempts": step.get("attempts"),
                "duration_ms": step.get("duration_ms"),
                "error_code": (error or {}).get("code") if isinstance(error, dict) else None,
                "error_message": (error or {}).get("message") if isinstance(error, dict) else None,
                "artifacts": step_artifacts,
            }
        )

    return {
        "schema_version": report.get("schema_version"),
        "run_id": context.get("run_id"),
        "workflow_name": context.get("workflow_name"),
        "correlation_id": context.get("correlation_id"),
        "status": report.get("status"),
        "success": report.get("success"),
        "failure": failure if isinstance(failure, dict) else None,
        "steps": steps,
        "artifacts": prepared_artifacts,
        "events": report.get("events") or [],
        "providers": report.get("providers") or [],
    }


def render_report_html(
    report: Dict[str, Any], *, artifact_root: Optional[Path] = None
) -> str:
    try:
        template = resources.read_text(
            "automation_runner", TEMPLATE_RESOURCE, encoding="utf-8"
        )
    except (FileNotFoundError, OSError) as exc:
        raise ViewerError("viewer template resource is missing") from exc
    data = prepare_report(report, artifact_root=artifact_root)
    # ``</`` is escaped so a payload cannot close the surrounding script tag.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    if _DATA_PLACEHOLDER not in template:
        raise ViewerError("viewer template is missing the data placeholder")
    return template.replace(_DATA_PLACEHOLDER, payload)


def default_output_path(report_path: str) -> Path:
    path = Path(report_path)
    return path.with_name(path.stem + ".viewer.html")
