import pytest

from adapters.phone_playwright.snapshot import snapshot_to_screen_snapshot
from automation_core.observations import ScreenSnapshot
from tests.adapters.phone_playwright._fakes import (
    FakeCompactElement,
    FakePhoneSnapshot,
)


def test_maps_page_snapshot_to_core_model():
    snap = FakePhoneSnapshot(
        elements=[
            FakeCompactElement(
                ref="@2",
                role="input",
                text="账号",
                left=40,
                top=300,
                right=1040,
                bottom=400,
                resource_id="com.example:id/account",
            ),
            FakeCompactElement(role="text", text="欢迎", left=0, top=0, right=10, bottom=10),
        ]
    )

    result = snapshot_to_screen_snapshot(snap)

    assert isinstance(result, ScreenSnapshot)
    assert result.viewport_width == 1080
    assert result.viewport_height == 2400
    assert result.package_name == "com.example.app"
    assert result.activity_name == ".LoginActivity"
    assert result.device_id == "dut-1"
    assert result.captured_at == 1000.0
    first = result.element(2)
    assert first is not None
    assert first.role == "input"
    assert first.text == "账号"
    assert first.bounds.to_dict() == {"x": 40, "y": 300, "width": 1000, "height": 100}
    assert first.resource_id == "com.example:id/account"
    assert first.clickable is True
    assert first.editable is False
    info = result.elements[1]
    assert info.ref is None
    assert info.clickable is False


def test_maps_empty_elements_tuple():
    result = snapshot_to_screen_snapshot(FakePhoneSnapshot(elements=[]))

    assert result.elements == ()
    assert result.to_markdown().endswith("## Interactive Elements:")


def test_rejects_object_without_snapshot_contract():
    class NotASnapshot:
        pass

    with pytest.raises(ValueError):
        snapshot_to_screen_snapshot(NotASnapshot())


def test_tolerates_missing_optional_metadata():
    snap = FakePhoneSnapshot()
    snap.package_name = None
    snap.activity_name = None
    snap.timestamp = None

    result = snapshot_to_screen_snapshot(snap)

    assert result.package_name is None
    assert result.activity_name is None
    assert result.captured_at is None


def test_dict_round_trip_via_core_model():
    result = snapshot_to_screen_snapshot(FakePhoneSnapshot())

    assert ScreenSnapshot.from_dict(result.to_dict()) == result
