# Examples Metadata Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return a clear CLI error when `examples --json` finds a built-in workflow without metadata.

**Architecture:** Keep the built-in workflow and metadata registries in `automation_runner.cli`. Add a small validation/serialization helper so JSON discovery either returns the same successful payload as today or fails before printing partial JSON. `automation_core` remains business-agnostic and unchanged.

**Tech Stack:** Python argparse/json, pytest, monkeypatch-based CLI regression tests.

---

### Task 1: Add Failing Metadata Consistency Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Import the CLI module for monkeypatching**

Add this import near the existing runner CLI import:

```python
import automation_runner.cli as cli
```

- [x] **Step 2: Add missing-metadata regression coverage**

Add this test near the existing examples JSON tests:

```python
def test_cli_examples_json_rejects_workflow_missing_metadata(monkeypatch, capsys):
    workflows = dict(cli.WORKFLOWS)
    workflows["missing-metadata"] = object()
    monkeypatch.setattr(cli, "WORKFLOWS", workflows)

    exit_code = main(["examples", "--json"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "missing workflow metadata: missing-metadata" in captured.err
```

- [x] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_examples_json_rejects_workflow_missing_metadata --no-cov -q
```

Expected: the test fails because `examples --json` raises `KeyError` instead
of returning a clean CLI error.

### Task 2: Implement Metadata Validation

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Add a list serialization helper**

Add this helper below `_workflow_listing_entry(...)`:

```python
def _workflow_listing_entries() -> List[Dict[str, object]]:
    missing_metadata = sorted(set(WORKFLOWS) - set(WORKFLOW_METADATA))
    if missing_metadata:
        raise ValueError(f"missing workflow metadata: {', '.join(missing_metadata)}")
    return [
        _workflow_listing_entry(workflow_name)
        for workflow_name in sorted(WORKFLOWS)
    ]
```

- [x] **Step 2: Use the helper from the examples JSON branch**

Replace:

```python
                "workflows": [
                    _workflow_listing_entry(workflow_name)
                    for workflow_name in sorted(WORKFLOWS)
                ],
```

with:

```python
                "workflows": _workflow_listing_entries(),
```

- [x] **Step 3: Catch the validation error before printing JSON**

Wrap the payload creation in the `args.command == "examples"` JSON branch:

```python
        if args.json:
            try:
                workflows = _workflow_listing_entries()
            except ValueError as exc:
                return _print_error(str(exc))
            payload = {
                "dry_run": args.dry_run,
                "workflows": workflows,
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
```

- [x] **Step 4: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json or missing_metadata' --no-cov -q
```

Expected: the new consistency test and existing examples JSON tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document metadata consistency**

Document that built-in workflow entries in `WORKFLOWS` must have matching JSON
discovery metadata before they can be emitted by `examples --json`.

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

- [x] **Step 4: Record the slice**

Append a `2026-06-17: Examples Metadata Consistency` section to
`docs/development-log.md` with red/green results, full verification, production
review summary, and the boundary note that `automation_core` remains unchanged.

- [x] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_runner tests docs
git commit -m "fix: validate examples metadata registry"
git push origin main
```
