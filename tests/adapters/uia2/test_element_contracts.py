"""Deep-coverage tests for adapters/uia2/element.py.

Pins the ElementHandle contracts: exists probing (absent attribute,
method-style, attribute-style, raising lookups) and the RefElement
viewport-clipped dispatch point plus every interaction failure branch.
"""

import pytest

from automation_core.drivers import ActionResult
from adapters.uia2.element import RefElement, Uia2Element


class FakeBounds:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class FakeSnapshotElement:
    def __init__(self, ref=1, text="elt", bounds=None, enabled=True, clickable=True, editable=False, scrollable=False):
        self.ref = ref
        self.text = text
        self.bounds = bounds or FakeBounds(0, 0, 100, 100)
        self.enabled = enabled
        self.clickable = clickable
        self.editable = editable
        self.scrollable = scrollable


# --- Uia2Element.exists probing (81, 84-85) -----------------------------------------


def test_exists_defaults_true_without_probe():
    class Bare:
        pass

    assert Uia2Element("x", Bare()).exists is True


def test_exists_method_style_probe():
    class MethodProbe:
        def __init__(self, value):
            self._value = value

        def exists(self):
            return self._value

    assert Uia2Element("x", MethodProbe(True)).exists is True
    assert Uia2Element("x", MethodProbe(False)).exists is False


def test_exists_attribute_style_probe():
    class AttrProbe:
        exists = False

    assert Uia2Element("x", AttrProbe()).exists is False


def test_exists_raising_probe_is_tolerated_as_present():
    class Exploding:
        def exists(self):
            raise RuntimeError("stale")

    assert Uia2Element("x", Exploding()).exists is True


# --- RefElement.dispatch_point clipping (132 region) ---------------------------------


def test_dispatch_point_clips_to_viewport():
    element = FakeSnapshotElement(bounds=FakeBounds(-50, -50, 200, 200))
    ref = RefElement(element, lambda x, y: None, viewport=(1080, 2400))
    # Visible region: (0,0)-(150,150) → centre (75,75)
    assert ref.dispatch_point() == (75, 75)


def test_dispatch_point_full_center_when_nothing_visible():
    element = FakeSnapshotElement(bounds=FakeBounds(2000, 3000, 100, 100))
    ref = RefElement(element, lambda x, y: None, viewport=(1080, 2400))
    # Intersection is empty → falls back to full bounds centre.
    assert ref.dispatch_point() == (2050, 3050)


def test_dispatch_point_full_center_without_viewport():
    element = FakeSnapshotElement(bounds=FakeBounds(10, 20, 100, 40))
    ref = RefElement(element, lambda x, y: None, viewport=None)
    assert ref.dispatch_point() == (60, 40)


# --- RefElement.click branches (139+) --------------------------------------------------


def test_ref_click_disabled_element():
    element = FakeSnapshotElement(enabled=False)
    ref = RefElement(element, lambda x, y: pytest.fail("must not dispatch"))

    result = ref.click()

    assert result.success is False
    assert "ref @1 is disabled" in result.message


def test_ref_click_not_interactable():
    element = FakeSnapshotElement(clickable=False, editable=False, scrollable=False)
    ref = RefElement(element, lambda x, y: pytest.fail("must not dispatch"))

    result = ref.click()

    assert result.success is False
    assert "not interactable" in result.message


def test_ref_click_success_dispatches_at_point():
    dispatched = []
    element = FakeSnapshotElement()
    ref = RefElement(element, lambda x, y: dispatched.append((x, y)))

    result = ref.click()

    assert result.success is True
    assert result.message == "ref element click"
    assert dispatched == [(50, 50)]


def test_ref_click_dispatch_raise_is_failure():
    element = FakeSnapshotElement()

    def exploding(x, y):
        raise RuntimeError("inject error")

    result = RefElement(element, exploding).click()

    assert result.success is False
    assert "ref element click failed: inject error" in result.message


# --- RefElement.input_text branches (156, 158, 163-164) --------------------------------


def test_ref_input_text_not_editable():
    element = FakeSnapshotElement(editable=False)
    ref = RefElement(element, lambda x, y: None)

    result = ref.input_text("hi")

    assert result.success is False
    assert "not an editable input" in result.message


def test_ref_input_text_focus_failure_propagates():
    element = FakeSnapshotElement(editable=True)

    def failing_click(x, y):
        raise RuntimeError("focus lost")

    result = RefElement(
        element, failing_click, send_text=lambda t: None
    ).input_text("hi")

    # click() swallows dispatch raises into its own failure result, which
    # input_text then propagates verbatim.
    assert result.success is False
    assert "ref element click failed: focus lost" in result.message


def test_ref_input_text_without_send_text_capability():
    element = FakeSnapshotElement(editable=True)
    ref = RefElement(element, lambda x, y: ActionResult(success=True, message="click"), send_text=None)

    result = ref.input_text("hi")

    assert result.success is False
    assert "does not support ref text input" in result.message


def test_ref_input_text_success_clears_then_sends():
    calls = []
    element = FakeSnapshotElement(editable=True)
    ref = RefElement(
        element,
        lambda x, y: ActionResult(success=True, message="click"),
        send_text=lambda t: calls.append(("send", t)),
        clear_text=lambda: calls.append(("clear",)),
    )

    result = ref.input_text("hi")

    assert result.success is True
    assert result.message == "ref element input"
    assert calls == [("clear",), ("send", "hi")]


def test_ref_input_text_send_raise_is_failure():
    element = FakeSnapshotElement(editable=True)

    def exploding_send(t):
        raise RuntimeError("ime dead")

    ref = RefElement(
        element,
        lambda x, y: ActionResult(success=True, message="click"),
        send_text=exploding_send,
    )

    result = ref.input_text("hi")

    assert result.success is False
    assert "ref element input failed: ime dead" in result.message


def test_ref_input_text_clear_skipped_when_false():
    calls = []
    element = FakeSnapshotElement(editable=True)
    ref = RefElement(
        element,
        lambda x, y: ActionResult(success=True, message="click"),
        send_text=lambda t: calls.append(("send", t)),
        clear_text=lambda: calls.append(("clear",)),
    )

    result = ref.input_text("hi", clear=False)

    assert result.success is True
    assert calls == [("send", "hi")]


def test_ref_text_and_bounds_delegation():
    element = FakeSnapshotElement(text="标签", bounds=FakeBounds(1, 2, 3, 4))
    ref = RefElement(element, lambda x, y: None)

    assert ref.text() == "标签"
    assert ref.bounds == {"x": 1, "y": 2, "width": 3, "height": 4}
    assert ref.identifier == "@1"
