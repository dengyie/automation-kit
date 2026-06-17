# Runner Report Contract Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock schema version `"1"` report contract consistency across emitted reports, packaged schema, and public docs without changing the runtime report payload shape.

**Architecture:** Keep the runtime report serializer unchanged in `automation_runner.reports`. Add report-schema tests that compare a real sample report against both report documentation files, then update `docs/artifacts.md` so its artifact-entry contract matches the already-emitted JSON and documented schema. Leave `automation_core` untouched.

**Tech Stack:** Python standard-library `json`, pytest, markdown text parsing via existing test helpers, runner report dataclasses.

---

### Task 1: Add Failing Artifact Contract Doc Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_report_schema.py`

- [ ] **Step 1: Add artifact contract doc parsing helpers**

Add helpers that read `docs/artifacts.md` and extract the documented artifact
report-entry fields from the `## Report Attachment` section.

Use a shape like:

```python
def _documented_artifact_report_fields():
    content = Path("docs/artifacts.md").read_text(encoding="utf-8")
    start = content.index("Runner reports serialize only:")
    end = content.index("Raw bytes", start)
    fields = []
    for line in content[start:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            fields.append(stripped.removeprefix("- `").removesuffix("`"))
    return fields
```

- [ ] **Step 2: Add failing artifact contract doc tests**

Add tests like:

```python
def test_artifact_guide_documents_current_artifact_report_fields():
    artifact_entry = _sample_report()["artifacts"][0]

    assert set(_documented_artifact_report_fields()) == set(artifact_entry)


def test_artifact_guide_documents_metadata_safety_rules():
    content = Path("docs/artifacts.md").read_text(encoding="utf-8")

    assert "metadata" in content
    assert "redacts sensitive metadata keys" in content
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest \
  tests/runner/test_report_schema.py::test_artifact_guide_documents_current_artifact_report_fields \
  tests/runner/test_report_schema.py::test_artifact_guide_documents_metadata_safety_rules \
  --no-cov -q
```

Expected: fail because `docs/artifacts.md` still omits `metadata` from the
artifact report-entry contract and does not describe metadata redaction.

### Task 2: Align Artifact Docs With The Existing Report Contract

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/docs/artifacts.md`

- [ ] **Step 1: Update artifact report-entry prose**

In `## Report Attachment`, change the documented runner report artifact entry
fields from:

```markdown
- `artifact_type`
- `path`
```

to:

```markdown
- `artifact_type`
- `path`
- `metadata`
```

Also add brief prose that:

- artifact metadata should remain generic and small,
- sensitive metadata keys are redacted in runner JSON reports.

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_report_schema.py --no-cov -q
```

Expected: report-schema tests pass.

- [ ] **Step 3: Run runner regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Expected: runner tests pass unchanged.

### Task 3: Verification, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Record the slice**

Append a `2026-06-17: Runner Report Contract Consistency` section to
`docs/development-log.md` with:

- completed changes,
- focused red/green test results,
- runner regression result,
- full-suite result,
- production review notes,
- confirmation that `automation_core` stayed unchanged.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Commit and push**

Run:

```bash
git add docs tests
git commit -m "docs: align runner report artifact contract"
git push origin main
```
