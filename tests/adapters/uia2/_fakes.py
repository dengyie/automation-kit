"""Duck-typed uiautomator2 test doubles (mirrors the real client API surface)."""


class FakeUiObject:
    def __init__(self, identifier, text=None):
        self.identifier = identifier
        self.text_value = text
        self.clicked = 0
        self.sent = []
        self.cleared = 0

    def click(self):
        self.clicked += 1

    def clear_text(self):
        self.cleared += 1

    def send_keys(self, text, clear=False):
        self.sent.append((text, clear))

    def get_text(self):
        if self.text_value is None:
            raise RuntimeError("no text on this element")
        return self.text_value


class FakeDevice:
    """Records interactions; resolves selector kwargs to FakeUiObject.

    Close hooks (``disconnect``/``quit``) deliberately do NOT exist on the
    base class; use the ``*Device`` subclasses below when a test needs them.
    """

    def __init__(
        self,
        *,
        elements=None,
        missing=(),
        screenshot_result=None,
        hierarchy_result=None,
    ):
        self.elements = elements or {}
        self.missing = set(missing)
        self.screenshot_result = screenshot_result
        self.hierarchy_result = hierarchy_result
        self.calls = []
        self.disconnect_count = 0
        self.quit_count = 0

    def _resolve(self, key, factory=None):
        if key in self.missing:
            raise KeyError("element not found")
        if key not in self.elements:
            self.elements[key] = (
                factory() if factory is not None else FakeUiObject(f"{key[0]}={key[1]}")
            )
        return self.elements[key]

    def __call__(self, **kwargs):
        self.calls.append(("selector", dict(kwargs)))
        kind, value = next(iter(kwargs.items()))
        return self._resolve((kind, value))

    def xpath(self, selector):
        self.calls.append(("xpath", selector))
        return self._resolve(("xpath", selector))

    def app_start(self, package):
        self.calls.append(("app_start", package))

    def app_stop(self, package):
        self.calls.append(("app_stop", package))

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def swipe(self, sx, sy, ex, ey, duration=0.0):
        self.calls.append(("swipe", sx, sy, ex, ey, duration))

    def screenshot(self):
        if callable(self.screenshot_result):
            return self.screenshot_result()
        return self.screenshot_result

    def dump_hierarchy(self):
        if callable(self.hierarchy_result):
            return self.hierarchy_result()
        return self.hierarchy_result


class DisconnectableDevice(FakeDevice):
    def disconnect(self):
        self.disconnect_count += 1


class QuitOnlyDevice(FakeDevice):
    def quit(self):
        self.quit_count += 1


class FullyClosableDevice(FakeDevice):
    def disconnect(self):
        self.disconnect_count += 1

    def quit(self):
        self.quit_count += 1


class FlakyDevice(FakeDevice):
    """Raises on the first ``fail_times`` selector lookups, then resolves."""

    def __init__(self, fail_times, **kwargs):
        super().__init__(**kwargs)
        self.fail_times = fail_times
        self.lookup_count = 0

    def __call__(self, **kwargs):
        self.lookup_count += 1
        if self.lookup_count <= self.fail_times:
            raise KeyError("not yet")
        return super().__call__(**kwargs)


class FakePilImage:
    """PIL-like screenshot result; ``save`` only writes when ``persist``."""

    def __init__(self, persist=True):
        self.persist = persist
        self.saved_to = None

    def save(self, path):
        if not self.persist:
            return
        self.saved_to = path
        with open(path, "wb") as handle:
            handle.write(b"png-bytes")
