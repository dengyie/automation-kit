# Runner Report JSON Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a machine-readable JSON Schema document for runner report schema version `"1"`.

**Architecture:** Keep the schema as documentation under `docs/report-schema-v1.json`. Use tests to pin the schema to the current `automation_runner.reports.build_report(...)` output without adding a runtime JSON Schema dependency or changing `automation_core`.

**Tech Stack:** Python standard-library `json`, pytest, existing runner report fixtures and dataclasses, JSON Schema draft 2020-12 document syntax.

---

## Task 1: Add Failing Schema Contract Tests

**Files:**

- Create: `/Users/mango/project/codex/automation-kit/tests/runner/test_report_schema.py`

- [x] **Step 1: Add schema contract tests**

Create `tests/runner/test_report_schema.py` with:

```python
import json
from pathlib import Path

from automation_core.actions import ActionBatchResult, ActionRequest
from automation_core.drivers import ActionResult, ArtifactHandle, SessionInfo
from automation_core.events import TaskStartEvent
from automation_core.state import RunState
from automation_runner.context import WorkflowContext
from automation_runner.reports import build_report
from examples.workflows import ExampleWorkflowResult


SCHEMA_PATH = Path("docs/report-schema-v1.json")


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sample_report():
    run_state = RunState(run_id="run-1", started_at=1.25)
    run_state.succeed(finished_at=2.5)
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=True,
        actions=[
            ActionResult(success=True, message="open"),
        ],
        artifacts=[
            ArtifactHandle(
                artifact_type="screenshot",
                path=Path("artifacts/run-1/screenshot/home.png"),
                metadata={"source": "driver"},
            ),
        ],
        events=[
            TaskStartEvent(
                task_name="damai-web-smoke",
                task_id="run-1",
            ).to_envelope()
        ],
        batch_result=ActionBatchResult(
            results=[
                ActionResult(success=True, message="open"),
            ],
            skipped=[
                ActionRequest(name="click_buy"),
            ],
        ),
    )
    return build_report(
        "damai-web-smoke",
        result,
        run_state=run_state,
        live=True,
        workflow_factory="pkg:create_workflow",
        session_factory="pkg:create_session",
        workflow_context=WorkflowContext(
            workflow_name="damai-web-smoke",
            live=True,
            workflow_factory="pkg:create_workflow",
            session_factory="pkg:create_session",
        ),
        elapsed_seconds=0.5,
    ).to_dict()


def test_report_schema_v1_matches_current_top_level_report_contract():
    schema = _load_schema()
    report = _sample_report()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "Automation Kit Runner Report v1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "1"
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)


def test_report_schema_v1_documents_safe_nested_report_sections():
    schema = _load_schema()
    properties = schema["properties"]

    assert properties["session"]["required"] == [
        "driver_name",
        "platform",
        "identifier",
    ]
    assert properties["run_state"]["required"] == [
        "run_id",
        "status",
        "started_at",
        "finished_at",
        "outcome",
    ]
    assert properties["actions"]["items"]["required"] == [
        "success",
        "message",
    ]
    assert "data" not in properties["actions"]["items"]["properties"]
    assert properties["artifacts"]["items"]["required"] == [
        "artifact_type",
        "path",
        "metadata",
    ]
    action_batch_schema = properties["action_batch"]["anyOf"][1]
    assert action_batch_schema["required"] == [
        "results",
        "skipped",
        "success",
    ]
    assert "parameters" not in action_batch_schema["properties"]["skipped"]["items"]["properties"]
```

- [x] **Step 2: Run red focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Expected: fail with `FileNotFoundError` for `docs/report-schema-v1.json`.

## Task 2: Add Runner Report JSON Schema

**Files:**

- Create: `/Users/mango/project/codex/automation-kit/docs/report-schema-v1.json`

- [x] **Step 1: Add `docs/report-schema-v1.json`**

Create a JSON Schema draft 2020-12 document that:

- fixes `schema_version` with `"const": "1"`;
- lists all current top-level report keys in `required`;
- sets top-level `"additionalProperties": false`;
- describes nullable fields with `["string", "null"]` or `["number", "null"]`;
- documents nested safe fields for `workflow_context`, `run_state`, `session`,
  `actions`, `action_batch`, and `artifacts`;
- keeps `events.items.payload` and `artifacts.items.metadata` extensible.

- [x] **Step 2: Run green focused tests**

```bash
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Link the schema from workflow docs**

In `docs/adding-a-workflow.md`, add a short sentence under the report
contract explaining that `docs/report-schema-v1.json` is the machine-readable
contract for `schema_version == "1"`.

- [x] **Step 2: Link the schema from README**

In `README.md`, mention the report schema next to the existing
`docs/adding-a-workflow.md` and `docs/artifacts.md` references.

- [x] **Step 3: Record the development log**

Add a new `## 2026-06-16: Runner Report JSON Schema` section to
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
git add README.md docs tests
git commit -m "docs: add runner report schema"
git push origin main
```
