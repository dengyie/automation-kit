# Runner Workflow Parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a business-agnostic `--param KEY=VALUE` runner input channel for custom workflow factories.

**Architecture:** Keep parsing and validation in `automation_runner.cli`, store parsed values on `WorkflowOptions`, and pass them through the existing custom workflow factory call path. Do not change `automation_core`, report serialization, or built-in Damai workflow signatures.

**Tech Stack:** Python dataclasses, argparse, pytest, existing runner fixtures.

---

## Task 1: Add WorkflowOptions Parameter Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_context.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/context.py`

- [x] **Step 1: Write failing tests for `WorkflowOptions.parameters`**

Add assertions that `WorkflowOptions` stores a parameter dictionary and includes
it in `to_dict()`:

```python
options = WorkflowOptions(
    url="https://example.test/damai",
    app_id="cn.damai",
    emit_json=True,
    report_file="reports/run.json",
    parameters={"account": "test-user", "city": "shanghai"},
)

assert options.parameters == {"account": "test-user", "city": "shanghai"}
assert options.to_dict()["parameters"] == {
    "account": "test-user",
    "city": "shanghai",
}
```

- [x] **Step 2: Run red context tests**

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: fail because `WorkflowOptions` has no `parameters` field.

- [x] **Step 3: Add `parameters` to `WorkflowOptions`**

Add a dataclass field:

```python
parameters: Dict[str, str] = field(default_factory=dict)
```

and include `parameters` in `to_dict()`.

- [x] **Step 4: Run green context tests**

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: pass.

## Task 2: Parse CLI Parameters For Custom Workflows

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/fixtures.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Extend the context workflow fixture**

Update `create_context_workflow(...)` so its fake action records:

```python
parameters=options.parameters,
```

- [x] **Step 2: Write failing CLI parameter pass-through test**

Extend `test_cli_passes_context_and_options_to_custom_workflow_factory` with:

```python
"--param",
"account=test-user",
"--param",
"city=shanghai",
"--param",
"token=a=b",
```

and assert the fake session receives:

```python
"parameters": {
    "account": "test-user",
    "city": "shanghai",
    "token": "a=b",
}
```

- [x] **Step 3: Write failing malformed parameter test**

Add a test that runs a live custom workflow with:

```python
"--param",
"missing-equals",
```

Expected:

```python
assert exit_code == 2
assert "--param must use KEY=VALUE" in captured.err
assert fixtures.CREATED_SESSIONS == []
```

- [x] **Step 4: Run red CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'context_and_options or rejects_invalid_workflow_param' --no-cov -q
```

Expected: fail because the parser and options object do not support `--param`.

- [x] **Step 5: Implement parameter parsing**

Add `--param` to the run parser with `action="append"` and parse values with a
small helper:

```python
def _parse_parameters(values: Optional[List[str]]) -> Dict[str, str]:
    parameters = {}
    for value in values or []:
        key, separator, raw_value = value.partition("=")
        if not separator or not key:
            raise ValueError("--param must use KEY=VALUE")
        parameters[key] = raw_value
    return parameters
```

Pass the parsed dictionary into `WorkflowOptions(parameters=...)` before any
live session factory is loaded.

- [x] **Step 6: Run green CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'context_and_options or rejects_invalid_workflow_param' --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document `--param` usage**

Document that custom workflows can use repeated `--param KEY=VALUE` flags and
read the parsed strings from `options.parameters`.

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
git commit -m "feat: pass workflow parameters"
git push origin main
```
