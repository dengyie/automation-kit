"""Gap-coverage tests for adapters/uia2/distill.py.

Pins the rarely-hit contracts: the root-is-node success path, the iter()
fallback for deeply nested window nodes, the min_element_size guard, the
full infer_semantic_role class matrix (checkbox/switch/tab/unknown/image),
the label-depth cutoff at _LABEL_DEPTH_LIMIT, and the two-level
interactive-descendant recursion.
"""

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


def _screen(*children):
    return "".join(
        [
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
            '<hierarchy rotation="0">',
            _node(
                cls="android.widget.FrameLayout",
                bounds="[0,0][1080,2400]",
                children="".join(children),
            ),
            "</hierarchy>",
        ]
    )


# --- parse_hierarchy edges (line 79, 88-91) ----------------------------------------


def test_parse_hierarchy_root_is_node_success_path():
    """A dump whose root already IS a node (plain root tag) is returned
    directly with its own bounds as the viewport — the success mirror of
    test_parse_hierarchy_rejects_node_without_bounds."""
    root, viewport = parse_hierarchy(
        '<node text="单根" class="android.widget.TextView" bounds="[10,20][110,120]"/>'
    )

    assert root.text == "单根"
    assert viewport.width == 100
    assert viewport.height == 100
    assert (viewport.x, viewport.y) == (10, 20)


def test_parse_hierarchy_fallback_scans_nested_nodes():
    """When the hierarchy root has no DIRECT node children (e.g. nodes are
    wrapped one level deeper by a nonstandard ROM), the iter() fallback
    rescues the first parseable node instead of failing with 'no node
    entries'."""
    xml = "".join(
        [
            '<hierarchy rotation="0">',
            "<windows>",
            '<node text="深窗" class="android.widget.TextView" bounds="[0,0][200,100]"/>',
            "</windows>",
            "</hierarchy>",
        ]
    )

    root, viewport = parse_hierarchy(xml)

    # Single rescued node is returned directly (no synthetic root wrapper).
    assert (root.text, root.children) == ("深窗", [])
    assert viewport.width == 200
    assert viewport.height == 100


# --- distill_snapshot guard (line 119) ----------------------------------------------


def test_distill_rejects_non_positive_min_element_size():
    with pytest.raises(HierarchyDistillError, match="min_element_size must be >= 1"):
        distill_snapshot(
            _screen(_node(text="x", bounds="[0,0][100,50]")),
            min_element_size=0,
        )


# --- infer_semantic_role class matrix (194, 196, 198, 211, 214) ----------------------


def test_infer_semantic_role_class_matrix():
    """Checkable/tab/switch classes each get their own role before the
    clickable fallback; a classless checkable view with no label falls all
    the way through to the 'unknown' bucket."""
    xml = _screen(
        _node(checkable=True, cls="android.widget.CheckBox", bounds="[0,100][100,200]"),
        _node(checkable=True, cls="android.widget.Switch", bounds="[0,200][200,300]"),
        _node(clickable=True, cls="android.widget.TabWidget", bounds="[0,300][300,400]"),
        _node(checkable=True, cls="android.view.View", bounds="[0,400][400,500]"),
    )

    snapshot = distill_snapshot(xml)

    assert [el.role for el in snapshot.elements] == [
        "checkbox",
        "switch",
        "tab",
        "unknown",
    ]


def test_info_leaf_imageview_role():
    """A non-interactive ImageView leaf carrying text is distilled as an
    'image' info element (image check precedes the text fallback)."""
    xml = _screen(_node(text="无障碍图标", cls="android.widget.ImageView", bounds="[10,10][80,80]"))

    snapshot = distill_snapshot(xml)

    assert [el.role for el in snapshot.elements] == ["image"]
    assert snapshot.elements[0].ref is None
    assert snapshot.elements[0].text == "无障碍图标"


# --- _collect_descendant_texts depth cutoff (line 276) -------------------------------


def test_label_collection_cut_off_beyond_depth_limit():
    """Labels are collected only within _LABEL_DEPTH_LIMIT (5): a sixth-level
    descendant's text is deliberately excluded from the container's label,
    while the fifth level still counts."""

    def build(depth):
        if depth == 6:
            return _node(text="第六层", bounds="[0,0][1080,100]")
        return _node(
            text=f"第{'一二三四五'[depth - 1]}层",
            bounds="[0,0][1080,600]",
            children=build(depth + 1),
        )

    xml = _screen(
        _node(
            cls="android.widget.Button",
            clickable=True,
            bounds="[0,0][1080,700]",
            children=build(1),
        )
    )

    snapshot = distill_snapshot(xml)

    assert len(snapshot.elements) == 1
    label = snapshot.elements[0].text
    assert "第五层" in label
    assert "第六层" not in label


# --- _has_interactive_descendants two-level recursion (line 300) ---------------------


def test_interactive_descendant_found_two_levels_deep():
    """A clickable container whose interactive descendant sits TWO levels
    down is kept as a ref via the recursive scan (the direct-child check on
    the inert middle node fails, the recursion succeeds)."""
    xml = _screen(
        _node(
            cls="android.widget.LinearLayout",
            clickable=True,
            bounds="[0,100][1080,600]",
            children=_node(
                cls="android.widget.FrameLayout",
                bounds="[0,150][1080,550]",
                children=_node(
                    text="深层按钮",
                    cls="android.widget.Button",
                    clickable=True,
                    bounds="[100,200][900,500]",
                ),
            ),
        )
    )

    snapshot = distill_snapshot(xml)

    assert [(el.ref, el.role) for el in snapshot.elements] == [
        (1, "item"),
        (2, "button"),
    ]
