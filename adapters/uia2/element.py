from typing import Any

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
