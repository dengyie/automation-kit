# Report File Write Failure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make report-file write failures produce a clean CLI error instead of partial JSON stdout plus an unhandled traceback.

**Architecture:** Keep the behavior in `automation_runner.cli`. Change report emission so the file is written before stdout when `--report-file` is present, and catch filesystem write errors at the CLI boundary using the existing `_print_error(...)` path.

**Tech Stack:** Python pathlib, argparse-style CLI return codes, pytest.

---

### Task 1: Add Failing Report-File Write Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add a blocked parent-path regression test**

Add this test near the existing report-file tests:

```python
def test_cli_handles_report_file_write_failure_without_partial_stdout(
    tmp_path,
    capsys,
):
    fixtures.reset()
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(blocked_parent / "report.json"),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "could not write report file" in captured.err
    assert "Traceback" not in captured.err
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_handles_report_file_write_failure_without_partial_stdout --no-cov -q
```

Expected: the test fails because the current implementation prints JSON before
the failing write and does not convert the filesystem exception into a clean
CLI error.

### Task 2: Implement Clean Report-File Write Failure Handling

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Split payload, file write, and stdout helpers**

Replace `_emit_json_report(...)` with small helpers so filesystem errors can
be handled separately from stdout errors:

```python
def _json_report_payload(report) -> str:
    return json.dumps(report.to_dict(), sort_keys=True) + "\n"


def _write_json_report_file(report_file: str, payload: str) -> None:
    report_path = Path(report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")


def _emit_json_report_payload(payload: str) -> None:
    print(payload, end="")


def _emit_json_report(report) -> None:
    _emit_json_report_payload(_json_report_payload(report))
```

- [ ] **Step 2: Catch filesystem write errors in the CLI**

Update the JSON reporting block in `main(...)`:

```python
        if config.emit_json:
            report = build_report(
                workflow_name,
                result,
                run_state=run_state,
                live=config.live,
                workflow_factory=config.workflow_factory,
                session_factory=config.factory if config.live else None,
                workflow_context=context if config.workflow_factory else None,
                elapsed_seconds=elapsed_seconds,
            )
            if args.report_file:
                payload = _json_report_payload(report)
                try:
                    _write_json_report_file(args.report_file, payload)
                except OSError as exc:
                    return _print_error(
                        f"could not write report file {args.report_file}: {exc}"
                    )
                _emit_json_report_payload(payload)
            else:
                _emit_json_report(report)
            return 0 if result.success else 1
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_handles_report_file_write_failure_without_partial_stdout --no-cov -q
```

Expected: `1 passed`.

- [ ] **Step 4: Run report-file regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_can_write_json_report_to_file tests/runner/test_cli.py::test_cli_can_write_report_file_when_json_comes_from_config tests/runner/test_cli.py::test_cli_emits_json_report_when_workflow_fails tests/runner/test_cli.py::test_cli_emits_json_report_when_session_factory_fails tests/runner/test_cli.py::test_cli_creates_report_file_parent_directories tests/runner/test_cli.py::test_cli_rejects_report_file_without_json --no-cov -q
```

Expected: all listed tests pass and stdout/file parity remains unchanged.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the report-file failure contract**

Add this bullet under "Artifact And Report Attachments":

```markdown
- If the report file cannot be written, the CLI returns an error and does not
  emit partial JSON stdout for that run.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Report File Write Failure Handling` section to
`docs/development-log.md` with:

- red and green focused test results,
- report-file regression test result,
- full verification result,
- production review result,
- boundary note that `automation_core` remains untouched.

- [ ] **Step 3: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 4: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 5: Commit and push**

Run:

```bash
git add automation_runner tests docs
git commit -m "fix: handle report file write failures"
git push origin main
```
