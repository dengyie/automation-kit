# -*- coding: utf-8 -*-
"""Two-device parallel live smoke orchestration (device-farm minimal cut).

Task 14 (development.md §12.13) stays trigger-gated on real infrastructure;
the minimal cut is orchestration only: run the two existing live probes
concurrently as isolated subprocesses and aggregate the outcomes.

Lanes (both optional, at least one required):

- ``dianping``: sibling automation-app-dianping live smoke on a real phone
  (``python -m automation_app_dianping live --mode smoke --driver uia2`` with
  ``DIANPING_LIVE_E2E=1`` + ``DIANPING_DEVICE_UDID``).
- ``uia2``: this repo's wave-2 adapter probe on a second device
  (``scripts/live_probe_wave2.py`` with ``AUTOMATION_UIA2_UDID``).

Each lane runs in its own process with its own env and artifact root under
``live_artifacts/<run_id>/``; per-lane stdout/stderr is teed to a log file and
the aggregated result lands in ``summary.json``. Without ``--execute`` the
script only prints the resolved plan (dry mode), so wiring can be verified
offline; the pure helpers are unit-tested (tests/scripts/).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

KIT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIANPING_REPO = KIT_ROOT.parent / "automation-app-dianping"
DEFAULT_UIA2_UDID = "10.144.144.52:5555"

Runner = Callable[[str, list, str, Dict[str, str]], "asyncio.Future"]


def build_lane_plan(
    run_id: str,
    *,
    include_dianping: bool = False,
    include_uia2: bool = False,
    dianping_udid: Optional[str] = None,
    uia2_udid: Optional[str] = None,
    dianping_repo: Optional[Path] = None,
    kit_root: Optional[Path] = None,
    base_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Resolve the per-lane argv/cwd/env without touching any process.

    Pure function; unit tests assert the wiring contracts (env isolation,
    artifact roots, sibling repo layout).
    """
    kit_root = Path(kit_root) if kit_root else KIT_ROOT
    dianping_repo = (
        Path(dianping_repo) if dianping_repo else DEFAULT_DIANPING_REPO
    )
    base_env = dict(base_env if base_env is not None else os.environ)
    artifact_root = kit_root / "live_artifacts" / run_id
    plan: Dict[str, Dict[str, Any]] = {}

    if include_uia2:
        env = dict(base_env)
        env["AUTOMATION_UIA2_UDID"] = uia2_udid or env.get(
            "AUTOMATION_UIA2_UDID", DEFAULT_UIA2_UDID
        )
        env["PYTHONPATH"] = str(kit_root)
        plan["uia2"] = {
            "argv": [
                sys.executable,
                str(kit_root / "scripts" / "live_probe_wave2.py"),
            ],
            "cwd": str(artifact_root / "uia2"),
            "env": env,
            "artifact_root": str(artifact_root / "uia2"),
        }

    if include_dianping:
        env = dict(base_env)
        env["DIANPING_LIVE_E2E"] = "1"
        env["DIANPING_DRIVER"] = "uia2"
        if dianping_udid:
            env["DIANPING_DEVICE_UDID"] = dianping_udid
        plan["dianping"] = {
            "argv": [
                sys.executable,
                "-m",
                "automation_app_dianping",
                "live",
                "--mode",
                "smoke",
                "--driver",
                "uia2",
            ],
            "cwd": str(dianping_repo),
            "env": env,
            "artifact_root": str(dianping_repo / "artifacts" / "dianping-live"),
        }

    if not plan:
        raise SystemExit(
            "no lane selected: pass --dianping and/or --uia2"
        )
    return plan


