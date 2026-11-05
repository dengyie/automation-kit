"""Offline tests for the two-device parallel live smoke orchestrator."""

import asyncio
import json
from pathlib import Path

import pytest

from scripts.live_parallel_smoke import (
    DEFAULT_UIA2_UDID,
    aggregate,
    build_lane_plan,
    execute_plan,
)


def build(**overrides):
    fields = {
        "run_id": "run-1",
        "include_dianping": True,
        "include_uia2": True,
        "kit_root": Path("/fake/kit"),
        "dianping_repo": Path("/fake/dianping"),
        "base_env": {"PATH": "/bin", "DIANPING_DEVICE_UDID": "1A2B3C"},
    }
    fields.update(overrides)
    return build_lane_plan(**fields)


def test_plan_builds_two_isolated_lanes():
    plan = build()

    assert set(plan) == {"dianping", "uia2"}
    uia2 = plan["uia2"]
    dianping = plan["dianping"]

    assert uia2["env"]["AUTOMATION_UIA2_UDID"] == DEFAULT_UIA2_UDID
    assert uia2["env"]["PATH"] == "/bin"
    assert uia2["cwd"] == str(Path("/fake/kit/live_artifacts/run-1/uia2"))
    assert uia2["argv"][-1] == str(Path("/fake/kit/scripts/live_probe_wave2.py"))

    assert dianping["env"]["DIANPING_LIVE_E2E"] == "1"
    assert dianping["env"]["DIANPING_DRIVER"] == "uia2"
    assert dianping["env"]["DIANPING_DEVICE_UDID"] == "1A2B3C"
    assert dianping["cwd"] == str(Path("/fake/dianping"))
    assert dianping["argv"][:4] == [
        __import__("sys").executable,
        "-m",
        "automation_app_dianping",
        "live",
    ]
    assert "--mode" in dianping["argv"] and "smoke" in dianping["argv"]


def test_plan_envs_do_not_cross_contaminate():
    plan = build(base_env={"PATH": "/bin", "AUTOMATION_UIA2_UDID": "a:5555"})

    assert "DIANPING_LIVE_E2E" not in plan["uia2"]["env"]
    assert "DIANPING_DRIVER" not in plan["uia2"]["env"]
    assert "AUTOMATION_UIA2_UDID" in plan["uia2"]["env"]


def test_plan_requires_at_least_one_lane():
    with pytest.raises(SystemExit, match="no lane selected"):
        build(include_dianping=False, include_uia2=False)


def test_plan_dianping_udid_override():
    plan = build(dianping_udid="OVERRIDE")

    assert plan["dianping"]["env"]["DIANPING_DEVICE_UDID"] == "OVERRIDE"


def test_aggregate_mixed_outcomes_are_not_ok():
    plan = {"run_id": "run-1"}
    summary = aggregate(
        plan,
        {
            "uia2": {"returncode": 0, "duration_s": 1.0, "log": "a.log"},
            "dianping": {"returncode": 1, "duration_s": 2.0, "log": "b.log"},
        },
    )

    assert summary["ok"] is False
    assert summary["succeeded"] == 1
    assert summary["total"] == 2
    assert summary["lanes"]["dianping"]["ok"] is False


def test_aggregate_all_green_is_ok():
    summary = aggregate(
        {"run_id": "run-1"},
        {
            "uia2": {"returncode": 0, "duration_s": 1.0, "log": "a.log"},
            "dianping": {"returncode": 0, "duration_s": 2.0, "log": "b.log"},
        },
    )

    assert summary["ok"] is True


def test_execute_plan_spawns_lanes_concurrently_and_writes_summary(tmp_path):
    lanes_started = []

    class FakeProcess:
        def __init__(self, lane):
            self._lane = lane
            self.returncode = 0

        async def communicate(self):
            lanes_started.append(self._lane)
            await asyncio.sleep(0.01)
            return b"%s ok" % self._lane.encode(), b""

    async def fake_spawn(*argv, cwd=None, env=None, stdout=None, stderr=None):
        lane = "uia2" if "live_probe_wave2" in argv[1] else "dianping"
        return FakeProcess(lane)

    plan = build(kit_root=tmp_path, dianping_repo=tmp_path / "dp")
    run_root = tmp_path / "live_artifacts" / "run-1"

    summary = asyncio.run(execute_plan(plan, run_root, spawn=fake_spawn))

    assert summary["ok"] is True
    assert set(summary["lanes"]) == {"uia2", "dianping"}
    assert len(lanes_started) == 2
    for lane in ("uia2", "dianping"):
        log_path = Path(summary["lanes"][lane]["log"])
        assert log_path.read_bytes() == b"%s ok" % lane.encode()


