"""Duck-typed phone-playwright test doubles."""

from typing import Any, Dict, List, Optional, Sequence


class FakeActionResult:
    def __init__(
        self,
        success: bool = True,
        verb: str = "click",
        executed_at_bounds: Any = None,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.verb = verb
        self.executed_at_bounds = executed_at_bounds
        self.error = error


class FakePhoneLocator:
    def __init__(
        self,
        selector: str,
        text: Optional[str] = None,
        bounds: Optional[Dict[str, int]] = None,
        should_fail_click: bool = False,
        should_fail_fill: bool = False,
        visible: Any = True,
    ) -> None:
        self.selector = selector
        self.text_value = text
        self.bounds = bounds
        self.clicked = 0
        self.filled: List[str] = []
        self.scroll_calls: List[Dict[str, Any]] = []
        self.should_fail_click = should_fail_click
        self.should_fail_fill = should_fail_fill
        self.visible = visible

    def click(self, timeout_s: float = 5.0) -> FakeActionResult:
        if self.should_fail_click:
            raise RuntimeError("element click failed intentionally")
        self.clicked += 1
        return FakeActionResult(success=True, verb="click", executed_at_bounds=self.bounds)

    def fill(self, text: str, timeout_s: float = 5.0) -> FakeActionResult:
        if self.should_fail_fill:
            raise RuntimeError("element fill failed intentionally")
        self.filled.append(text)
        return FakeActionResult(success=True, verb="fill")

    def scroll_into_view(
        self, max_swipes: int = 5, direction: str = "up", distance_ratio: float = 0.5
    ) -> "FakePhoneLocator":
        self.scroll_calls.append({
            "max_swipes": max_swipes,
            "direction": direction,
            "distance_ratio": distance_ratio,
        })
        return self

    def text_content(self) -> Optional[str]:
        return self.text_value

    def is_visible(self) -> bool:
        if callable(self.visible):
            return bool(self.visible())
        return bool(self.visible)


class FakePhoneSnapshot:
    def __init__(self, content: str = "# Viewport: 1080x2400\n- [@1] button: \"Login\"") -> None:
        self.content = content

    def to_markdown(self) -> str:
        return self.content

    @property
    def summary_markdown(self) -> str:
        return self.content


class BaseFakePhonePage:
    """Base test double without teardown hooks (close/disconnect/quit)."""

    def __init__(
        self,
        *,
        locators: Optional[Dict[str, FakePhoneLocator]] = None,
        missing: Sequence[str] = (),
        screenshot_result: Any = b"\x89PNG\r\n\x1a\nfake",
        hierarchy_result: Any = "<hierarchy></hierarchy>",
        snapshot_result: Any = None,
    ) -> None:
        self.locators = locators or {}
        self.missing = set(missing)
        self.screenshot_result = screenshot_result
        self.hierarchy_result = hierarchy_result
        self.snapshot_result = snapshot_result or FakePhoneSnapshot()
        self.calls: List[Any] = []
        self.platform = "android"

    def locator(self, selector: str) -> FakePhoneLocator:
        self.calls.append(("locator", selector))
        if selector in self.missing:
            raise KeyError(f"locator not found: {selector}")
        if selector not in self.locators:
            self.locators[selector] = FakePhoneLocator(selector)
        return self.locators[selector]

    def app_start(self, package: str) -> None:
        self.calls.append(("app_start", package))

    def app_stop(self, package: str) -> None:
        self.calls.append(("app_stop", package))

    def click(self, x: float, y: float) -> None:
        self.calls.append(("click", x, y))

    def swipe(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("swipe", args, kwargs))

    def snapshot(self, **kwargs: Any) -> Any:
        self.calls.append(("snapshot", kwargs))
        if callable(self.snapshot_result):
            return self.snapshot_result()
        return self.snapshot_result

    def take_screenshot(self) -> Any:
        self.calls.append(("take_screenshot",))
        if callable(self.screenshot_result):
            return self.screenshot_result()
        return self.screenshot_result

    def dump_raw_tree(self) -> Any:
        self.calls.append(("dump_raw_tree",))
        if callable(self.hierarchy_result):
            return self.hierarchy_result()
        return self.hierarchy_result

    def press_back(self) -> None:
        self.calls.append(("press_back",))

    def press_home(self) -> None:
        self.calls.append(("press_home",))


class FakePhonePage(BaseFakePhonePage):
    """Default test double with close() hook."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class DisconnectablePage(BaseFakePhonePage):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.disconnect_count = 0

    def disconnect(self) -> None:
        self.disconnect_count += 1


class QuitOnlyPage(BaseFakePhonePage):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.quit_count = 0

    def quit(self) -> None:
        self.quit_count += 1


class NoClosePage(BaseFakePhonePage):
    pass
