from typing import Any, Dict, Optional

from automation_core.drivers import ActionResult


class PhonePlaywrightElement:
    """ElementHandle wrapper around a phone-playwright locator.

    The wrapped locator is a borrowed page-scoped object; the wrapper never
    closes or reconnects it.
    """

    def __init__(self, identifier: str, locator: Any) -> None:
        self.identifier = identifier
        self._locator = locator

    def click(self) -> ActionResult:
        try:
            res = self._locator.click()
            if hasattr(res, "success"):
                err = getattr(res, "error", None)
                verb = getattr(res, "verb", "")
                if not res.success and err:
                    msg = f"{verb or 'element click'} failed: {err}"
                else:
                    msg = verb or "element click"
                return ActionResult(
                    success=bool(res.success),
                    message=msg,
                    data=getattr(res, "executed_at_bounds", None) or getattr(res, "data", None),
                )
            return ActionResult(success=True, message="element click")
        except Exception as exc:
            return ActionResult(False, f"element click failed: {exc}")

    def input_text(self, text: str) -> ActionResult:
        try:
            val_text = str(text) if not isinstance(text, str) else text
            if callable(getattr(self._locator, "fill", None)):
                res = self._locator.fill(val_text)
            elif callable(getattr(self._locator, "type_text", None)):
                res = self._locator.type_text(val_text)
            elif callable(getattr(self._locator, "send_keys", None)):
                res = self._locator.send_keys(val_text)
            else:
                return ActionResult(False, "locator does not support text input")

            if hasattr(res, "success"):
                err = getattr(res, "error", None)
                verb = getattr(res, "verb", "")
                if not res.success and err:
                    msg = f"{verb or 'element input'} failed: {err}"
                else:
                    msg = verb or "element input"
                return ActionResult(
                    success=bool(res.success),
                    message=msg,
                    data=getattr(res, "data", None),
                )
            return ActionResult(success=True, message="element input")
        except Exception as exc:
            return ActionResult(False, f"element input failed: {exc}")

    def text(self) -> str:
        try:
            if callable(getattr(self._locator, "text_content", None)):
                val = self._locator.text_content()
            elif callable(getattr(self._locator, "text", None)):
                val = self._locator.text()
            elif callable(getattr(self._locator, "get_text", None)):
                val = self._locator.get_text()
            else:
                val = getattr(self._locator, "text_value", None)
            return str(val) if val is not None else ""
        except Exception:
            return ""

    @property
    def bounds(self) -> Optional[Dict[str, int]]:
        """Element bounds as {x, y, width, height}, or None when unavailable."""
        if callable(getattr(self._locator, "bounding_box", None)):
            try:
                res = self._locator.bounding_box()
                if isinstance(res, dict) and "x" in res and "y" in res and "width" in res and "height" in res:
                    return {
                        "x": int(res["x"]),
                        "y": int(res["y"]),
                        "width": int(res["width"]),
                        "height": int(res["height"]),
                    }
            except Exception:
                pass

        b = getattr(self._locator, "bounds", None)
        if b is None:
            info = getattr(self._locator, "info", None)
            if isinstance(info, dict):
                b = info.get("bounds")

        if b is None:
            return None

        if isinstance(b, dict):
            if "left" in b and "top" in b and "right" in b and "bottom" in b:
                try:
                    left = int(b["left"])
                    top = int(b["top"])
                    return {
                        "x": left,
                        "y": top,
                        "width": int(b["right"]) - left,
                        "height": int(b["bottom"]) - top,
                    }
                except (KeyError, TypeError, ValueError):
                    return None
            if "x" in b and "y" in b and "width" in b and "height" in b:
                try:
                    return {
                        "x": int(b["x"]),
                        "y": int(b["y"]),
                        "width": int(b["width"]),
                        "height": int(b["height"]),
                    }
                except (KeyError, TypeError, ValueError):
                    return None

        if hasattr(b, "left") and hasattr(b, "top") and hasattr(b, "right") and hasattr(b, "bottom"):
            try:
                left = int(b.left)
                top = int(b.top)
                return {
                    "x": left,
                    "y": top,
                    "width": int(b.right) - left,
                    "height": int(b.bottom) - top,
                }
            except (TypeError, ValueError):
                return None

        return None
