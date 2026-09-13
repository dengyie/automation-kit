import json
from pathlib import Path

import pytest

from automation_runner import cli
from automation_runner.viewer import (
    ViewerError,
    load_report,
    prepare_report,
    render_report_html,
)


PNG_BYTES = b"\x89PNG-fake-image-data"


def make_report(tmp_path, *, artifact_path="shot.png", status="failed"):
    (tmp_path / "shot.png").write_bytes(PNG_BYTES)
    return {
        "schema_version": "2",
        "context": {
            "run_id": "run-1",
            "workflow_name": "damai-web-smoke",
            "correlation_id": "trace-1",
        },
        "status": status,
        "success": status == "succeeded",
        "steps": [
            {
                "step_id": "step-1",
                "step_name": "open",
                "kind": "action",
                "status": "failed",
                "attempts": 1,
                "duration_ms": 12,
                "error": {
                    "category": "BUSINESS",
                    "code": "action_failed",
                    "message": "open failed",
                },
                "artifact_result": None,
            },
            {
                "step_id": "step-1-onfailure-1",
                "step_name": "screenshot",
                "kind": "artifact",
                "status": "succeeded",
                "attempts": 1,
                "duration_ms": 5,
                "artifact_result": {
                    "artifact_type": "screenshot",
                    "path": str(artifact_path),
                },
            },
        ],
        "events": [{"event_id": "run-1:workflow.start", "event_type": "workflow.start"}],
        "artifacts": [
            {
                "artifact_type": "screenshot",
                "path": str(artifact_path),
                "metadata": {},
            }
        ],
        "failure": {"category": "BUSINESS", "code": "action_failed"},
        "providers": [],
    }


def test_render_embeds_existing_image_artifact(tmp_path):
    report = make_report(tmp_path)

    html = render_report_html(report, artifact_root=tmp_path)

    assert "run-1" in html
    assert "damai-web-smoke" in html
    assert "data:image/png;base64," in html
    assert "__REPORT_DATA__" not in html


def test_render_state_transitions(tmp_path, monkeypatch):
    report = make_report(tmp_path)
    prepared = prepare_report(report, artifact_root=tmp_path)

    assert prepared["artifacts"][0]["state"] == "embedded"

    (tmp_path / "shot.png").unlink()
    prepared = prepare_report(report, artifact_root=tmp_path)
    assert prepared["artifacts"][0]["state"] == "missing"

    (tmp_path / "shot.xml").write_text("<xml/>")
    xml_report = make_report(tmp_path, artifact_path="shot.xml")
    prepared = prepare_report(xml_report, artifact_root=tmp_path)
    assert prepared["artifacts"][0]["state"] == "linked"

    monkeypatch.setattr("automation_runner.viewer.MAX_EMBED_BYTES", 4)
    prepared = prepare_report(report, artifact_root=tmp_path)
    assert prepared["artifacts"][0]["state"] == "oversize"


def test_render_marks_paths_outside_artifact_root_external(tmp_path):
    outside = tmp_path.parent / "outside-shot.png"
    outside.write_bytes(PNG_BYTES)
    try:
        report = make_report(tmp_path, artifact_path=str(outside))
        prepared = prepare_report(report, artifact_root=tmp_path / "artifacts")
        # The file resolves on disk but is outside the declared root; it must
        # not be silently embedded.
        assert prepared["artifacts"][0]["state"] in {"external", "missing"}
        assert prepared["artifacts"][0]["embedded"] is False
    finally:
        outside.unlink()


def test_artifact_root_candidate_beats_cwd_shadow(tmp_path, monkeypatch):
    """A same-named file in CWD must not shadow the artifact root copy."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "shot.png").write_bytes(b"shadowed-from-cwd")
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "shot.png").write_bytes(PNG_BYTES)
    monkeypatch.chdir(cwd)
    try:
        report = make_report(tmp_path, artifact_path="shot.png")
        prepared = prepare_report(report, artifact_root=root)
        assert prepared["artifacts"][0]["state"] == "embedded"
        assert "data:image/png;base64," in render_report_html(
            report, artifact_root=root
        )
    finally:
        monkeypatch.chdir(tmp_path)


def test_render_escapes_script_breakout(tmp_path):
    report = make_report(tmp_path)
    report["steps"][0]["step_name"] = "</script><script>alert(1)</script>"

    html = render_report_html(report, artifact_root=tmp_path)

    assert "</script><script>alert(1)</script>" not in html.split("report-data")[1].split("</script>")[0]


def test_load_report_rejects_invalid_documents(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json", encoding="utf-8")
    with pytest.raises(ViewerError):
        load_report(str(bad_json))

    not_report = tmp_path / "not-report.json"
    not_report.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ViewerError):
        load_report(str(not_report))


def test_cli_report_view_writes_html(tmp_path, capsys):
    report = make_report(tmp_path, status="succeeded")
    report_file = tmp_path / "report.json"
    report_file.write_text(json.dumps(report), encoding="utf-8")
    output = tmp_path / "out" / "viewer.html"

    exit_code = cli.main(
        ["report-view", str(report_file), "--artifact-root", str(tmp_path),
         "--output", str(output)]
    )

    assert exit_code == 0
    assert output.is_file()
    assert "damai-web-smoke" in output.read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == str(output)


def test_cli_report_view_errors(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    assert cli.main(["report-view", str(bad)]) == 2

    good_json = tmp_path / "not-report.json"
    good_json.write_text('{"hello": 1}', encoding="utf-8")
    assert cli.main(["report-view", str(good_json)]) == 2
