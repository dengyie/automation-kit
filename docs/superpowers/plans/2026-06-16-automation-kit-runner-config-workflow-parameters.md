# Runner Config Workflow Parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow runner config sources to provide custom workflow parameters, with CLI `--param` overriding config values.

**Architecture:** Add a `parameters` field to runner-layer `RunnerConfig`, parse config-sourced parameter dictionaries in `automation_runner.config`, and merge those values with CLI parameters in `automation_runner.cli`. Leave `automation_core.config` unchanged and keep report serialization unchanged.

**Tech Stack:** Python dataclasses, standard-library `json`, pytest, existing runner fixtures.

---

## Task 1: Add RunnerConfig Parameter Parsing Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_config.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/config.py`

- [x] **Step 1: Write failing config tests**

Add tests that expect:

```python
config = load_runner_config(
    DictConfigSource(
        {
            "parameters": {
                "account": "config-user",
                "city": "shanghai",
            }
        }
    )
)
assert config.parameters == {
    "account": "config-user",
    "city": "shanghai",
}
```

and:

```python
config = load_runner_config(
    DictConfigSource(
        {
            "parameters": '{"account":"config-user","city":"shanghai"}',
        }
    )
)
assert config.parameters == {
    "account": "config-user",
    "city": "shanghai",
}
```

and invalid values:

```python
with pytest.raises(ValueError, match="config parameters expected object"):
    load_runner_config(DictConfigSource({"parameters": "not-json"}))

with pytest.raises(ValueError, match="config parameters expected string keys and values"):
    load_runner_config(DictConfigSource({"parameters": {"count": 3}}))
```

- [x] **Step 2: Run red config tests**

```bash
.venv/bin/python -m pytest tests/runner/test_config.py --no-cov -q
```

Expected: fail because `RunnerConfig` has no `parameters` field and config
parsing ignores `parameters`.

- [x] **Step 3: Implement config parameter parsing**

In `automation_runner/config.py`:

- import `json`,
- add `parameters: Dict[str, str] = field(default_factory=dict)` to
  `RunnerConfig`,
- add an `_optional_parameters(...)` helper that accepts mappings or JSON object
  strings and rejects malformed values,
- pass `parameters=_optional_parameters(source, "parameters")` from
  `load_runner_config(...)`.

- [x] **Step 4: Run green config tests**

```bash
.venv/bin/python -m pytest tests/runner/test_config.py --no-cov -q
```

Expected: pass.

## Task 2: Merge Config And CLI Parameters

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Write failing CLI config parameter tests**

Add a test that runs `tests.runner.fixtures:create_context_workflow` with a
config source containing:

```python
{
    "json": "true",
    "workflow_factory": "tests.runner.fixtures:create_context_workflow",
    "parameters": {"account": "config-user", "city": "beijing"},
}
```

Assert the fake action receives:

```python
"parameters": {"account": "config-user", "city": "beijing"}
```

Add a second test that also passes:

```python
"--param", "city=shanghai"
```

Assert the final parameters are:

```python
"parameters": {"account": "config-user", "city": "shanghai"}
```

- [x] **Step 2: Run red CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'config_parameters' --no-cov -q
```

Expected: fail because config parameters are not merged into `WorkflowOptions`.

- [x] **Step 3: Merge parameters in CLI options**

Change `_workflow_options(...)` to merge config parameters with CLI parameters:

```python
parameters = dict(config.parameters)
parameters.update(_parse_parameters(args.param))
```

Pass that merged dictionary to `WorkflowOptions`.

- [x] **Step 4: Run green CLI tests**

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py -k 'config_parameters' --no-cov -q
```

Expected: pass.

## Task 3: Documentation, Review, Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document config-sourced workflow parameters**

Document `AUTOMATION_RUNNER_PARAMETERS='{"key":"value"}'` and explain CLI
`--param` override precedence.

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
git commit -m "feat: load workflow parameters from config"
git push origin main
```
