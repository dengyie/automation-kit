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


class FakeCompactElement:
    """Mirrors phone_playwright.models.schema.CompactElement."""

    def __init__(
        self,
        ref: Optional[str] = None,
        role: str = "button",
        text: str = "",
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
        enabled: bool = True,
        scrollable: bool = False,
        resource_id: Optional[str] = None,
    ) -> None:
        self.ref = ref
        self.role = role
        self.text = text
        self.enabled = enabled
        self.scrollable = scrollable
        self.resource_id = resource_id
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def bounds(self) -> "FakeCompactElement":
        return self


class FakePhoneSnapshot:
    """Mirrors phone_playwright.models.schema.PageSnapshot."""

    def __init__(
        self,
        elements: Optional[List[FakeCompactElement]] = None,
        viewport_width: int = 1080,
        viewport_height: int = 2400,
        package_name: Optional[str] = "com.example.app",
        activity_name: Optional[str] = ".LoginActivity",
        device_id: str = "dut-1",
        timestamp: float = 1000.0,
    ) -> None:
        self.elements = (
            elements
            if elements is not None
            else [
                FakeCompactElement(
                    ref="@1",
                    role="button",
                    text="Login",
                    left=440,
                    top=100,
                    right=640,
                    bottom=160,
                )
            ]
        )
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.package_name = package_name
        self.activity_name = activity_name
        self.device_id = device_id
        self.timestamp = timestamp

    def to_markdown(self) -> str:
        lines = [
            f"# Device Viewport: {self.viewport_width}x{self.viewport_height}",
            "## Interactive Elements:",
        ]
        for el in self.elements:
            ref = f"- [{el.ref}]" if el.ref else "- (info)"
            lines.append(f'{ref} {el.role}: "{el.text}"')
        return "\n".join(lines)

    @property
    def summary_markdown(self) -> str:
        return self.to_markdown()


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
