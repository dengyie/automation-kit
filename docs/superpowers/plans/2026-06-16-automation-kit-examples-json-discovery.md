# Examples JSON Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `automation-runner examples --json` for machine-readable built-in workflow discovery.

**Architecture:** Extend only the examples subcommand in `automation_runner.cli`. Reuse the existing `WORKFLOWS` registry, keep text output unchanged, and avoid any live session loading or package scanning.

**Tech Stack:** Python argparse, json, pytest, existing runner CLI tests.

---

## Task 1: Add Failing CLI Discovery Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Write `examples --json` test**

Add a test:

```python
def test_cli_lists_example_workflows_as_json(capsys):
    exit_code = main(["examples", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "dry_run": False,
        "workflows": [
            {"name": "damai-android-smoke"},
            {"name": "damai-web-smoke"},
        ],
    }
    assert captured.err == ""
```

- [x] **Step 2: Write `examples --dry-run --json` test**

Add a test:

```python
def test_cli_lists_example_workflows_as_json_with_dry_run(capsys):
    exit_code = main(["examples", "--dry-run", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["dry_run"] is True
    assert payload["workflows"] == [
        {"name": "damai-android-smoke"},
        {"name": "damai-web-smoke"},
    ]
```

- [x] **Step 3: Run red CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Expected: fail because the examples parser does not accept `--json`.

## Task 2: Implement JSON Examples Output

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Add parser flag**

Add to the examples subparser:

```python
examples.add_argument("--json", action="store_true", help="emit JSON workflow list")
```

- [x] **Step 2: Emit deterministic JSON payload**

In the `args.command == "examples"` branch, before plain text printing:

```python
if args.json:
    payload = {
        "dry_run": args.dry_run,
        "workflows": [
            {"name": workflow_name}
            for workflow_name in sorted(WORKFLOWS)
        ],
    }
    print(json.dumps(payload, sort_keys=True))
    return 0
```

- [x] **Step 3: Run green CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document examples JSON discovery**

Document:

```bash
automation-runner examples --json
automation-runner examples --dry-run --json
```

and mention that the JSON output only lists built-in examples.

- [x] **Step 2: Run full verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and diff check reports no whitespace errors.

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and no unresolved P0/P1/P2 findings remain.

- [ ] **Step 4: Commit and push**

```bash
git add automation_runner tests README.md docs
git commit -m "feat: add json examples listing"
git push origin main
```