def test_execute_plan_failure_surfaces_returncode(tmp_path):
    class FailingProcess:
        returncode = 3

        async def communicate(self):
            return b"boom", b""

    async def fake_spawn(*argv, cwd=None, env=None, stdout=None, stderr=None):
        return FailingProcess()

    plan = build(include_dianping=False, kit_root=tmp_path)
    summary = asyncio.run(
        execute_plan(
            plan, tmp_path / "live_artifacts" / "r", spawn=fake_spawn
        )
    )

    assert summary["ok"] is False
    assert summary["lanes"]["uia2"]["returncode"] == 3


# --- review fixes 2026-11: main() E2E, cwd creation, env redaction ----------


def test_run_lane_creates_missing_cwd(tmp_path):
    """The uia2 lane cwd (live_artifacts/<run>/uia2) must be created pre-spawn."""
    import asyncio

    from scripts.live_parallel_smoke import run_lane

    spec = {
        "argv": ["echo", "hi"],
        "cwd": str(tmp_path / "fresh" / "uia2"),
        "env": {"PYTHONUNBUFFERED": "1"},
    }

    async def fake_spawn(*argv, cwd=None, env=None, stdout=None, stderr=None):
        from pathlib import Path as _P

        assert _P(cwd).is_dir(), "cwd must exist before spawn"
        assert env["PYTHONUNBUFFERED"] == "1"

        class Done:
            returncode = 0

            async def communicate(self):
                return b"hi", b""

        return Done()

    outcome = asyncio.run(run_lane("uia2", spec, tmp_path / "logs", spawn=fake_spawn))

    assert outcome["returncode"] == 0


def test_main_dry_run_redacts_inherited_env(monkeypatch, tmp_path, capsys):
    """Dry-run plan printing must never leak wholesale os.environ values."""
    from scripts import live_parallel_smoke as mod

    monkeypatch.setattr(
        mod,
        "build_lane_plan",
        lambda *a, **k: {
            "uia2": {
                "argv": ["probe"],
                "cwd": str(tmp_path / "uia2"),
                "env": {
                    "PATH": "c:/secret-path",
                    "API_TOKEN": "super-secret",
                    "AUTOMATION_UIA2_UDID": "10.144.144.52:5555",
                },
                "artifact_root": str(tmp_path / "uia2"),
            }
        },
    )

    rc = mod.main(["--run-id", "dryredact", "--uia2"])

    assert rc == 0
    out = capsys.readouterr().out
    plan = json.loads(out)
    assert plan["run_id"] == "dryredact"
    env = plan["uia2"]["env"]
    assert env["AUTOMATION_UIA2_UDID"] == "10.144.144.52:5555"
    assert env["API_TOKEN"] == "<inherited>"
    assert "super-secret" not in out
    assert env["PATH"] == "<inherited>"


def test_main_execute_runs_lanes_and_writes_summary(monkeypatch, tmp_path, capsys):
    """main() end-to-end: lanes run, summary.json lands, exit code reflects ok."""
    import sys

    from scripts import live_parallel_smoke as mod

    fake_repo = tmp_path / "dp"
    fake_repo.mkdir()
    kit_root = tmp_path / "kit"
    scripts_dir = kit_root / "scripts"
    scripts_dir.mkdir(parents=True)
    # Harmless lane stand-in: main() must spawn the REAL subprocess machinery
    # (cwd creation, teeing, summary) without touching adb/uiautomator2.
    (scripts_dir / "live_probe_wave2.py").write_text(
        "print('lane-ok')", encoding="utf-8"
    )
    monkeypatch.setattr(mod, "KIT_ROOT", kit_root)
    monkeypatch.setattr(mod, "DEFAULT_DIANPING_REPO", fake_repo)
    assert sys.executable  # real interpreter spawns the stand-in script

    rc = mod.main(
        [
            "--run-id",
            "e2e-run",
            "--uia2",
            "--uia2-udid",
            "10.144.144.52:5555",
            "--execute",
        ]
    )

    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["ok"] is True
    assert set(summary["lanes"]) == {"uia2"}
    written = json.loads(
        (tmp_path / "kit" / "live_artifacts" / "e2e-run" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert written["ok"] is True
