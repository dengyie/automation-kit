# Runner Report Schema CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose runner report schema version `"1"` through `automation-runner report-schema --version 1`.

**Architecture:** Keep schema discovery in the `automation_runner` layer by adding a package resource and small loader. Keep `docs/report-schema-v1.json` as the public documentation copy, and test parity so the packaged schema and docs cannot drift.

**Tech Stack:** Python standard-library `argparse`, `json`, `importlib.resources`, pytest, existing runner CLI tests.

---

## Task 1: Add Failing Schema Loader And CLI Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_report_schema.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Add loader import and schema resource tests**

In `tests/runner/test_report_schema.py`, add:

```python
import pytest

from automation_runner.schemas import load_report_schema
```

Add tests:

```python
def test_packaged_report_schema_matches_docs_schema():
    assert load_report_schema("1") == _load_schema()


def test_unknown_report_schema_version_raises_clear_error():
    with pytest.raises(ValueError, match="unsupported report schema version: 2"):
        load_report_schema("2")
```

- [x] **Step 2: Add CLI schema tests**

In `tests/runner/test_cli.py`, add:

```python
def test_cli_prints_report_schema_v1(capsys):
    exit_code = main(["report-schema", "--version", "1"])

    captured = capsys.readouterr()
    schema = json.loads(captured.out)

    assert exit_code == 0
    assert schema["title"] == "Automation Kit Runner Report v1"
    assert schema["properties"]["schema_version"]["const"] == "1"
    assert captured.err == ""


def test_cli_rejects_unknown_report_schema_version(capsys):
    exit_code = main(["report-schema", "--version", "2"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "unsupported report schema version: 2" in captured.err
```

- [x] **Step 3: Run red focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py tests/runner/test_cli.py::test_cli_prints_report_schema_v1 tests/runner/test_cli.py::test_cli_rejects_unknown_report_schema_version --no-cov -q
```

Expected: fail because `automation_runner.schemas` and the `report-schema`
command do not exist yet.

## Task 2: Add Packaged Schema Loader And CLI Command

**Files:**

- Create: `/Users/mango/project/codex/automation-kit/automation_runner/schemas/__init__.py`
- Create: `/Users/mango/project/codex/automation-kit/automation_runner/schemas/report-schema-v1.json`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Add `automation_runner.schemas` loader**

Create `automation_runner/schemas/__init__.py`:

```python
import json
from importlib import resources
from typing import Dict


REPORT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_RESOURCE = "report-schema-v1.json"


def load_report_schema(version: str = REPORT_SCHEMA_VERSION) -> Dict[str, object]:
    if version != REPORT_SCHEMA_VERSION:
        raise ValueError(f"unsupported report schema version: {version}")
    schema_text = resources.files(__package__).joinpath(REPORT_SCHEMA_RESOURCE).read_text(
        encoding="utf-8"
    )
    return json.loads(schema_text)
```

- [x] **Step 2: Copy the v1 schema resource**

Copy the exact contents of `docs/report-schema-v1.json` into
`automation_runner/schemas/report-schema-v1.json`.

- [x] **Step 3: Add `report-schema` parser**

In `automation_runner/cli.py`, import `load_report_schema` and add:

```python
    report_schema = subparsers.add_parser(
        "report-schema",
        help="print runner report JSON schema",
    )
    report_schema.add_argument(
        "--version",
        default="1",
        help="runner report schema version",
    )
```

- [x] **Step 4: Add command handling**

Before the `run` command branch in `main(...)`, add:

```python
    if args.command == "report-schema":
        try:
            schema = load_report_schema(args.version)
        except ValueError as exc:
            return _print_error(str(exc))
        print(json.dumps(schema, sort_keys=True))
        return 0
```

- [x] **Step 5: Run green focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py tests/runner/test_cli.py::test_cli_prints_report_schema_v1 tests/runner/test_cli.py::test_cli_rejects_unknown_report_schema_version --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document CLI schema discovery**

In `README.md`, add the command:

```bash
automation-runner report-schema --version 1
```

Near existing report schema text, explain that this prints the packaged
machine-readable report contract.

- [x] **Step 2: Document the command in workflow guide**

In `docs/adding-a-workflow.md`, extend the report schema paragraph to mention
`automation-runner report-schema --version 1`.

- [x] **Step 3: Record the development log**

Add a new `## 2026-06-16: Runner Report Schema CLI` section to
`docs/development-log.md` with completed work, red/green focused test results,
full verification, production review scripts, and layer-boundary notes.

- [x] **Step 4: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and diff check reports no whitespace errors.

- [x] **Step 5: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and no unresolved P0/P1/P2 findings remain.

- [ ] **Step 6: Commit and push**

```bash
git add automation_runner tests README.md docs
git commit -m "feat: expose runner report schema"
git push origin main
```
