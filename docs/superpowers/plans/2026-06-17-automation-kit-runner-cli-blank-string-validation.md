# Runner CLI Blank String Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only explicit CLI string arguments so built-in workflow required options and runner factory inputs behave like genuinely missing values instead of dirty present values.

**Architecture:** Keep the change inside `automation_runner.cli`, where command-line arguments are merged into runner config and later validated. Add failing CLI tests first for blank `--url`, `--app-id`, `--factory`, and `--workflow-factory`, then add one tiny helper that normalizes optional CLI strings before `_merge_config(...)` performs fallback logic. Leave `automation_core` and config parsing unchanged.

**Tech Stack:** Python argparse, runner CLI helpers, pytest, existing runner docs.

---

### Task 1: Add Failing CLI Regression Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add blank built-in option regression tests**

Add these tests near the existing built-in workflow validation coverage:

```python
def test_cli_rejects_blank_explicit_url_for_builtin_workflow(capsys):
    fixtures.reset()

    exit_code = main(["run", "damai-web-smoke", "--json", "--url", "   "])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--url is required for damai-web-smoke" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_blank_explicit_app_id_for_builtin_workflow(capsys):
    fixtures.reset()

    exit_code = main(["run", "damai-android-smoke", "--json", "--app-id", "   "])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--app-id is required for damai-android-smoke" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 2: Add blank factory path regression tests**

Add these tests near the existing factory import validation coverage:

```python
def test_cli_rejects_blank_explicit_workflow_factory(capsys):
    exit_code = main(["run", "--workflow-factory", "   ", "--json"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "import path must use module:object" in captured.err


def test_cli_rejects_blank_explicit_factory_for_live_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--factory",
            "   ",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "import path must use module:object" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_for_builtin_workflow \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_for_builtin_workflow \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_workflow_factory \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_factory_for_live_workflow \
  --no-cov -q
```

Expected: fail because whitespace-only CLI values currently slip through or
fail later than intended.

### Task 2: Normalize Optional CLI String Arguments

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Add a tiny CLI string normalizer**

Add a helper like:

```python
def _optional_cli_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not value.strip():
        return None
    return value
```

Use it inside `_merge_config(...)` for:

- `factory`
- `workflow_factory`
- `url`
- `app_id`

so fallback semantics become:

```python
factory=_optional_cli_string(args.factory) or config.factory
```

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_url_for_builtin_workflow \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_app_id_for_builtin_workflow \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_workflow_factory \
  tests/runner/test_cli.py::test_cli_rejects_blank_explicit_factory_for_live_workflow \
  --no-cov -q
```

Expected: all four tests pass.

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

- [ ] **Step 1: Document CLI blank-string rejection**

Add one sentence near the runner CLI usage documentation noting that explicit
CLI values for `--factory`, `--workflow-factory`, `--url`, and `--app-id` must
contain at least one non-whitespace character.

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner CLI Blank String Validation` section to
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
git commit -m "fix: validate runner cli blank strings"
git push origin main
```
