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

    (tmp_path / "shot.log").write_text("binary-not-previewable")
    log_report = make_report(tmp_path, artifact_path="shot.log")
    prepared = prepare_report(log_report, artifact_root=tmp_path)
    assert prepared["artifacts"][0]["state"] == "linked"

    monkeypatch.setattr("automation_runner.viewer.MAX_EMBED_BYTES", 4)
    prepared = prepare_report(report, artifact_root=tmp_path)
    assert prepared["artifacts"][0]["state"] == "oversize"


def test_render_embeds_text_artifact_as_preview(tmp_path):
    markdown = "# Device Viewport: 1080x2400\n- [@1] button: \"Login\""
    (tmp_path / "snapshot.md").write_text(markdown, encoding="utf-8")
    report = make_report(tmp_path, artifact_path="snapshot.md")

    prepared = prepare_report(report, artifact_root=tmp_path)

    assert prepared["artifacts"][0]["state"] == "embedded"
    assert prepared["artifacts"][0]["embedded"] is True
    assert prepared["artifacts"][0]["text_content"] == markdown

    html = render_report_html(report, artifact_root=tmp_path)
    assert 'class="text-preview"' in html
    # The literal markdown must survive rendering (pre-escaped in the
    # payload, decoded again by the browser).
    assert "- [@1] button:" in html


def test_text_artifact_content_is_markup_escaped(tmp_path):
    (tmp_path / "snapshot.md").write_text(
        "<script>alert(1)</script> & <b>", encoding="utf-8"
    )
    report = make_report(tmp_path, artifact_path="snapshot.md")

    prepared = prepare_report(report, artifact_root=tmp_path)

    assert prepared["artifacts"][0]["text_content"] == (
        "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;"
    )
    html = render_report_html(report, artifact_root=tmp_path)
    assert "<script>alert(1)</script>" not in html


def test_text_artifact_oversize_is_not_embedded(tmp_path, monkeypatch):
    (tmp_path / "snapshot.md").write_text("too big", encoding="utf-8")
    report = make_report(tmp_path, artifact_path="snapshot.md")
    monkeypatch.setattr("automation_runner.viewer.MAX_EMBED_BYTES", 4)

    prepared = prepare_report(report, artifact_root=tmp_path)

    assert prepared["artifacts"][0]["state"] == "oversize"
    assert prepared["artifacts"][0]["embedded"] is False
    assert prepared["artifacts"][0]["text_content"] is None


def test_text_artifact_outside_root_is_external(tmp_path):
    outside = tmp_path.parent / "outside-snapshot.md"
    outside.write_text("# leaked?", encoding="utf-8")
    try:
        report = make_report(tmp_path, artifact_path=str(outside))
        prepared = prepare_report(report, artifact_root=tmp_path / "artifacts")
        assert prepared["artifacts"][0]["state"] in {"external", "missing"}
        assert prepared["artifacts"][0]["text_content"] is None
    finally:
        outside.unlink()


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


# --- round-2 gap tests: OSError resilience + template contract --------------------


def test_resolve_skips_unresolvable_candidates(tmp_path, monkeypatch):
    """_resolve_artifact_path tolerates resolve() OSError on any candidate
    and falls through to the next candidate."""
    from automation_runner.viewer import _resolve_artifact_path

    target = tmp_path / "ok.txt"
    target.write_text("x", encoding="utf-8")

    real_resolve = Path.resolve

    def flaky_resolve(self, *args, **kwargs):
        if self.name == "bad.txt":
            raise OSError("permission denied")
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", flaky_resolve)

    resolved = _resolve_artifact_path("bad.txt", artifact_root=None)
    assert resolved is None

    resolved = _resolve_artifact_path("ok.txt", artifact_root=tmp_path)
    assert resolved == target.resolve()


