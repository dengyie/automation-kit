import dataclasses

import pytest

from automation_core.observations import (
    ScreenBounds,
    ScreenElement,
    ScreenSnapshot,
)


def _element(**overrides):
    defaults = dict(
        role="button",
        text="确定",
        bounds=ScreenBounds(x=100, y=200, width=80, height=40),
        ref=1,
    )
    defaults.update(overrides)
    return ScreenElement(**defaults)


class TestScreenBounds:
    def test_center_uses_half_extent(self):
        assert ScreenBounds(x=10, y=20, width=80, height=40).center == (50, 40)

    def test_to_dict_round_trip(self):
        bounds = ScreenBounds(x=1, y=2, width=3, height=4)
        assert ScreenBounds.from_dict(bounds.to_dict()) == bounds

    def test_from_dict_rejects_missing_fields(self):
        with pytest.raises(ValueError):
            ScreenBounds.from_dict({"x": 1, "y": 2, "width": 3})

    def test_from_dict_rejects_non_object(self):
        with pytest.raises(ValueError):
            ScreenBounds.from_dict("[0,0,1,1]")

    def test_from_dict_rejects_non_numeric_fields(self):
        with pytest.raises(ValueError):
            ScreenBounds.from_dict({"x": "a", "y": 2, "width": 3, "height": 4})


class TestScreenElement:
    def test_to_dict_omits_sparse_defaults(self):
        data = _element().to_dict()
        assert data == {
            "role": "button",
            "text": "确定",
            "bounds": {"x": 100, "y": 200, "width": 80, "height": 40},
            "ref": 1,
        }

    def test_to_dict_keeps_explicit_state(self):
        data = _element(
            ref=None,
            resource_id="com.app:id/ok",
            clickable=True,
            editable=True,
            scrollable=True,
            enabled=False,
        ).to_dict()
        assert data["resource_id"] == "com.app:id/ok"
        assert data["clickable"] and data["editable"] and data["scrollable"]
        assert data["enabled"] is False
        assert "ref" not in data

    def test_to_dict_round_trip(self):
        element = _element(
            resource_id="com.app:id/ok",
            clickable=True,
            scrollable=True,
            enabled=False,
        )
        assert ScreenElement.from_dict(element.to_dict()) == element

    def test_from_dict_accepts_at_string_ref(self):
        element = ScreenElement.from_dict(
            {
                "role": "button",
                "text": "ok",
                "bounds": {"x": 0, "y": 0, "width": 1, "height": 1},
                "ref": "@7",
            }
        )
        assert element.ref == 7

    def test_from_dict_rejects_bad_ref(self):
        with pytest.raises(ValueError):
            ScreenElement.from_dict(
                {
                    "role": "button",
                    "text": "ok",
                    "bounds": {"x": 0, "y": 0, "width": 1, "height": 1},
                    "ref": "@zero",
                }
            )

    def test_from_dict_rejects_missing_role_and_bounds(self):
        base = {"role": "button", "text": "ok", "bounds": {"x": 0, "y": 0, "width": 1, "height": 1}}
        with pytest.raises(ValueError):
            ScreenElement.from_dict({**base, "role": ""})
        no_bounds = {key: value for key, value in base.items() if key != "bounds"}
        with pytest.raises(ValueError):
            ScreenElement.from_dict(no_bounds)

    def test_from_dict_rejects_bad_flag_types(self):
        base = {"role": "button", "text": "ok", "bounds": {"x": 0, "y": 0, "width": 1, "height": 1}}
        with pytest.raises(ValueError):
            ScreenElement.from_dict({**base, "clickable": "yes"})

    def test_from_dict_rejects_non_object(self):
        with pytest.raises(ValueError):
            ScreenElement.from_dict("button")

    def test_element_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _element().ref = 2  # type: ignore[misc]


class TestScreenSnapshot:
    def test_markdown_renders_refs_and_info_lines(self):
        snapshot = ScreenSnapshot(
            viewport_width=1080,
            viewport_height=2400,
            elements=(
                _element(text="确 定\n"),
                _element(role="text", text="欢迎", ref=None),
            ),
        )
        assert snapshot.to_markdown() == "\n".join(
            [
                "# Device Viewport: 1080x2400",
                "## Interactive Elements:",
                '- [@1] button: "确 定"',
                '- (info) text: "欢迎"',
            ]
        )

    def test_markdown_includes_app_and_activity_when_present(self):
        snapshot = ScreenSnapshot(
            viewport_width=1,
            viewport_height=1,
            package_name="com.example",
            activity_name=".MainActivity",
        )
        assert snapshot.to_markdown() == "\n".join(
            [
                "# Device Viewport: 1x1",
                "# Active App: com.example",
                "# Activity: .MainActivity",
                "## Interactive Elements:",
            ]
        )

    def test_element_lookup_by_ref(self):
        first = _element(ref=1)
        second = _element(text="取消", ref=2)
        snapshot = ScreenSnapshot(
            viewport_width=1,
            viewport_height=1,
            elements=(first, second),
        )
        assert snapshot.element(2) is second
        assert snapshot.element(3) is None
        assert snapshot.element(0) is None
        assert snapshot.element(True) is None

    def test_interactable_filters_info_elements(self):
        snapshot = ScreenSnapshot(
            viewport_width=1,
            viewport_height=1,
            elements=(
                _element(ref=1),
                _element(role="text", ref=None),
                _element(text="取消", ref=2),
            ),
        )
        assert snapshot.interactable() == (_element(ref=1), _element(text="取消", ref=2))

    def test_to_dict_round_trip(self):
        snapshot = ScreenSnapshot(
            viewport_width=1080,
            viewport_height=2400,
            elements=(_element(resource_id="com.app:id/ok", clickable=True),),
            package_name="com.example",
            captured_at=12.5,
        )
        assert ScreenSnapshot.from_dict(snapshot.to_dict()) == snapshot

    def test_from_dict_rejects_missing_viewport(self):
        with pytest.raises(ValueError):
            ScreenSnapshot.from_dict({"elements": []})

    def test_from_dict_rejects_bad_elements_and_metadata(self):
        with pytest.raises(ValueError):
            ScreenSnapshot.from_dict({"viewport_width": 1, "viewport_height": 1, "elements": "all"})
        with pytest.raises(ValueError):
            ScreenSnapshot.from_dict(
                {"viewport_width": 1, "viewport_height": 1, "package_name": 3}
            )
        with pytest.raises(ValueError):
            ScreenSnapshot.from_dict(
                {"viewport_width": 1, "viewport_height": 1, "captured_at": "now"}
            )

    def test_from_dict_rejects_non_object(self):
        with pytest.raises(ValueError):
            ScreenSnapshot.from_dict(42)
