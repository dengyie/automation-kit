"""Viewport-aware semantic distillation for uiautomator2 hierarchy dumps.

Mirrors the ``phone-playwright`` pruner contract on the uia2 path: single
O(N) DFS over the accessibility XML, geometric viewport clipping,
semantic label hoisting from descendants, ``@ref`` index assignment for
interactable elements and static info elements for pure display nodes.
Only ``xml.etree`` and ``automation_core.observations`` are used; the
``uiautomator2`` package itself is never imported (boundary-tested).
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

from automation_core.observations import (
    ScreenBounds,
    ScreenElement,
    ScreenSnapshot,
)

DEFAULT_MIN_ELEMENT_SIZE = 8

_LABEL_DEPTH_LIMIT = 5

_BOUNDS_PATTERN = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


class HierarchyDistillError(ValueError):
    """The hierarchy dump could not be parsed or distilled."""


class _Node:
    __slots__ = (
        "text",
        "desc",
        "resource_id",
        "class_name",
        "clickable",
        "checkable",
        "scrollable",
        "enabled",
        "editable",
        "bounds",
        "children",
    )

    def __init__(self) -> None:
        self.text = ""
        self.desc = ""
        self.resource_id = ""
        self.class_name = ""
        self.clickable = False
        self.checkable = False
        self.scrollable = False
        self.enabled = True
        self.editable = False
        self.bounds = ScreenBounds(x=0, y=0, width=0, height=0)
        self.children: List["_Node"] = []


def parse_hierarchy(xml_text: str) -> Tuple[_Node, ScreenBounds]:
    """Parse a uiautomator XML dump into the node tree and viewport bounds."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise HierarchyDistillError(f"hierarchy dump is not valid XML: {exc}") from exc

    node = root if root.tag == "node" else None
    if node is None:
        for child in root.iter("node"):
            node = child
            break
    if node is None:
        raise HierarchyDistillError("hierarchy dump contains no node entries")

    parsed = _parse_node(node)
    if parsed is None:
        raise HierarchyDistillError("hierarchy root node has no usable bounds")
    return parsed, parsed.bounds


def distill_snapshot(
    xml_text: str,
    *,
    package_name: Optional[str] = None,
    activity_name: Optional[str] = None,
    device_id: Optional[str] = None,
    captured_at: Optional[float] = None,
    min_element_size: int = DEFAULT_MIN_ELEMENT_SIZE,
) -> ScreenSnapshot:
    """Distill a raw hierarchy dump into a viewport-aware screen snapshot."""
    root, viewport = parse_hierarchy(xml_text)
    if min_element_size < 1:
        raise HierarchyDistillError("min_element_size must be >= 1")

    elements: List[ScreenElement] = []
    next_ref = 1

    def traverse(node: _Node) -> None:
        nonlocal next_ref
        intersection = _intersection(node.bounds, viewport)
        if (
            intersection is None
            or intersection.width < min_element_size
            or intersection.height < min_element_size
        ):
            return

        is_interactive = (
            node.clickable
            or node.editable
            or node.checkable
            or (node.scrollable and not node.children)
        )
        if is_interactive:
            label = " ".join(_collect_descendant_texts(node))
            ref = next_ref
            next_ref += 1
            elements.append(
                ScreenElement(
                    role=infer_semantic_role(node),
                    text=label,
                    bounds=node.bounds,
                    ref=ref,
                    resource_id=node.resource_id or None,
                    clickable=node.clickable,
                    editable=node.editable,
                    scrollable=node.scrollable,
                    enabled=node.enabled,
                )
            )
            if not _has_interactive_descendants(node):
                return
        elif (node.text or node.desc) and not node.children:
            elements.append(
                ScreenElement(
                    role=infer_semantic_role(node),
                    text=(node.text or node.desc or "").strip(),
                    bounds=node.bounds,
                    resource_id=node.resource_id or None,
                    enabled=node.enabled,
                )
            )
            return

        for child in node.children:
            traverse(child)

    traverse(root)
    return ScreenSnapshot(
        viewport_width=viewport.width,
        viewport_height=viewport.height,
        elements=tuple(elements),
        package_name=package_name,
        activity_name=activity_name,
        device_id=device_id,
        captured_at=captured_at,
    )


def infer_semantic_role(node: _Node) -> str:
    """Heuristic role inference from the native class name and attributes."""
    class_lower = node.class_name.lower()
    if node.editable or "edittext" in class_lower or "textfield" in class_lower:
        return "input"
    if "button" in class_lower:
        return "button"
    if "checkbox" in class_lower:
        return "checkbox"
    if "switch" in class_lower or "toggle" in class_lower:
        return "switch"
    if "tab" in class_lower:
        return "tab"
    if (
        node.scrollable
        or "scrollview" in class_lower
        or "recyclerview" in class_lower
        or "listview" in class_lower
    ):
        return "scrollable"
    if node.clickable:
        if not node.text and not node.desc:
            return "item"
        return "button"
    if "imageview" in class_lower or "image" in class_lower:
        return "image"
    if node.text or node.desc:
        return "text"
    return "unknown"


def _parse_node(element: ET.Element) -> Optional[_Node]:
    node = _Node()
    node.text = element.get("text", "") or ""
    node.desc = element.get("content-desc", "") or ""
    node.resource_id = element.get("resource-id", "") or ""
    node.class_name = element.get("class", "") or ""
    node.clickable = element.get("clickable", "false") == "true"
    node.checkable = element.get("checkable", "false") == "true"
    node.scrollable = element.get("scrollable", "false") == "true"
    node.enabled = element.get("enabled", "true") != "false"
    node.editable = "edittext" in node.class_name.lower() or "textfield" in node.class_name.lower()
    bounds = _parse_bounds(element.get("bounds", ""))
    if bounds is None:
        return None
    node.bounds = bounds
    for child in element.findall("node"):
        parsed_child = _parse_node(child)
        if parsed_child is not None:
            node.children.append(parsed_child)
    return node


def _parse_bounds(raw: str) -> Optional[ScreenBounds]:
    match = _BOUNDS_PATTERN.fullmatch(raw.strip())
    if match is None:
        return None
    left, top, right, bottom = (int(group) for group in match.groups())
    return ScreenBounds(
        x=left,
        y=top,
        width=max(0, right - left),
        height=max(0, bottom - top),
    )


def _intersection(a: ScreenBounds, b: ScreenBounds) -> Optional[ScreenBounds]:
    left = max(a.x, b.x)
    top = max(a.y, b.y)
    right = min(a.x + a.width, b.x + b.width)
    bottom = min(a.y + a.height, b.y + b.height)
    if right <= left or bottom <= top:
        return None
    return ScreenBounds(x=left, y=top, width=right - left, height=bottom - top)


def _collect_descendant_texts(node: _Node) -> List[str]:
    """Own plus descendant non-blank texts, deduped in first-seen order."""
    texts: List[str] = []

    def dfs(current: _Node, depth: int) -> None:
        if depth > _LABEL_DEPTH_LIMIT:
            return
        for value in (current.text, current.desc):
            stripped = (value or "").strip()
            if stripped and stripped not in texts:
                texts.append(stripped)
        for child in current.children:
            dfs(child, depth + 1)

    dfs(node, 0)
    return texts


def _has_interactive_descendants(node: _Node) -> bool:
    for child in node.children:
        if child.clickable or child.editable or child.checkable:
            return True
        if _has_interactive_descendants(child):
            return True
    return False
