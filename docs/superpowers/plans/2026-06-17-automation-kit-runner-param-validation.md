# Runner Param Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure `automation-runner run --param` syntax is validated before workflow execution for both built-in and custom workflows.

**Architecture:** Keep validation in `automation_runner.cli`, where the CLI option is defined. Parse parameters once for every `run` command and pass the resulting `WorkflowOptions` only to custom workflow factories, preserving existing built-in workflow behavior and keeping `automation_core` business-free.

**Tech Stack:** Python argparse, existing runner config models, pytest.

---

### Task 1: Add Failing Built-In Workflow Param Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add the red test**

Add this test near the existing invalid parameter coverage:

```python
def test_cli_rejects_invalid_workflow_param_for_builtin_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
            "--param",
            "missing-equals",
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
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_for_builtin_workflow --no-cov -q
```

Expected: fail because invalid built-in workflow `--param` is currently ignored.

### Task 2: Validate Parameters Before Workflow Execution

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Parse workflow options for every run command**

In `main()`, after built-in workflow option validation and before loading a
live session factory, replace the custom-workflow-only parse block with:

```python
        try:
            options = _workflow_options(config, args)
        except ValueError as exc:
            return _print_error(str(exc))
```

Keep the later custom workflow construction using the same `options` value:

```python
                    options=options,
```

- [ ] **Step 2: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_for_builtin_workflow tests/runner/test_cli.py::test_cli_rejects_invalid_workflow_param_before_loading_factory --no-cov -q
```

Expected: both tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document validation behavior**

Add one sentence near the `--param KEY=VALUE` documentation:

```markdown
The runner validates `--param KEY=VALUE` syntax before execution even when the
selected workflow does not consume custom parameters.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner Param Validation` section to
`docs/development-log.md` with:

- red and green focused test results,
- full verification result,
- production review result,
- boundary note that `automation_core` remains untouched.

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
git add automation_runner tests docs
git commit -m "fix: validate runner params before execution"
git push origin main
```
