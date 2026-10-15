"""Platform-neutral screen observation models for AI-native automation.

Frozen value objects describing a distilled, viewport-aware semantic
snapshot of a screen. Adapters map their native hierarchies (Android
accessibility trees, iOS, web) onto these models; AI consumers program
against stable integer refs (rendered as ``@1``, ``@2``, ...) and the
compact markdown serialization. Only Python standard library types are
used; serialization is deterministic and safe by construction.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class ScreenBounds:
    """Absolute pixel rectangle as x/y plus extent."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: Any) -> "ScreenBounds":
        if not isinstance(data, dict):
            raise ValueError("bounds must be an object")
        try:
            return cls(
                x=int(data["x"]),
                y=int(data["y"]),
                width=int(data["width"]),
                height=int(data["height"]),
            )
        except KeyError as exc:
            raise ValueError(f"bounds is missing field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError("bounds fields must be numbers") from exc


@dataclass(frozen=True)
class ScreenElement:
    """One distilled screen element.

    ``ref`` is a 1-based stable identifier assigned in document order for
    interactable elements; static informational elements carry ``None``.
    """

    role: str
    text: str
    bounds: ScreenBounds
    ref: Optional[int] = None
    resource_id: Optional[str] = None
    clickable: bool = False
    editable: bool = False
    scrollable: bool = False
    enabled: bool = True

    @property
    def center(self) -> Tuple[int, int]:
        return self.bounds.center

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "role": self.role,
            "text": self.text,
            "bounds": self.bounds.to_dict(),
        }
        if self.ref is not None:
            data["ref"] = self.ref
        if self.resource_id is not None:
            data["resource_id"] = self.resource_id
        if self.clickable:
            data["clickable"] = True
        if self.editable:
            data["editable"] = True
        if self.scrollable:
            data["scrollable"] = True
        if not self.enabled:
            data["enabled"] = False
        return data

    @classmethod
    def from_dict(cls, data: Any) -> "ScreenElement":
        if not isinstance(data, dict):
            raise ValueError("element must be an object")
        role = data.get("role")
        text = data.get("text", "")
        if not isinstance(role, str) or not role:
            raise ValueError("element role must be a non-empty string")
        if not isinstance(text, str):
            raise ValueError("element text must be a string")
        ref = _normalize_ref(data.get("ref"))
        resource_id = data.get("resource_id")
        if resource_id is not None and not isinstance(resource_id, str):
            raise ValueError("element resource_id must be a string")
        flags = _normalize_flags(data, ("clickable", "editable", "scrollable"))
        enabled = data.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("element enabled must be a boolean")
        return cls(
            role=role,
            text=text,
            bounds=ScreenBounds.from_dict(data.get("bounds")),
            ref=ref,
            resource_id=resource_id,
            clickable=flags["clickable"],
            editable=flags["editable"],
            scrollable=flags["scrollable"],
            enabled=enabled,
        )


@dataclass(frozen=True)
class ScreenSnapshot:
    """Distilled semantic snapshot of the active screen viewport."""

    viewport_width: int
    viewport_height: int
    elements: Tuple[ScreenElement, ...] = ()
    package_name: Optional[str] = None
    activity_name: Optional[str] = None
    device_id: Optional[str] = None
    captured_at: Optional[float] = None

    def element(self, ref: int) -> Optional[ScreenElement]:
        """Return the element carrying ``ref``, or None."""
        if isinstance(ref, bool) or not isinstance(ref, int) or ref < 1:
            return None
        for element in self.elements:
            if element.ref == ref:
                return element
        return None

    def interactable(self) -> Tuple[ScreenElement, ...]:
        return tuple(element for element in self.elements if element.ref is not None)

    def to_markdown(self) -> str:
        """Compact LLM-facing element list; format mirrors the @ref contract."""
        lines = [f"# Device Viewport: {self.viewport_width}x{self.viewport_height}"]
        if self.package_name:
            lines.append(f"# Active App: {self.package_name}")
        if self.activity_name:
            lines.append(f"# Activity: {self.activity_name}")
        lines.append("## Interactive Elements:")
        for element in self.elements:
            clean_text = element.text.replace("\n", " ").strip()
            if element.ref is not None:
                lines.append(f'- [@{element.ref}] {element.role}: "{clean_text}"')
            else:
                lines.append(f'- (info) {element.role}: "{clean_text}"')
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "elements": [element.to_dict() for element in self.elements],
        }
        if self.package_name is not None:
            data["package_name"] = self.package_name
        if self.activity_name is not None:
            data["activity_name"] = self.activity_name
        if self.device_id is not None:
            data["device_id"] = self.device_id
        if self.captured_at is not None:
            data["captured_at"] = self.captured_at
        return data

    @classmethod
    def from_dict(cls, data: Any) -> "ScreenSnapshot":
        if not isinstance(data, dict):
            raise ValueError("snapshot must be an object")
        try:
            viewport_width = int(data["viewport_width"])
            viewport_height = int(data["viewport_height"])
        except KeyError as exc:
            raise ValueError(f"snapshot is missing field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError("snapshot viewport fields must be numbers") from exc
        raw_elements = data.get("elements", ())
        if not isinstance(raw_elements, (list, tuple)):
            raise ValueError("snapshot elements must be a list")
        package_name = data.get("package_name")
        activity_name = data.get("activity_name")
        device_id = data.get("device_id")
        captured_at = data.get("captured_at")
        for name, value in (
            ("package_name", package_name),
            ("activity_name", activity_name),
            ("device_id", device_id),
        ):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"snapshot {name} must be a string")
        if captured_at is not None:
            if isinstance(captured_at, bool) or not isinstance(captured_at, (int, float)):
                raise ValueError("snapshot captured_at must be a number")
        return cls(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            elements=tuple(ScreenElement.from_dict(item) for item in raw_elements),
            package_name=package_name,
            activity_name=activity_name,
            device_id=device_id,
            captured_at=None if captured_at is None else float(captured_at),
        )


def _normalize_ref(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("@") and value[1:].isdigit():
        value = int(value[1:])
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("element ref must be a positive integer or '@N' string")
    return value


def _normalize_flags(data: Dict[str, Any], names: Tuple[str, ...]) -> Dict[str, bool]:
    flags: Dict[str, bool] = {}
    for name in names:
        value = data.get(name, False)
        if not isinstance(value, bool):
            raise ValueError(f"element {name} must be a boolean")
        flags[name] = value
    return flags
