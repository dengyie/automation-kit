import pytest

from adapters.uia2 import HierarchyDistillError, distill_snapshot
from adapters.uia2.distill import parse_hierarchy


def _node(
    text="",
    resource_id="",
    cls="android.widget.TextView",
    desc="",
    clickable=False,
    enabled=True,
    scrollable=False,
    checkable=False,
    bounds="[0,0][0,0]",
    children="",
):
    attrs = (
        f'index="0" text="{text}" resource-id="{resource_id}" class="{cls}" '
        f'package="com.example" content-desc="{desc}" '
        f'checkable="{"true" if checkable else "false"}" '
        f'clickable="{"true" if clickable else "false"}" '
        f'enabled="{"true" if enabled else "false"}" '
        f'scrollable="{"true" if scrollable else "false"}" '
        f'bounds="{bounds}"'
    )
    return f"<node {attrs}>{children}</node>"


SCREEN_XML = "".join(
    [
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
        '<hierarchy rotation="0">',
        _node(cls="android.widget.FrameLayout", bounds="[0,0][1080,2400]", children="".join([
            # Static display text (info element, no ref)
            _node(text="设置", bounds="[440,100][640,160]"),
            # Clickable image button labelled only by content-desc
            _node(
                desc="搜索",
                cls="android.widget.ImageButton",
                clickable=True,
                bounds="[900,80][1040,220]",
            ),
            # Edit text with a hint child whose text is promoted as label
            _node(
                resource_id="com.example:id/search_src_text",
                cls="android.widget.EditText",
                clickable=True,
                bounds="[40,300][1040,400]",
                children=_node(text="搜索我的订单", bounds="[60,320][400,380]"),
            ),
            # Fully outside the viewport: pruned with its subtree
            _node(
                text="below the fold",
                clickable=True,
                bounds="[0,2500][1080,2900]",
            ),
            # Disabled button: distilled but flagged
            _node(
                text="禁用按钮",
                cls="android.widget.Button",
                clickable=True,
                enabled=False,
                bounds="[100,500][500,600]",
            ),
            # Scrollable container with a clickable child item
            _node(
                cls="androidx.recyclerview.widget.RecyclerView",
                scrollable=True,
                bounds="[0,700][1080,2300]",
                children=_node(
                    text="订单一",
                    cls="android.widget.LinearLayout",
                    clickable=True,
                    bounds="[0,700][1080,900]",
                ),
            ),
        ])),
        "</hierarchy>",
    ]
)


def test_parse_hierarchy_returns_root_and_viewport():
    root, viewport = parse_hierarchy(SCREEN_XML)

    assert viewport.width == 1080
    assert viewport.height == 2400
    assert len(root.children) == 6


def test_parse_hierarchy_rejects_malformed_xml():
    with pytest.raises(HierarchyDistillError):
        parse_hierarchy("<hierarchy><node></hierarchy>")


def test_parse_hierarchy_rejects_empty_hierarchy():
    with pytest.raises(HierarchyDistillError):
        parse_hierarchy('<hierarchy rotation="0"></hierarchy>')


def test_parse_hierarchy_rejects_node_without_bounds():
    with pytest.raises(HierarchyDistillError):
        parse_hierarchy('<node text="x" class="android.widget.TextView"/>')


def test_distill_snapshot_elements_and_metadata():
    snapshot = distill_snapshot(
        SCREEN_XML,
        package_name="com.example",
        activity_name=".MainActivity",
        device_id="dut-1",
        captured_at=123.5,
    )

    assert snapshot.viewport_width == 1080
    assert snapshot.viewport_height == 2400
    assert snapshot.package_name == "com.example"
    assert snapshot.activity_name == ".MainActivity"
    assert snapshot.device_id == "dut-1"
    assert snapshot.captured_at == 123.5
    # 设置(info) + 搜索(ref1) + 搜索框(ref2) + 禁用按钮(ref3) + 订单一(ref4)
    assert [(el.ref, el.role) for el in snapshot.elements] == [
        (None, "text"),
        (1, "button"),
        (2, "input"),
        (3, "button"),
        (4, "button"),
    ]


def test_distill_promotes_descendant_label():
    snapshot = distill_snapshot(SCREEN_XML)

    edit = snapshot.element(2)
    assert edit is not None
    assert edit.text == "搜索我的订单"
    assert edit.resource_id == "com.example:id/search_src_text"
    assert edit.editable and edit.clickable


def test_distill_hoists_content_desc_for_icon_buttons():
    snapshot = distill_snapshot(SCREEN_XML)

    search = snapshot.element(1)
    assert search is not None
    assert search.text == "搜索"
    assert search.clickable and not search.editable


def test_distill_marks_disabled_elements():
    snapshot = distill_snapshot(SCREEN_XML)

    disabled = snapshot.element(3)
    assert disabled is not None
    assert disabled.enabled is False
    assert disabled.to_dict()["enabled"] is False


def test_distill_prunes_off_viewport_subtrees():
    snapshot = distill_snapshot(SCREEN_XML)

    assert all("below the fold" not in el.text for el in snapshot.elements)


def test_distill_recurses_into_scrollable_containers():
    snapshot = distill_snapshot(SCREEN_XML)

    item = snapshot.element(4)
    assert item is not None
    assert item.text == "订单一"
    assert item.center == (540, 800)


def test_distill_interactable_excludes_info_elements():
    snapshot = distill_snapshot(SCREEN_XML)

    assert [el.ref for el in snapshot.interactable()] == [1, 2, 3, 4]


def test_distill_min_element_size_filters_slivers():
    thin_button = "".join(
        [
            "<hierarchy rotation=\"0\">",
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    text="x",
                    cls="android.widget.Button",
                    clickable=True,
                    bounds="[0,0][1080,4]",
                ),
            ),
            "</hierarchy>",
        ]
    )

    snapshot = distill_snapshot(thin_button, min_element_size=8)

    assert snapshot.elements == ()


def test_distill_keeps_full_bounds_for_partially_visible_elements():
    partial_xml = "".join(
        [
            "<hierarchy rotation=\"0\">",
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    text="贴边按钮",
                    cls="android.widget.Button",
                    clickable=True,
                    bounds="[0,2350][540,2600]",
                ),
            ),
            "</hierarchy>",
        ]
    )

    snapshot = distill_snapshot(partial_xml)

    # Included via the 50px visible intersection but carrying the full
    # physical rectangle; ref dispatch clamps to the visible region.
    button = snapshot.element(1)
    assert button is not None
    assert button.bounds.to_dict() == {
        "x": 0,
        "y": 2350,
        "width": 540,
        "height": 250,
    }


def test_distill_emits_scrollable_leaf_inside_clickable_container():
    nested_xml = "".join(
        [
            "<hierarchy rotation=\"0\">",
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children=_node(
                    cls="android.widget.LinearLayout",
                    clickable=True,
                    bounds="[0,100][1080,500]",
                    children=_node(
                        cls="androidx.recyclerview.widget.RecyclerView",
                        scrollable=True,
                        bounds="[100,200][1000,400]",
                    ),
                ),
            ),
            "</hierarchy>",
        ]
    )

    snapshot = distill_snapshot(nested_xml)

    # Without the scrollable-leaf clause in _has_interactive_descendants
    # the container prunes early and the nested scrollable never gets a ref.
    assert [(el.ref, el.role) for el in snapshot.elements] == [
        (1, "item"),
        (2, "scrollable"),
    ]
