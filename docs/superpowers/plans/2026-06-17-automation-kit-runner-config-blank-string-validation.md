# Runner Config Blank String Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only config strings for runner fields so config-backed runtime inputs behave like missing values instead of dirty present values.

**Architecture:** Keep the change inside `automation_runner.config._optional_string(...)`, the runner-layer parser for optional string config fields. Add config tests first for blank strings across the supported runtime keys, then tighten the parser with one stripped-emptiness check. Add one CLI regression test proving a blank config `url` does not satisfy the built-in workflow requirement. Leave `automation_core` unchanged.

**Tech Stack:** Python dataclasses, runner config helpers, existing CLI tests, pytest.

---

### Task 1: Add Failing Blank-String Config Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_config.py`

- [ ] **Step 1: Add parameterized blank-string config tests**

Add this test near the existing non-string field coverage:

```python
@pytest.mark.parametrize(
    "key",
    ["factory", "workflow_factory", "url", "app_id"],
)
def test_load_runner_config_rejects_blank_string_fields(key):
    with pytest.raises(ValueError, match=f"config {key} expected string"):
        load_runner_config(DictConfigSource({key: "   "}))
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_string_fields' --no-cov -q
```

Expected: fail because whitespace-only strings are currently accepted.

### Task 2: Add A CLI Regression For Blank Config URL

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add the blank-config-url regression test**

Add this test near the existing built-in workflow validation coverage:

```python
def test_cli_rejects_blank_config_url_for_builtin_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        ["run", "damai-web-smoke"],
        config_source=DictConfigSource(
            {
                "json": "true",
                "url": "   ",
            }
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--url is required for damai-web-smoke" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_config_url_for_builtin_workflow --no-cov -q
```

Expected: fail because the blank config string currently counts as a present
`url`.

### Task 3: Tighten Optional String Parsing

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/config.py`

- [ ] **Step 1: Update `_optional_string(...)`**

Change the string branch from:

```python
    if not isinstance(value, str):
        raise ValueError(f"config {key} expected string")
    return value
```

to:

```python
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config {key} expected string")
    return value
```

Leave `None` handling unchanged.

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_string_fields or reads_runtime_values or rejects_non_string_fields' --no-cov -q
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_blank_config_url_for_builtin_workflow --no-cov -q
```

Expected: new tests pass.

- [ ] **Step 3: Run runner regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Expected: runner tests pass.

### Task 4: Documentation, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document blank-string rejection**

Add one sentence near the config field documentation:

```markdown
Config-backed `factory`, `workflow_factory`, `url`, and `app_id` values must
contain at least one non-whitespace character.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner Config Blank String Validation` section to
`docs/development-log.md` with:

- focused red results,
- focused green results,
- runner regression result,
- full-suite result,
- production review notes,
- confirmation that `automation_core` stays unchanged.

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
git add automation_runner tests README.md docs
git commit -m "fix: validate runner config blank strings"
git push origin main
```
