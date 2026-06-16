# Examples JSON Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `automation-runner examples --json` with stable built-in workflow metadata.

**Architecture:** Keep metadata in `automation_runner.cli` beside the built-in `WORKFLOWS` registry. The output remains deterministic and offline; `automation_core` stays business-agnostic and does not learn about Damai workflow metadata.

**Tech Stack:** Python argparse/json, pytest CLI tests, existing runner docs.

---

### Task 1: Add Failing CLI Metadata Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [x] **Step 1: Update `examples --json` expected payload**

Replace the expected `workflows` entries in
`test_cli_lists_example_workflows_as_json` with:

```python
        "workflows": [
            {
                "description": "Launch an Android app and capture startup artifacts.",
                "name": "damai-android-smoke",
                "platform": "android",
                "required_options": ["app_id"],
                "supports_dry_run": True,
            },
            {
                "description": "Open a web URL and capture a screenshot artifact.",
                "name": "damai-web-smoke",
                "platform": "web",
                "required_options": ["url"],
                "supports_dry_run": True,
            },
        ],
```

- [x] **Step 2: Update `examples --dry-run --json` expected workflows**

Replace the expected `payload["workflows"]` entries in
`test_cli_lists_example_workflows_as_json_with_dry_run` with the same two
metadata dictionaries.

- [x] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Expected: tests fail because the CLI currently emits only `{"name": ...}` for
each workflow.

### Task 2: Implement Examples Metadata Output

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Add a built-in metadata registry**

Add this constant below `WORKFLOWS`:

```python
WORKFLOW_METADATA = {
    "damai-android-smoke": {
        "description": "Launch an Android app and capture startup artifacts.",
        "platform": "android",
        "required_options": ["app_id"],
        "supports_dry_run": True,
    },
    "damai-web-smoke": {
        "description": "Open a web URL and capture a screenshot artifact.",
        "platform": "web",
        "required_options": ["url"],
        "supports_dry_run": True,
    },
}
```

- [x] **Step 2: Add a serialization helper**

Add this helper near the CLI helpers:

```python
def _workflow_listing_entry(workflow_name: str) -> Dict[str, object]:
    metadata = WORKFLOW_METADATA[workflow_name]
    return {
        "name": workflow_name,
        "description": metadata["description"],
        "platform": metadata["platform"],
        "required_options": list(metadata["required_options"]),
        "supports_dry_run": metadata["supports_dry_run"],
    }
```

- [x] **Step 3: Use the helper in JSON examples output**

Replace:

```python
                    {"name": workflow_name}
                    for workflow_name in sorted(WORKFLOWS)
```

with:

```python
                    _workflow_listing_entry(workflow_name)
                    for workflow_name in sorted(WORKFLOWS)
```

- [x] **Step 4: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'example_workflows_as_json' --no-cov -q
```

Expected: metadata tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document examples metadata**

Document that `automation-runner examples --json` returns built-in workflow
metadata including `name`, `description`, `platform`, `required_options`, and
`supports_dry_run`.

- [x] **Step 2: Run full verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

Expected: full tests pass and `git diff --check` emits no output.

- [x] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

Expected: scripts complete and identify the Python review context.

- [x] **Step 4: Record the slice**

Append a `2026-06-17: Examples JSON Metadata` section to
`docs/development-log.md` with red/green results, full verification, review
summary, and the boundary note that `automation_core` remains unchanged.

- [x] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_runner tests README.md docs
git commit -m "feat: add examples json metadata"
git push origin main
```
