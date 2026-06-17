# Runner Param Key Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject blank `--param` keys so custom workflows never receive whitespace-only parameter names from the CLI.

**Architecture:** Keep the change inside `automation_runner.cli._parse_parameters(...)`, the existing runner-layer parser for `--param KEY=VALUE`. Add CLI tests first for blank and whitespace-only keys, then tighten the key predicate while preserving existing value behavior and leaving `automation_core` unchanged.

**Tech Stack:** Python argparse, existing runner CLI helpers, pytest.

---

### Task 1: Add Failing Blank-Key Param Tests

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add the whitespace-key regression tests**

Add these tests near the existing invalid parameter coverage:

```python
def test_cli_rejects_blank_workflow_param_key(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_context_workflow",
            "--json",
            "--param",
            "   =value",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--param must use KEY=VALUE" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_tab_only_workflow_param_key(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_context_workflow",
            "--json",
            "--param",
            "\t=value",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--param must use KEY=VALUE" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'blank_workflow_param_key or tab_only_workflow_param_key' --no-cov -q
```

Expected: both tests fail because whitespace-only keys are currently accepted.

### Task 2: Reject Blank Keys In The Parser

**Files:**
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Tighten `_parse_parameters(...)`**

Change the key validation branch from:

```python
        if not separator or not key:
            raise ValueError("--param must use KEY=VALUE")
```

to:

```python
        if not separator or not key.strip():
            raise ValueError("--param must use KEY=VALUE")
```

Do not strip or otherwise normalize valid keys.

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'blank_workflow_param_key or tab_only_workflow_param_key or passes_context_and_options_to_custom_workflow_factory or param_overrides_config_parameters' --no-cov -q
```

Expected: new blank-key tests and existing valid parameter behavior pass.

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

- [ ] **Step 1: Document key validation**

Add one sentence near the `--param KEY=VALUE` documentation:

```markdown
The `KEY` portion must contain at least one non-whitespace character.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner Param Key Validation` section to
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
git commit -m "fix: validate runner param keys"
git push origin main
```
