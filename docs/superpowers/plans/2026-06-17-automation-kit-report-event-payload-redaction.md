# Report Event Payload Redaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redact common sensitive keys inside runner report event payloads before JSON serialization.

**Architecture:** Keep event payload redaction in `automation_runner.reports`, next to existing report-safe action, batch, artifact, and metadata serialization. `automation_core.events` remains a generic event model package and does not learn report security policy.

**Tech Stack:** Python report serialization helpers, `EventEnvelope`, pytest.

---

### Task 1: Add Failing Report Redaction Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_reports.py`

- [x] **Step 1: Import `EventEnvelope`**

Update the event import:

```python
from automation_core.events import EventEnvelope, TaskStartEvent
```

- [x] **Step 2: Add event payload redaction coverage**

Add this test near the existing event serialization test:

```python
def test_build_report_redacts_sensitive_event_payload_fields():
    result = ExampleWorkflowResult(
        session=SessionInfo(
            driver_name="fake",
            platform="web",
            identifier="run-1",
        ),
        success=False,
        actions=[],
        artifacts=[],
        events=[
            EventEnvelope(
                event_type="error",
                task_id="run-1",
                payload={
                    "task_name": "checkout",
                    "auth_token": "secret-token",
                    "details": {
                        "cookie": "session=abc",
                        "attempt": 1,
                    },
                    "attempts": [
                        {
                            "password": "secret",
                            "status": "failed",
                        }
                    ],
                },
            )
        ],
    )

    report = build_report("damai-web-smoke", result).to_dict()

    assert report["events"][0]["payload"] == {
        "task_name": "checkout",
        "auth_token": "[redacted]",
        "details": {
            "cookie": "[redacted]",
            "attempt": 1,
        },
        "attempts": [
            {
                "password": "[redacted]",
                "status": "failed",
            }
        ],
    }
```

- [x] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
```

Expected: the new event payload redaction test fails because event payloads are currently serialized unchanged.

### Task 2: Implement Report Payload Redaction

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/reports.py`

- [x] **Step 1: Add `Any` to report typing imports**

Replace:

```python
from typing import Dict, List, Optional
```

with:

```python
from typing import Any, Dict, List, Optional
```

- [x] **Step 2: Add recursive sensitive-value redaction helper**

Add this helper near `_serialize_metadata(...)`:

```python
def _redact_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        safe_value = {}
        for key, nested_value in value.items():
            lowered = str(key).lower()
            if any(term in lowered for term in SENSITIVE_REPORT_KEY_TERMS):
                safe_value[key] = "[redacted]"
            else:
                safe_value[key] = _redact_sensitive_values(nested_value)
        return safe_value
    if isinstance(value, list):
        return [_redact_sensitive_values(item) for item in value]
    return value
```

- [x] **Step 3: Reuse the helper for artifact metadata**

Replace `_serialize_metadata(...)` with:

```python
def _serialize_metadata(metadata: Dict[str, str]) -> Dict[str, str]:
    return _redact_sensitive_values(metadata)
```

- [x] **Step 4: Add event serialization helper**

Add:

```python
def _serialize_events(events) -> List[Dict[str, object]]:
    serialized_events = []
    for envelope in events:
        event = envelope.to_dict()
        event["payload"] = _redact_sensitive_values(event["payload"])
        serialized_events.append(event)
    return serialized_events
```

- [x] **Step 5: Use event serialization in `build_report(...)`**

Replace:

```python
        events=[envelope.to_dict() for envelope in result.events],
```

with:

```python
        events=_serialize_events(result.events),
```

- [x] **Step 6: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_reports.py --no-cov -q
```

Expected: all report serialization tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document event payload redaction**

Add this note near the artifact/report attachment rules:

```markdown
Report serialization also redacts common sensitive keys in event payloads before
writing JSON to stdout or report files.
```

- [x] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: full tests pass and `git diff --check` emits no output.

- [x] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify Python stack review context.

- [x] **Step 4: Record the slice**

Append a `2026-06-17: Report Event Payload Redaction` section to
`docs/development-log.md` with:

- red and green focused test results,
- full suite result,
- production review result,
- boundary note that `automation_core.events` remains unchanged.

- [x] **Step 5: Commit and push**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_runner tests docs
git commit -m "fix: redact sensitive event payload fields"
git push origin main
```
