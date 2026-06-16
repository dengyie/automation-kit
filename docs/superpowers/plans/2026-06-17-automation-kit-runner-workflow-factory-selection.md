# Runner Workflow Factory Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure `automation-runner run` uses an unambiguous workflow source by rejecting explicit built-in/custom conflicts and honoring positional workflow CLI precedence over configured custom factories.

**Architecture:** Keep the selection rule in `automation_runner.cli`. Add a small helper that resolves the merged `RunnerConfig` after argument parsing, rejects explicit conflicts, and clears config-provided `workflow_factory` when a positional workflow is present.

**Tech Stack:** Python argparse, dataclasses, existing runner config models, pytest.

---

### Task 1: Add Failing Workflow Selection Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Add explicit conflict test**

Add this test near the existing workflow/factory validation tests:

```python
def test_cli_rejects_workflow_name_with_explicit_workflow_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--workflow-factory",
            "tests.runner.fixtures:create_custom_workflow",
            "--json",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "workflow and --workflow-factory are mutually exclusive" in captured.err
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 2: Add CLI precedence test for config factories**

Add this test near the existing config override tests:

```python
def test_cli_workflow_name_overrides_config_workflow_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
        ],
        config_source=DictConfigSource(
            {
                "workflow_factory": "tests.runner.fixtures:create_custom_workflow",
            }
        ),
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] is None
    assert report["actions"] == [
        {"success": True, "message": "open"},
    ]
    assert fixtures.CREATED_SESSIONS == []
```

- [ ] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_workflow_name_with_explicit_workflow_factory tests/runner/test_cli.py::test_cli_workflow_name_overrides_config_workflow_factory --no-cov -q
```

Expected: both tests fail under the current ambiguous selection behavior.

### Task 2: Implement Workflow Selection Resolution

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [ ] **Step 1: Import dataclass replacement helper**

Add this import near the top:

```python
from dataclasses import replace
```

- [ ] **Step 2: Add a selection helper**

Add this helper near `_merge_config`:

```python
def _resolve_workflow_selection(
    args: argparse.Namespace,
    config: RunnerConfig,
) -> RunnerConfig:
    if args.workflow and args.workflow_factory:
        raise ValueError("workflow and --workflow-factory are mutually exclusive")
    if args.workflow and config.workflow_factory:
        return replace(config, workflow_factory=None)
    return config
```

- [ ] **Step 3: Apply the helper after config merge**

In `main()`, after `_merge_config(args, config)`, add:

```python
        try:
            config = _resolve_workflow_selection(args, config)
        except ValueError as exc:
            return _print_error(str(exc))
```

- [ ] **Step 4: Run focused green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_rejects_workflow_name_with_explicit_workflow_factory tests/runner/test_cli.py::test_cli_workflow_name_overrides_config_workflow_factory --no-cov -q
```

Expected: both tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document workflow source precedence**

Add this note near the custom workflow command documentation:

```markdown
Use either a built-in workflow name or `--workflow-factory`, not both. A
positional workflow name overrides a config-provided workflow factory because
CLI arguments take precedence over environment defaults.
```

- [ ] **Step 2: Record the slice**

Append a `2026-06-17: Runner Workflow Factory Selection` section to
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
git add automation_runner tests README.md docs
git commit -m "fix: disambiguate runner workflow factory selection"
git push origin main
```
