# Report Contract Documentation Run State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the human workflow authoring guide aligned with the runner report top-level contract by documenting `run_state`.

**Architecture:** Add a focused documentation regression test in the existing report schema test module. Update only `docs/adding-a-workflow.md` and development documentation; leave report serialization, JSON schema, and `automation_core` unchanged.

**Tech Stack:** Python pathlib/string parsing, pytest, existing report schema tests.

---

### Task 1: Add Failing Documentation Contract Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_report_schema.py`

- [x] **Step 1: Add a small markdown field-list parser**

Add this helper near `_sample_report()`:

```python
def _documented_report_fields():
    content = Path("docs/adding-a-workflow.md").read_text(encoding="utf-8")
    start = content.index("JSON reports currently include:")
    end = content.index("Each artifact entry contains:", start)
    fields = []
    for line in content[start:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            fields.append(stripped.removeprefix("- `").removesuffix("`"))
    return fields
```

- [x] **Step 2: Add the regression test**

Add this test after `test_report_schema_v1_matches_current_top_level_report_contract`:

```python
def test_workflow_guide_documents_current_top_level_report_fields():
    report = _sample_report()

    assert set(_documented_report_fields()) == set(report)
```

- [x] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_workflow_guide_documents_current_top_level_report_fields --no-cov -q
```

Expected: fail because `docs/adding-a-workflow.md` omits `run_state`.

### Task 2: Update Workflow Guide Report Contract

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`

- [x] **Step 1: Add `run_state` to the top-level field list**

Insert this bullet immediately after `run_id`:

```markdown
- `run_state`
```

- [x] **Step 2: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_report_schema.py::test_workflow_guide_documents_current_top_level_report_fields --no-cov -q
```

Expected: pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Record the slice**

Append a `2026-06-17: Report Contract Run State Documentation` section to
`docs/development-log.md` with red/green results, full verification, review
summary, and the boundary note that report serialization and `automation_core`
remain unchanged.

- [x] **Step 2: Run full verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and `git diff --check` emits no output.

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify the Python review context.

- [x] **Step 4: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add tests docs
git commit -m "docs: document report run state field"
git push origin main
```