def test_within_root_oserror_marks_external(tmp_path, monkeypatch):
    """An OSError while resolving the artifact root containment check
    degrades to state=external (fail-closed, no embed)."""
    from automation_runner.viewer import _artifact_entry

    img = tmp_path / "shot.png"
    img.write_bytes(PNG_BYTES)

    real_resolve = Path.resolve

    def flaky_resolve(self, *args, **kwargs):
        # Second resolve call (containment check) fails.
        if flaky_resolve.calls >= 1:
            raise OSError("root vanished")
        flaky_resolve.calls += 1
        return real_resolve(self, *args, **kwargs)

    flaky_resolve.calls = 0
    monkeypatch.setattr(Path, "resolve", flaky_resolve)

    prepared = _artifact_entry(
        {"artifact_type": "screenshot", "path": str(img)}, tmp_path
    )
    assert prepared["state"] == "external"


def test_artifact_read_oserror_keeps_missing_state(tmp_path, monkeypatch):
    """A text artifact that exists but raises OSError on read stays in the
    default missing state (no embed, no crash)."""
    from automation_runner.viewer import _artifact_entry

    note = tmp_path / "note.md"
    note.write_text("content", encoding="utf-8")

    def exploding_read_text(self, *args, **kwargs):
        raise OSError("file locked")

    monkeypatch.setattr(Path, "read_text", exploding_read_text)

    prepared = _artifact_entry(
        {"artifact_type": "log", "path": str(note)}, tmp_path
    )
    assert prepared["embedded"] is False
    assert prepared["text_content"] is None


def test_image_read_oserror_keeps_missing_state(tmp_path, monkeypatch):
    from automation_runner.viewer import _artifact_entry

    img = tmp_path / "shot.png"
    img.write_bytes(PNG_BYTES)

    def exploding_read_bytes(self, *args, **kwargs):
        raise OSError("device gone")

    monkeypatch.setattr(Path, "read_bytes", exploding_read_bytes)

    prepared = _artifact_entry(
        {"artifact_type": "screenshot", "path": str(img)}, tmp_path
    )
    assert prepared["embedded"] is False
    assert prepared["data_uri"] is None


def test_render_missing_template_placeholder_raises():
    from automation_runner import viewer as viewer_module

    report = {"schema_version": "2", "steps": [], "context": {}}

    real_read_text = viewer_module.resources.read_text

    def template_without_placeholder(*args, **kwargs):
        return "no placeholder here"

    viewer_module.resources.read_text = template_without_placeholder
    try:
        with pytest.raises(ViewerError, match="missing the data placeholder"):
            viewer_module.render_report_html(report)
    finally:
        viewer_module.resources.read_text = real_read_text


def test_default_output_path_pairs_with_report():
    from automation_runner.viewer import default_output_path

    assert default_output_path("reports/run.json").name == "run.viewer.html"


def test_load_report_missing_file_and_bad_json(tmp_path):
    with pytest.raises(ViewerError, match="could not read report file"):
        load_report(str(tmp_path / "nope.json"))

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ViewerError, match="not valid JSON"):
        load_report(str(bad))


def test_prepare_report_skips_non_dict_entries():
    report = {
        "schema_version": "2",
        "context": {"run_id": "r"},
        "steps": ["not-a-dict", {"step_id": "s1", "step_name": "open"}],
        "artifacts": ["not-a-dict", {"artifact_type": "shot", "path": "x.png"}],
        "events": [],
        "providers": [],
    }
    prepared = prepare_report(report)
    assert [s["step_id"] for s in prepared["steps"]] == ["s1"]
    # Non-dict artifact entries are skipped; the dict entry survives as a
    # state=missing artifact (file x.png does not exist here).
    assert [a["state"] for a in prepared["artifacts"]] == ["missing"]


def test_render_report_html_missing_template_resource_raises():
    """Template resource missing (FileNotFoundError branch) → ViewerError."""
    from automation_runner import viewer as viewer_module
    from importlib import resources as real_resources

    missing = viewer_module.TEMPLATE_RESOURCE

    def raising_read_text(package, resource, *args, **kwargs):
        if resource == missing:
            raise FileNotFoundError(resource)
        return real_resources.read_text(package, resource, *args, **kwargs)

    original = viewer_module.resources.read_text
    viewer_module.resources.read_text = raising_read_text
    try:
        with pytest.raises(ViewerError, match="template resource is missing"):
            viewer_module.render_report_html({"steps": []})
    finally:
        viewer_module.resources.read_text = original
