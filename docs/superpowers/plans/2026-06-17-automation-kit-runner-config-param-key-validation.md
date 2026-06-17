# Runner Config Param Key Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject blank workflow parameter keys from runner config sources so config-backed parameters match the CLI boundary.

**Architecture:** Keep the change inside `automation_runner.config._optional_parameters(...)`, the runner-layer parser for dictionary and environment-backed workflow parameters. Add config tests first for blank keys in mapping and JSON-string inputs, then tighten the key predicate while preserving existing string-value behavior and leaving `automation_core` unchanged.

**Tech Stack:** Python dataclasses, standard-library `json`, runner config helpers, pytest.

---

### Task 1: Add Failing Blank-Key Config Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_config.py`

- [ ] **Step 1: Add blank-key regression tests**

Add these tests near the existing parameter validation coverage:

```python
def test_load_runner_config_rejects_blank_parameter_key():
    with pytest.raises(
        ValueError,
        match="config parameters expected string keys and values",
    ):
        load_runner_config(DictConfigSource({"parameters": {"   ": "value"}}))


def test_load_runner_config_rejects_blank_json_parameter_key():
    with pytest.raises(
        ValueError,
        match="config parameters expected string keys and values",
    ):
        load_runner_config(DictConfigSource({"parameters": '{"   ":"value"}'}))
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_parameter_key' --no-cov -q
```

Expected: both tests fail because whitespace-only keys are currently accepted.

### Task 2: Reject Blank Keys In Runner Config Parsing

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/config.py`

- [ ] **Step 1: Tighten `_optional_parameters(...)`**

Change the key/value validation branch from:

```python
        if not isinstance(parameter_key, str) or not isinstance(parameter_value, str):
            raise ValueError(f"config {key} expected string keys and values")
```

to:

```python
        if (
            not isinstance(parameter_key, str)
            or not parameter_key.strip()
            or not isinstance(parameter_value, str)
        ):
            raise ValueError(f"config {key} expected string keys and values")
```

Do not strip or otherwise normalize valid keys.

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py -k 'blank_parameter_key or reads_json_parameters or rejects_non_string_parameter_values' --no-cov -q
```

Expected: new blank-key tests and existing valid parameter parsing pass.

- [ ] **Step 3: Run runner regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Expected: runner tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document config-key validation**

Add one sentence near the config-backed parameter documentation:

```markdown
Config-backed workflow parameter keys must contain at least one
non-whitespace character.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner Config Param Key Validation` section to
`docs/development-log.md` with:

- focused red result,
- focused green result,
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

Expected: all tests pass and `git diff --check` has no output.

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
git commit -m "fix: validate runner config param keys"
git push origin main
```
