from typing import Any, Callable, Optional

from automation_core.drivers import ActionResult


class Uia2Element:
    """ElementHandle wrapper around a uiautomator2 UiObject or XPath lookup.

    The wrapped lookup is a borrowed driver-scoped object; the wrapper never
    closes or reconnects it.
    """

    def __init__(self, identifier: str, lookup: Any):
        self.identifier = identifier
        self._lookup = lookup

    def click(self) -> ActionResult:
        try:
            self._lookup.click()
        except Exception as exc:
            return ActionResult(False, f"element click failed: {exc}")
        return ActionResult(success=True, message="element click")

    def input_text(self, text: str) -> ActionResult:
        try:
            self.type_text(text, clear=True)
        except Exception as exc:
            return ActionResult(False, f"element input failed: {exc}")
        return ActionResult(success=True, message="element input")

    def type_text(self, text: str, clear: bool = True) -> Any:
        """Focus, optionally clear, then type; mirrors user interaction."""
        self._lookup.click()
        if clear and callable(getattr(self._lookup, "clear_text", None)):
            self._lookup.clear_text()
        return self._lookup.send_keys(text)

    def text(self) -> str:
        try:
            value = self._lookup.get_text()
        except Exception:
            return ""
        return value if isinstance(value, str) else ""

    @property
    def bounds(self):
        """Element bounds as {x, y, width, height}, or None when unavailable.

        Reads the lookup's snapshot info; uiautomator2 exposes bounds as
        left/top/right/bottom screen pixels.
        """
        info = getattr(self._lookup, "info", None)
        if not isinstance(info, dict):
            return None
        bounds = info.get("bounds") or {}
        try:
            left = int(bounds["left"])
            top = int(bounds["top"])
            return {
                "x": left,
                "y": top,
                "width": int(bounds["right"]) - left,
                "height": int(bounds["bottom"]) - top,
            }
        except (KeyError, TypeError, ValueError):
            return None


class RefElement:
    """ElementHandle bound to a snapshot ref (@N) instead of a live lookup.

    Interaction dispatches at the cached snapshot bounds (warm-cache fast
    dispatch): ``click`` taps the element centre through the injected
    coordinate dispatcher, ``input_text`` focuses first and then sends text
    through the injected text channel. The wrapped snapshot element is a
    borrowed, read-only observation; the wrapper closes nothing.
    """

    def __init__(
        self,
        snapshot_element: Any,
        dispatch_click: Callable[[int, int], Any],
        send_text: Optional[Callable[[str], Any]] = None,
        clear_text: Optional[Callable[[], Any]] = None,
    ):
        self.snapshot_element = snapshot_element
        self.identifier = f"@{snapshot_element.ref}"
        self._dispatch_click = dispatch_click
        self._send_text = send_text
        self._clear_text = clear_text

    def click(self) -> ActionResult:
        element = self.snapshot_element
        if not element.enabled:
            return ActionResult(False, f"ref @{element.ref} is disabled")
        if not (element.clickable or element.editable or element.scrollable):
            return ActionResult(False, f"ref @{element.ref} is not interactable")
        x, y = element.center
        try:
            self._dispatch_click(x, y)
        except Exception as exc:
            return ActionResult(False, f"ref element click failed: {exc}")
        return ActionResult(success=True, message="ref element click")

    def input_text(self, text: str, clear: bool = True) -> ActionResult:
        element = self.snapshot_element
        if not element.editable:
            return ActionResult(
                False,
                f"ref @{element.ref} is not an editable input",
            )
        focused = self.click()
        if not focused.success:
            return focused
        if not callable(self._send_text):
            return ActionResult(False, "driver does not support ref text input")
        try:
            if clear and callable(self._clear_text):
                self._clear_text()
            self._send_text(text)
        except Exception as exc:
            return ActionResult(False, f"ref element input failed: {exc}")
        return ActionResult(success=True, message="ref element input")

    def text(self) -> str:
        return self.snapshot_element.text

    @property
    def bounds(self):
        return self.snapshot_element.bounds.to_dict()
