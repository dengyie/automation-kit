# Runner Config String Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make runner configuration reject non-string values for string fields before workflow selection, factory loading, or execution.

**Architecture:** Keep validation in `automation_runner.config`. Do not change generic config sources, CLI argparse behavior, runner report schemas, adapters, or workflow APIs.

**Tech Stack:** Python dataclasses, runner config helpers, pytest.

---

### Task 1: Add Failing Runner Config Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_config.py`

- [ ] **Step 1: Add non-string string-field validation tests**

Add these tests near the existing invalid config tests:

```python
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("factory", 123),
        ("workflow_factory", {"module": "factory"}),
        ("url", ["https://example.test"]),
        ("app_id", 42),
    ],
)
def test_load_runner_config_rejects_non_string_fields(key, value):
    with pytest.raises(ValueError, match=f"config {key} expected string"):
        load_runner_config(DictConfigSource({key: value}))
```

- [ ] **Step 2: Run red config verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py --no-cov -q
```

Expected: the new parametrized test fails because `_optional_string(...)`
currently coerces non-string values with `str(value)`.

### Task 2: Add Failing CLI Boundary Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add invalid config factory CLI test**

Add this test near the config-backed runner tests:

```python
def test_cli_rejects_non_string_config_factory_before_loading_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--url",
            "https://example.test/damai",
        ],
        config_source=DictConfigSource({"factory": 123}),
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "config factory expected string" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 2: Run red CLI verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_non_string_config_factory_before_loading_factory --no-cov -q
```

Expected: the test fails because the current config loader coerces `123` to
`"123"` and the CLI reports a later import-path error.

### Task 3: Implement String Field Validation

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/config.py`

- [ ] **Step 1: Tighten `_optional_string(...)`**

Replace `_optional_string(...)` with:

```python
def _optional_string(source: ConfigSource, key: str) -> Optional[str]:
    value = source.get(key, default=None).value
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"config {key} expected string")
    return value
```

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_config.py tests/runner/test_cli.py::test_cli_rejects_non_string_config_factory_before_loading_factory --no-cov -q
```

Expected: config tests and the new CLI boundary test pass.

- [ ] **Step 3: Run runner regression tests**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner --no-cov -q
```

Expected: all runner tests pass.

### Task 4: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document config type expectations**

Add a short note to the runner configuration docs:

```markdown
Dictionary-backed runner config must provide string values for `factory`,
`workflow_factory`, `url`, and `app_id`; invalid types fail before factories are
loaded.
```

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

Append a `2026-06-17: Runner Config String Validation` section to
`docs/development-log.md` with:

- red and green focused test results,
- runner regression result,
- full suite result,
- production review result,
- boundary note that `automation_core` remains generic.

- [ ] **Step 5: Commit and push**

Run:

```bash
git add automation_runner tests README.md docs
git commit -m "fix: validate runner config string fields"
git push origin main
```
