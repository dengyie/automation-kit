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
        "foreground.snapshot_alignment",
        "descriptor.single_key_lookup",
        "descriptor.instance_document_order",
        "descriptor.wait_for_element",
        "governance.failover_real_session",
        "transport.stall_health",
    ]
    alignment = next(
        item
        for item in summary["checks"]
        if item["name"] == "foreground.snapshot_alignment"
    )
    # The fake reports app_current com.android.settings; the session-level
    # foreground guard re-dumps until the hierarchy carries that package.
    assert alignment["ok"] is True
    assert "aligned on com.android.settings" in alignment["detail"]
    assert all(item["ok"] for item in summary["checks"])
    # Every check carries a wall-clock measurement for stall diagnosis.
    assert all(isinstance(item.get("elapsed_s"), float) for item in summary["checks"])
    stall = next(
        item for item in summary["checks"] if item["name"] == "transport.stall_health"
    )
    assert stall["ok"] is True
    assert "no transport stalls" in stall["detail"]


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


def test_foreground_alignment_reports_mismatch_as_failure():
    """If the snapshot still lands on the wrong window after the session's
    bounded retries, the gate must fail loudly instead of passing."""

    class MisalignedDevice(FakeProbeDevice):
        def app_current(self):
            return {"package": "com.example.settings", "activity": ".Settings"}

    summary = run_probe(MisalignedDevice(), "fake:5555")

    alignment = next(
        item
        for item in summary["checks"]
        if item["name"] == "foreground.snapshot_alignment"
    )
    assert alignment["ok"] is False
    assert "lacks foreground evidence" in alignment["detail"]


def test_foreground_alignment_degrades_to_unverifiable():
    class NoMetadataDevice(FakeProbeDevice):
        def app_current(self):
            return "not-a-dict"

    summary = run_probe(NoMetadataDevice(), "fake:5555")

    alignment = next(
        item
        for item in summary["checks"]
        if item["name"] == "foreground.snapshot_alignment"
    )
    assert alignment["ok"] is True
    assert "unverifiable" in alignment["detail"]


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


def test_stall_health_warns_without_failing_when_stalls_absorbed():
    """Absorbed stalls are evidence of transport flapping: reported in the
    detail with per-op counts, but the check stays green (fail-warn)."""

    class StallingDevice(FakeProbeDevice):
        def dump_hierarchy(self):
            self.dumps += 1
            if self.dumps == 1:
                # Simulate a stall that outlives driver_call_timeout: the
                # session's daemon worker abandons it and retries.
                import threading
                import time as _time

                _time.sleep(0.5)
                threading.Event().wait()
            return self.HIERARCHY

    # A tiny timeout keeps the offline test fast while still exercising
    # the abandon-and-retry path inside the probe's session.
    import adapters.uia2.session as session_mod

    original_default = session_mod.DEFAULT_DRIVER_CALL_TIMEOUT
    session_mod.DEFAULT_DRIVER_CALL_TIMEOUT = 0.2
    try:
        summary = run_probe(StallingDevice(), "fake:5555")
    finally:
        session_mod.DEFAULT_DRIVER_CALL_TIMEOUT = original_default

    stall = next(
        item for item in summary["checks"] if item["name"] == "transport.stall_health"
    )
    assert stall["ok"] is True, "stall evidence must not fail the probe"
    assert "WARN" in stall["detail"]
    assert "dump x1" in stall["detail"]


def test_alignment_degrades_and_warns_when_shell_query_stalls():
    """The probe's foreground ground truth goes through the session's
    _foreground_app: a stalled shell query is absorbed (fail-warn in
    transport.stall_health) and the alignment check degrades to
    'unverifiable' instead of crashing the run."""

    class StallingShellProbeDevice(FakeProbeDevice):
        def shell(self, cmdargs, timeout=60):
            import threading

            threading.Event().wait()  # blocks until process exit
            return ""  # unreachable

    summary = run_probe(StallingShellProbeDevice(), "fake:5555", driver_call_timeout=0.2)

    alignment = next(
        item
        for item in summary["checks"]
        if item["name"] == "foreground.snapshot_alignment"
    )
    assert alignment["ok"] is True
    assert "unverifiable" in alignment["detail"]
    stall = next(
        item for item in summary["checks"] if item["name"] == "transport.stall_health"
    )
    assert stall["ok"] is True
    assert "app_current_shell x" in stall["detail"]
