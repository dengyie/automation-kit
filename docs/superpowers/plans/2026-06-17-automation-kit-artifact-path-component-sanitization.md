# Artifact Path Component Sanitization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent artifact paths from escaping the artifact root when `run_id` or `artifact_type` contains path-like input.

**Architecture:** Keep the fix in `automation_core.artifacts.store`. Reuse one path-component sanitizer for `run_id`, `artifact_type`, and artifact names, with field-specific error messages. Do not change adapters, runner reports, report schemas, or workflow APIs.

**Tech Stack:** Python pathlib, dataclasses, pytest.

---

### Task 1: Add Failing Artifact Path Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/artifacts/test_store.py`

- [ ] **Step 1: Add path-like component normalization test**

Add this test near the existing path-building tests:

```python
def test_artifact_store_sanitizes_run_and_type_components():
    store = ArtifactStore(Path("/artifacts"))

    path = store.build_path(
        "../run 42",
        "../page source",
        "../startup.xml",
    )

    assert str(path) == "/artifacts/run_42/page_source/startup.xml"
```

- [ ] **Step 2: Add invalid component rejection tests**

Add these tests near `test_artifact_store_rejects_invalid_name`:

```python
def test_artifact_store_rejects_invalid_run_id():
    store = ArtifactStore(Path("/artifacts"))

    with pytest.raises(ValueError, match="invalid run_id"):
        store.build_path("..", "screenshot", "home.png")


def test_artifact_store_rejects_invalid_artifact_type():
    store = ArtifactStore(Path("/artifacts"))

    with pytest.raises(ValueError, match="invalid artifact_type"):
        store.build_path("run-1", "..", "home.png")
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/artifacts/test_store.py --no-cov -q
```

Expected: the new normalization test fails because `run_id` and `artifact_type`
are not sanitized yet, and the invalid component tests fail because the current
implementation does not reject those fields.

### Task 2: Implement Shared Component Sanitization

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/artifacts/store.py`

- [ ] **Step 1: Replace name-only sanitizer with component sanitizer**

Replace `_sanitize_name(...)` with:

```python
    def _sanitize_component(self, value: str, field_name: str) -> str:
        cleaned = value.replace("\\", "/").split("/")[-1].strip()
        if cleaned in {"", ".", ".."}:
            raise ValueError(f"invalid {field_name}")
        return cleaned.replace(" ", "_")
```

- [ ] **Step 2: Sanitize all path components in `build_path(...)`**

Replace the body of `build_path(...)` with:

```python
    def build_path(self, run_id: str, artifact_type: str, name: str) -> Path:
        safe_run_id = self._sanitize_component(run_id, "run_id")
        safe_artifact_type = self._sanitize_component(
            artifact_type,
            "artifact_type",
        )
        safe_name = self._sanitize_component(name, "artifact name")
        return self.root / safe_run_id / safe_artifact_type / safe_name
```

- [ ] **Step 3: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/artifacts/test_store.py --no-cov -q
```

Expected: all artifact store tests pass.

- [ ] **Step 4: Run adapter artifact regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/adapters/selenium/test_session.py tests/adapters/appium/test_session.py tests/drivers/test_contracts.py --no-cov -q
```

Expected: adapter and driver contract tests pass, proving existing adapter
artifact paths still use the shared store successfully.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/artifacts.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document all path components**

Update the naming rules in `docs/artifacts.md` to say that `run_id`,
`artifact_type`, and artifact names are all treated as single path components,
path-like values are reduced to the final segment, invalid empty/`.`/`..`
components are rejected, and spaces are normalized to `_`.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: full tests pass and `git diff --check` emits no output.

- [ ] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify Python stack review context.

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Artifact Path Component Sanitization` section to
`docs/development-log.md` with:

- red and green focused test results,
- adapter regression result,
- full suite result,
- production review result,
- boundary note that `automation_core` remains business-agnostic.

- [ ] **Step 5: Commit and push**

Run:

```bash
git add automation_core tests docs
git commit -m "fix: sanitize artifact path components"
git push origin main
```
