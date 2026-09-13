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