def aggregate(plan: Dict[str, Dict[str, Any]], results: Dict[str, Any]) -> Dict[str, Any]:
    """Merge lane outcomes into the summary document."""
    lanes = {}
    succeeded = 0
    for lane, outcome in results.items():
        ok = bool(outcome.get("returncode") == 0)
        succeeded += 1 if ok else 0
        lanes[lane] = {
            "ok": ok,
            "returncode": outcome.get("returncode"),
            "duration_s": outcome.get("duration_s"),
            "log": outcome.get("log"),
        }
    return {
        "run_id": plan.get("run_id"),
        "lanes": lanes,
        "succeeded": succeeded,
        "total": len(lanes),
        "ok": succeeded == len(lanes) and len(lanes) > 0,
    }


# Env keys that are safe (and useful) to show in the printed dry-run plan.
# Everything else inherits the parent environment silently and is rendered as
# "<inherited>" so wholesale os.environ content (tokens, credentials) never
# lands in terminal or CI logs.
DISPLAY_ENV_KEYS = (
    "AUTOMATION_UIA2_UDID",
    "AUTOMATION_PHONE_PLAYWRIGHT_UDID",
    "DIANPING_LIVE_E2E",
    "DIANPING_DRIVER",
    "DIANPING_DEVICE_UDID",
    "PYTHONPATH",
    "PYTHONUNBUFFERED",
)


def _redact_env(env: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (env[key] if key in DISPLAY_ENV_KEYS else "<inherited>")
        for key in sorted(env)
    }


def _redact_plan(plan: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        lane: {
            **spec,
            "env": _redact_env(spec.get("env", {})),
        }
        for lane, spec in plan.items()
    }


async def run_lane(
    lane: str,
    spec: Dict[str, Any],
    log_dir: Path,
    spawn: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Spawn one lane subprocess, tee output to its log, return the outcome."""
    log_dir.mkdir(parents=True, exist_ok=True)
    # The lane cwd doubles as its artifact root and does not exist yet for
    # fresh run ids; CreateProcess fails hard on a missing cwd.
    Path(spec["cwd"]).mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{lane}.log"
    spec["env"].setdefault("PYTHONUNBUFFERED", "1")
    started = time.monotonic()
    create = spawn or asyncio.create_subprocess_exec
    process = await create(
        *spec["argv"],
        cwd=spec["cwd"],
        env=spec["env"],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output_bytes, _ = await process.communicate()
    duration = time.monotonic() - started
    log_path.write_bytes(output_bytes or b"")
    return {
        "returncode": process.returncode,
        "duration_s": round(duration, 2),
        "log": str(log_path),
    }


async def execute_plan(
    plan: Dict[str, Dict[str, Any]],
    run_root: Path,
    spawn: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Run every lane concurrently; ``spawn`` is injectable for offline tests."""
    outcomes = await asyncio.gather(
        *(
            run_lane(lane, spec, run_root, spawn=spawn)
            for lane, spec in plan.items()
        )
    )
    results = dict(zip(plan.keys(), outcomes))
    return aggregate({"run_id": run_root.name}, results)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", default=time.strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--dianping", action="store_true", help="run the dianping live smoke lane")
    parser.add_argument("--dianping-udid", default=None, help="adb serial for the dianping lane")
    parser.add_argument("--uia2", action="store_true", help="run the uia2 adapter probe lane")
    parser.add_argument("--uia2-udid", default=None, help="adb serial for the uia2 lane")
    parser.add_argument("--execute", action="store_true", help="actually spawn the lanes (default: dry plan)")
    args = parser.parse_args(argv)

    plan = build_lane_plan(
        args.run_id,
        include_dianping=args.dianping,
        include_uia2=args.uia2,
        dianping_udid=args.dianping_udid,
        uia2_udid=args.uia2_udid,
    )
    run_root = KIT_ROOT / "live_artifacts" / args.run_id

    if not args.execute:
        # Never print lane env wholesale: it inherits os.environ and would
        # dump credentials to the terminal / CI log.
        print(
            json.dumps(
                {"run_id": args.run_id, **_redact_plan(plan)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    summary = asyncio.run(execute_plan(plan, run_root))
    run_root.mkdir(parents=True, exist_ok=True)
    summary_path = run_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
