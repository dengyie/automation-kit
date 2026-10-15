"""Mapping from phone-playwright snapshots onto the core observation models.

The phone-playwright SDK returns pydantic ``PageSnapshot`` objects; this
module converts them (duck-typed, no SDK import) into the platform-neutral
``automation_core.observations`` value objects so every Android adapter
speaks the same screen-observation contract.
"""

from typing import Any, Optional

from automation_core.observations import (
    ScreenBounds,
    ScreenElement,
    ScreenSnapshot,
)

# Attributes read off a phone-playwright PageSnapshot / CompactElement.
_SNAPSHOT_FIELDS = (
    "viewport_width",
    "viewport_height",
    "package_name",
    "activity_name",
    "device_id",
    "timestamp",
)


def snapshot_to_screen_snapshot(snap: Any) -> ScreenSnapshot:
    """Convert a phone-playwright PageSnapshot-like object.

    Raises ``ValueError`` when the object does not expose the snapshot
    contract (missing viewport fields) so callers can degrade cleanly.
    """
    for field_name in ("viewport_width", "viewport_height", "elements"):
        if not hasattr(snap, field_name):
            raise ValueError(
                f"snapshot object is missing required field: {field_name}"
            )

    elements = tuple(
        _element_from_compact(compact) for compact in (snap.elements or ())
    )
    return ScreenSnapshot(
        viewport_width=int(snap.viewport_width),
        viewport_height=int(snap.viewport_height),
        elements=elements,
        package_name=_optional_str(getattr(snap, "package_name", None)),
        activity_name=_optional_str(getattr(snap, "activity_name", None)),
        device_id=_optional_str(getattr(snap, "device_id", None)),
        captured_at=_optional_float(getattr(snap, "timestamp", None)),
    )


def _element_from_compact(compact: Any) -> ScreenElement:
    bounds = compact.bounds
    x = int(getattr(bounds, "left", getattr(bounds, "x", 0)))
    y = int(getattr(bounds, "top", getattr(bounds, "y", 0)))
    width = int(
        getattr(bounds, "width", 0)
        or (int(bounds.right) - x if hasattr(bounds, "right") else 0)
    )
    height = int(
        getattr(bounds, "height", 0)
        or (int(bounds.bottom) - y if hasattr(bounds, "bottom") else 0)
    )
    return ScreenElement(
        role=str(getattr(compact, "role", "unknown") or "unknown"),
        text=str(getattr(compact, "text", "") or ""),
        bounds=ScreenBounds(x=x, y=y, width=width, height=height),
        ref=_ref_to_int(getattr(compact, "ref", None)),
        resource_id=_optional_str(getattr(compact, "resource_id", None)),
        clickable=_ref_to_int(getattr(compact, "ref", None)) is not None,
        scrollable=bool(getattr(compact, "scrollable", False)),
        enabled=bool(getattr(compact, "enabled", True)),
    )


def _ref_to_int(ref: Any) -> Optional[int]:
    if ref is None:
        return None
    text = str(ref).strip()
    if text.startswith("@"):
        text = text[1:]
    if not text.isdigit():
        return None
    return int(text)


def _optional_str(value: Any) -> Optional[str]:
    return str(value) if value else None


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
