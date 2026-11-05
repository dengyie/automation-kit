"""Offline tests for the restart-wave live probe (composite + governance)."""

import xml.etree.ElementTree as ET

import re as _re

from scripts.live_probe_composite import run_probe

_BOUNDS_RE = _re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


class FakeProbeDevice:
    """u2-like double: deterministic hierarchy with countable resource-ids."""

    HIERARCHY = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="com.android.settings:id/recycler" class="androidx.recyclerview.widget.RecyclerView" bounds="[0,144][1080,2340]">
    <node index="0" text="网络和互联网" resource-id="com.android.settings:id/title" class="android.widget.TextView" bounds="[84,300][996,380]" />
    <node index="1" text="已连接的设备" resource-id="com.android.settings:id/title" class="android.widget.TextView" bounds="[84,456][996,536]" />
    <node index="2" text="应用" resource-id="com.android.settings:id/title" class="android.widget.TextView" bounds="[84,612][996,692]" />
  </node>
</hierarchy>
"""

    def __init__(self):
        self.dumps = 0
        self.lookups = []

    def dump_hierarchy(self):
        self.dumps += 1
        return self.HIERARCHY

    def _matches(self, kwargs):
        root = ET.fromstring(self.HIERARCHY)
        hits = []
        for node in root.iter("node"):
            ok = True
            for key, expected in kwargs.items():
                if key == "instance":
                    continue
                if key == "resourceId":
                    ok = ok and (node.get("resource-id") or "") == expected
                elif key == "className":
                    ok = ok and (node.get("class") or "") == expected
                elif key == "text":
                    ok = ok and (node.get("text") or "") == expected
                elif key == "textContains":
                    ok = ok and expected in (node.get("text") or "")
                elif key == "description":
                    ok = ok and (node.get("content-desc") or "") == expected
                elif key == "descriptionContains":
                    ok = ok and expected in (node.get("content-desc") or "")
                else:
                    ok = False
            if ok:
                hits.append(node)
        instance = kwargs.get("instance")
        if isinstance(instance, int) and not isinstance(instance, bool):
            hits = hits[instance : instance + 1]
        return hits

    def __call__(self, **kwargs):
        """Mirror the real uiautomator2 selector: multi-kwarg + instance."""
        self.lookups.append(dict(kwargs))
        hits = self._matches(kwargs)
        if not hits:
            return FakeWidget(exists=False)
        node = hits[0]
        match = _BOUNDS_RE.fullmatch(node.get("bounds") or "")
        assert match is not None, f"bad bounds in fixture: {node.get('bounds')}"
        left, top, right, bottom = (int(part) for part in match.groups())
        return FakeWidget(
            exists=True,
            info={"bounds": {"left": left, "top": top, "right": right, "bottom": bottom}},
        )

    def click(self, x, y):
        pass

    def press(self, key):
        pass

    def app_current(self):
        return {"package": "com.android.settings", "activity": ".Settings"}

    def screenshot(self):
        return b"png"


class FakeWidget:
    def __init__(self, exists, info=None):
        self.exists = exists
        self.info = info or {}

    def click(self):
        pass


def test_run_probe_all_checks_pass_on_scripted_device():
    device = FakeProbeDevice()

    summary = run_probe(device, "fake:5555")

    assert summary["device"] == "fake:5555"
    assert summary["ok"] is True, summary
    names = [item["name"] for item in summary["checks"]]
    assert names == [
        "device.front_app",
        "descriptor.single_key_lookup",
        "descriptor.instance_document_order",
        "descriptor.wait_for_element",
        "governance.failover_real_session",
    ]
    assert all(item["ok"] for item in summary["checks"])


def test_run_probe_instance_semantics_live_truth():
    """Instance semantics validated against live truth: instance(0)
    deterministic, upward probing counts live instances, beyond-count fails
    closed. The fixture's dump and live views agree, so the divergence note
    reads "dump and live agree"."""
    device = FakeProbeDevice()

    summary = run_probe(device, "fake:5555")

    instance_check = next(
        item
        for item in summary["checks"]
        if item["name"] == "descriptor.instance_document_order"
    )
    assert instance_check["ok"] is True
    assert "x3 live instances" in instance_check["detail"]
    assert "snapshot and live agree" in instance_check["detail"]


def test_run_probe_records_dump_live_divergence_without_failing():
    """Multi-window ROMs merge overlays into the dump; a live count lower
    than the dump count is recorded as info, not a check failure."""
    device = FakeProbeDevice()
    original = device.__class__.__call__

    def call(self, **kwargs):
        # The live view lost one title node: overlay-window semantics.
        if (
            kwargs.get("resourceId") == "com.android.settings:id/title"
            and kwargs.get("instance") == 2
        ):
            return FakeWidget(exists=False)
        return original(self, **kwargs)

    device.__class__ = type(
        "PartialLiveDevice", (device.__class__,), {"__call__": call}
    )

    summary = run_probe(device, "fake:5555")

    instance_check = next(
        item
        for item in summary["checks"]
        if item["name"] == "descriptor.instance_document_order"
    )
    assert instance_check["ok"] is True
    assert "x2 live instances" in instance_check["detail"]
    assert "snapshot matches=3" in instance_check["detail"]


def test_run_probe_reports_check_failure_without_crashing():
    class BrokenDevice(FakeProbeDevice):
        def dump_hierarchy(self):
            return "<hierarchy><node text='no ids here' bounds='[0,0][10,10]' /></hierarchy>"

    summary = run_probe(BrokenDevice(), "fake:5555")

    assert summary["ok"] is False
    descriptor_checks = [
        item
        for item in summary["checks"]
        if item["name"].startswith("descriptor.")
    ]
    assert descriptor_checks and all(
        not item["ok"] for item in descriptor_checks
    )
    assert all("no resource-id node" in item["detail"] for item in descriptor_checks)


def test_run_probe_governance_fails_when_device_cannot_snapshot():
    class NoDumpDevice(FakeProbeDevice):
        def dump_hierarchy(self):
            raise RuntimeError("hierarchy service down")

    summary = run_probe(NoDumpDevice(), "fake:5555")

    governance = next(
        item
        for item in summary["checks"]
        if item["name"] == "governance.failover_real_session"
    )
    # The secondary must report a typed failure instead of hanging, and the
    # check records the overall failover outcome (primary failure first).
    assert governance["ok"] is False
    assert "snapshot_failed" in governance["detail"] or "did not succeed" in governance["detail"]
