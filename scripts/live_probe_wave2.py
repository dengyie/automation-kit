# -*- coding: utf-8 -*-
"""Wave-2 live capability probe against a real Android device (uia2 adapter).

Exercises: semantic_snapshot, warm-cache @N ref tap, element_bounds,
scroll_into_view (settle), press_back/press_home — with dump-call accounting
to verify the snapshot TTL reuse contract.
"""
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import uiautomator2 as u2

from adapters.uia2.session import Uia2Session

SERIAL = "10.144.144.52:5555"


class CountingDevice:
    """Proxy counting dump_hierarchy calls to verify warm-cache dispatch."""

    def __init__(self, inner):
        self._inner = inner
        self.dumps = 0
        self.clicks = []
        self.swipes = []

    def dump_hierarchy(self):
        self.dumps += 1
        return self._inner.dump_hierarchy()

    def click(self, x, y):
        self.clicks.append((x, y))
        return self._inner.click(x, y)

    def swipe(self, fx, fy, tx, ty, duration):
        self.swipes.append((fx, fy, tx, ty, duration))
        return self._inner.swipe(fx, fy, tx, ty, duration)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def section(title):
    print(f"\n===== {title} =====")


def main():
    raw = u2.connect(SERIAL)
    device = CountingDevice(raw)
    session = Uia2Session(device, identifier="live-probe", artifact_root=__import__("pathlib").Path("live_artifacts"))
    session.start()

    section("0. device state")
    print("current app:", device.app_current())

    section("1. semantic_snapshot (fresh)")
    result = session.execute_action("semantic_snapshot", refresh=True)
    print("success:", result.success, "| message:", result.message)
    data = result.data
    print("viewport:", data.get("viewport_width"), "x", data.get("viewport_height"))
    print("package:", data.get("package_name"))
    print("elements:", len(data.get("elements", [])))
    print("dumps after snapshot:", device.dumps)
    md = data.get("markdown", "")
    print("--- markdown head ---")
    print("\n".join(md.splitlines()[:20]))

    section("2. tap by @N ref (warm cache)")
    refs = [e for e in data.get("elements", []) if e.get("ref") and e.get("enabled", True)]
    if not refs:
        print("NO tappable ref found on current screen; skipping tap")
        tap_ref = None
    else:
        # Prefer the launcher Settings icon; fall back to the first ref
        target = next((e for e in refs if e.get("text") == "设置"), refs[0])
        tap_ref = f"@{target['ref']}"
        print("target:", tap_ref, target.get("role"), repr(target.get("text"))[:60], target.get("bounds"))
        dumps_before = device.dumps
        time.sleep(0.05)
        tap_result = session.execute_action("tap", selector=tap_ref, by="ref")
        print("tap success:", tap_result.success, "| message:", tap_result.message)
        print("dumps used by tap:", device.dumps - dumps_before, "(expect 0 if within TTL)")
        print("device clicks:", device.clicks)
        time.sleep(2.0)
        print("current app after tap:", device.app_current().get("package"))

    section("3. element_bounds by ref")
    if tap_ref:
        bounds_result = session.execute_action("element_bounds", selector=tap_ref, by="ref")
        print("success:", bounds_result.success, "| data:", bounds_result.data)

    section("4. press_back / press_home")
    back_result = session.execute_action("press_back")
    print("press_back:", back_result.success, back_result.message)
    time.sleep(0.5)
    home_result = session.execute_action("press_home")
    print("press_home:", home_result.success, home_result.message)
    time.sleep(0.5)
    print("current app after home:", device.app_current().get("package"))

    section("5. scroll_into_view on Settings (text selector)")
    # Requirements: the tap in step 2 opened the system Settings app. If not
    # (e.g. the launcher icon was absent), open it via adb-safe app_start.
    package_now = device.app_current().get("package")
    if package_now != "com.android.settings":
        device.app_start("com.android.settings")
        time.sleep(2.0)
        package_now = device.app_current().get("package")
    print("current app:", package_now)
    scroll_result = session.execute_action(
        "scroll_into_view", by="text", selector="电池", direction="up", max_swipes=6
    )
    print("scroll success:", scroll_result.success, "| message:", scroll_result.message)
    print("scroll data:", scroll_result.data)
    print("swipes issued:", len(device.swipes))
    if device.swipes:
        print("first swipe:", device.swipes[0])

    section("6. final totals")
    print("total dumps:", device.dumps, "| total clicks:", device.clicks, "| total swipes:", len(device.swipes))

    session.stop()
    print("\nPROBE COMPLETE")


if __name__ == "__main__":
    main()
