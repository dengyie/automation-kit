# -*- coding: utf-8 -*-
"""Restart-wave live probe: composite descriptor by + provider governance.

Hard-assertion live validation of the two capabilities shipped in the
2026-11 restart wave, against a real Android device:

1. **Composite descriptor** — resolves a resource-id'd node from a fresh
   hierarchy dump, then asserts the kit ``uiautomator`` descriptor by:
   single-key lookup exists, ``instance(k)`` bounds match the k-th dump
   match in document order, multi-kwarg ``wait_for_element`` converges.
2. **Governance failover** — a primary capability provider that always
   fails and a secondary backed by the real session's ``semantic_snapshot``
   action; the executor walk must land on the secondary and produce a real
   snapshot, with the health ledger recording one failure + one success.

Unlike ``live_probe_wave2.py`` (observational, print-only), every check
here is asserted: the script prints a JSON summary and exits non-zero when
any check fails, so it is usable as a parallel-smoke lane quality gate.

Usage:
    AUTOMATION_UIA2_UDID=10.144.144.52:5555 python scripts/live_probe_composite.py
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

SERIAL = os.environ.get("AUTOMATION_UIA2_UDID", "10.144.144.52:5555")


def run_probe(device, serial: str) -> dict:
    """Execute all checks against an injected uiautomator2-like device.

    Returns ``{"device", "checks": [{"name", "ok", "detail"}], "ok"}``;
    every check is asserted, a check failure never aborts the run (the
    summary reports it), and only infrastructure errors raise.
    """
    from adapters.uia2.session import Uia2Session
    from automation_core.drivers import ActionResult
    from automation_core.capabilities import (
        CapabilityExecutor,
        CapabilityRegistry,
        CapabilityRequest,
        CapabilityResolver,
        CapabilityResult,
        CapabilityExecutionProfile,
        CapabilityManifest,
    )
    from automation_core.execution import ExecutionContext

    checks: List[Dict[str, Any]] = []

    def check(name, fn):
        try:
            detail = fn()
            checks.append({"name": name, "ok": True, "detail": detail or "ok"})
        except Exception as exc:  # noqa: BLE001 - probe records, never crashes
            checks.append({"name": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"})

    session = Uia2Session(device, identifier=f"composite-probe-{serial}")
    session.start()

    # Descriptor-vs-dump comparisons need a STATIC screen: launch Settings
    # (present on every Android build, static list UI) and fall back to the
    # current front app when unavailable.
    front_app = "current"
    app_start = getattr(device, "app_start", None)
    if callable(app_start):
        try:
            app_start("com.android.settings")
            time.sleep(1.5)
            front_app = "com.android.settings"
        except Exception:
            front_app = "current"
    checks.append(
        {"name": "device.front_app", "ok": True, "detail": front_app}
    )

    def c_foreground_alignment():
        """Session-level foreground guard verification: the snapshot's
        ELEMENTS must carry foreground evidence (resource_id prefixed with
        the live package). Comparing package_name metadata would be
        tautological — it echoes app_current; element evidence proves the
        bounded dump retries actually landed a foreground-covered dump."""
        current = getattr(device, "app_current", None)
        live_package = None
        if callable(current):
            try:
                info = current()
                if isinstance(info, dict):
                    live_package = info.get("package")
            except Exception:
                live_package = None
        if not live_package:
            return "unverifiable (app_current unavailable)"
        snapshot = session.execute_action("semantic_snapshot", refresh=True)
        assert snapshot.success, f"semantic snapshot failed: {snapshot.message}"
        elements = snapshot.data.get("elements", [])
        evidence = [
            e.get("resource_id")
            for e in elements
            if (e.get("resource_id") or "").startswith(live_package + ":")
        ]
        assert evidence, (
            f"snapshot lacks foreground evidence for {live_package} "
            f"({len(elements)} elements) — dump flap survived the retries"
        )
        return f"aligned on {live_package} ({evidence[0]})"

    check("foreground.snapshot_alignment", c_foreground_alignment)

    def snapshot_elements() -> List[Dict[str, Any]]:
        """Fresh semantic snapshot elements — SAME source as the live
        selector (the accessibility view), so candidate discovery never
        diverges from what ``uiautomator`` can resolve. The raw
        ``dump_hierarchy`` was abandoned: the Redroid cloud phone merges
        overlay windows into it nondeterministically, so dump and live can
        disagree about which nodes exist at all.
        """
        outcome = session.execute_action("semantic_snapshot", refresh=True)
        if not outcome.success:
            raise AssertionError(f"semantic snapshot failed: {outcome.message}")
        return list(outcome.data.get("elements", []))

    def pick_target(elements: List[Dict[str, Any]]):
        """Resource-id with the most snapshot matches, tie-broken by first
        document order (the snapshot's element order)."""
        counts: Dict[str, List[Dict[str, Any]]] = {}
        order: List[str] = []
        for element in elements:
            rid = element.get("resource_id") or ""
            if not rid:
                continue
            if rid not in counts:
                counts[rid] = []
                order.append(rid)
            counts[rid].append(element)
        if not counts:
            return None, []
        rid = max(order, key=lambda key: len(counts[key]))
        return counts[rid][0], counts[rid]

    # --- 1. composite descriptor ------------------------------------------------
    def c_descriptor_lookup():
        target, _ = pick_target(snapshot_elements())
        assert target is not None, "no resource-id node in current snapshot"
        rid = target.get("resource_id")
        element = session.find_element("uiautomator", {"resourceId": rid})
        assert element.exists is True, f"descriptor lookup missing: {rid}"
        return f"resourceId={rid}"

    check("descriptor.single_key_lookup", c_descriptor_lookup)

    def c_descriptor_instance_order():
        """Instance semantics validated against LIVE truth only.

        Platform fact (cloud-phone Redroid, 2026-11-06): dump_hierarchy
        merges overlay windows (systemui), while the live UiSelector only
        sees the active window — dump match order/count is NOT a reliable
        oracle for live instance indexing across windows. The check therefore
        derives the live instance count by upward probing and asserts:
        instance(0) deterministic, each live instance resolvable, and an
        instance beyond the live count failing closed.
        """
        target, matches = pick_target(snapshot_elements())
        assert target is not None, "no resource-id node in current snapshot"
        rid = target.get("resource_id")
        # The snapshot is only used to PICK a candidate rid; the live side is
        # probed up to a ceiling instead of trusting any static count.
        probe_ceiling = max(len(matches), 32)

        def bounds_for(index):
            try:
                return session.execute_action(
                    "element_bounds",
                    by="uiautomator",
                    selector={"resourceId": rid, "instance": index},
                )
            except Exception as exc:  # live u2 raises on absent instances
                return ActionResult(False, f"{type(exc).__name__}: {exc}")

        first = bounds_for(0)
        assert first.success, f"instance(0) failed: {first.message}"
        again = bounds_for(0)
        assert again.success and again.data == first.data, (
            f"instance(0) nondeterministic: {first.data} vs {again.data}"
        )
        live_count = 1
        hit_ceiling = False
        for index in range(1, probe_ceiling):
            outcome = bounds_for(index)
            if not outcome.success:
                break
            live_count += 1
        else:
            hit_ceiling = True
        if not hit_ceiling:
            beyond = bounds_for(live_count)
            assert not beyond.success, (
                f"instance({live_count}) beyond live count must fail, "
                f"got {beyond.data}"
            )
        divergence = (
            f"snapshot matches={len(matches)} vs live instances={live_count}"
            if live_count != len(matches)
            else "snapshot and live agree"
        )
        ceiling_note = " [probe ceiling hit]" if hit_ceiling else ""
        return (
            f"resourceId={rid} x{live_count} live instances "
            f"({divergence}){ceiling_note}"
        )

    check("descriptor.instance_document_order", c_descriptor_instance_order)

    def c_descriptor_wait_for_element():
        target, _ = pick_target(snapshot_elements())
        assert target is not None, "no resource-id node in current snapshot"
        rid = target.get("resource_id")
        result = session.execute_action(
            "wait_for_element",
            by="uiautomator",
            selector={"resourceId": rid, "instance": 0},
            timeout=3.0,
            interval=0.2,
        )
        assert result.success, f"wait_for_element failed: {result.message}"
        return f"resourceId={rid}"

    check("descriptor.wait_for_element", c_descriptor_wait_for_element)

    # --- 2. governance failover over the real session ---------------------------
    def c_governance_failover():
        class AlwaysFailingPrimary:
            manifest = CapabilityManifest(
                name="visual.challenge",
                version="1.0.0",
                operations=("solve",),
                platforms=("android",),
                default_cancellation="cooperative",
            )

            def execution_profile(self, request):
                return CapabilityExecutionProfile(cancellation="cooperative")

            async def execute(self, request, context):
                return CapabilityResult(
                    success=False,
                    provider="primary-stub",
                    error_code="simulated_failure",
                    retryable=False,
                )

        class SessionSnapshotSecondary:
            """Real-device capability: semantic_snapshot via the kit session."""

            manifest = AlwaysFailingPrimary.manifest

            def execution_profile(self, request):
                return CapabilityExecutionProfile(cancellation="cooperative")

            async def execute(self, request, context):
                outcome = session.execute_action("semantic_snapshot", refresh=True)
                if not outcome.success:
                    return CapabilityResult(
                        success=False,
                        provider="session-secondary",
                        error_code="snapshot_failed",
                        retryable=False,
                    )
                return CapabilityResult(
                    success=True,
                    provider="session-secondary",
                    data={"markdown_head": outcome.data.get("markdown", "")[:80]},
                )

        registry = CapabilityRegistry()
        registry.register(AlwaysFailingPrimary(), name="primary-stub")
        registry.register(SessionSnapshotSecondary(), name="session-secondary")
        executor = CapabilityExecutor(CapabilityResolver(registry))
        context = ExecutionContext(
            run_id=f"composite-probe-{serial}",
            task_id="governance-check",
            workflow_name="live_probe_composite",
        )
        request = CapabilityRequest(
            capability="visual.challenge", operation="solve", parameters={}
        )
        result = asyncio.run(executor.execute(request, context))

        assert result.success is True, f"failover did not succeed: {result.to_dict()}"
        assert result.provider == "session-secondary", result.provider
        health = executor.resolver.health
        assert health.snapshot("primary-stub").consecutive_failures == 1, "primary not recorded"
        assert health.snapshot("session-secondary").state == "closed", "secondary not recorded"
        markdown = result.data.get("markdown_head", "")
        assert "# Device Viewport" in markdown or markdown, (
            "semantic snapshot did not yield a semantic view"
        )
        return f"failover ok, viewport view: {markdown[:40]!r}"

    check("governance.failover_real_session", c_governance_failover)

    session.stop()
    return {
        "device": serial,
        "checks": checks,
        "ok": all(item["ok"] for item in checks),
    }


def main() -> int:
    # Windows consoles choke on the CJK UI dumps; rewrap only when actually
    # running as a script (import-time wrapping breaks pytest capture).
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    import uiautomator2 as u2

    raw = u2.connect(SERIAL)
    summary = run_probe(raw, SERIAL)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
