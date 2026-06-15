# Automation Kit Workflow Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add typed runner-layer workflow context and options for custom workflow factories.

**Architecture:** Keep `WorkflowContext` and `WorkflowOptions` in `automation_runner`, because they describe runner execution rather than core automation primitives. Custom factories receive these typed values while built-in examples keep their current explicit `url` and `app_id` signatures. The implementation must preserve compatibility for existing custom factories that only accept `session_factory`.

**Tech Stack:** Python dataclasses, argparse, pytest, existing `automation_runner` CLI and config code.

---

## Task 1: Add Runner Context Models

**Files:**

- Create: `/Users/mango/project/codex/automation-kit/automation_runner/context.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/__init__.py`
- Test: `/Users/mango/project/codex/automation-kit/tests/runner/test_context.py`

- [ ] **Step 1: Write failing tests**

```python
from automation_runner.context import WorkflowContext, WorkflowOptions


def test_workflow_context_records_runner_metadata():
    context = WorkflowContext(
        workflow_name="tests.runner.fixtures:create_context_workflow",
        live=True,
        workflow_factory="tests.runner.fixtures:create_context_workflow",
        session_factory="tests.runner.fixtures:make_session",
    )

    assert context.workflow_name == "tests.runner.fixtures:create_context_workflow"
    assert context.live is True
    assert context.workflow_factory == "tests.runner.fixtures:create_context_workflow"
    assert context.session_factory == "tests.runner.fixtures:make_session"


def test_workflow_options_records_runner_inputs():
    options = WorkflowOptions(
        url="https://example.test/damai",
        app_id="cn.damai",
        emit_json=True,
        report_file="reports/run.json",
    )

    assert options.url == "https://example.test/damai"
    assert options.app_id == "cn.damai"
    assert options.emit_json is True
    assert options.report_file == "reports/run.json"
```

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: fail because `automation_runner.context` does not exist.

- [ ] **Step 2: Implement models**

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    live: bool
    workflow_factory: Optional[str] = None
    session_factory: Optional[str] = None


@dataclass(frozen=True)
class WorkflowOptions:
    url: Optional[str] = None
    app_id: Optional[str] = None
    emit_json: bool = False
    report_file: Optional[str] = None
```

- [ ] **Step 3: Export models**

Add exports from `automation_runner/__init__.py`.

- [ ] **Step 4: Verify**

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_context.py --no-cov -q
```

Expected: pass.

## Task 2: Pass Context To Custom Workflow Factories

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/fixtures.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`

- [ ] **Step 1: Write failing custom workflow fixture and test**

Add a fixture factory:

```python
def create_context_workflow(session_factory, context, options):
    return ExampleWorkflow(
        name=context.workflow_name,
        session_factory=session_factory,
        run_fn=lambda session: ExampleWorkflowResult(
            session=session.info,
            success=True,
            actions=[
                session.execute_action(
                    "context_action",
                    workflow=context.workflow_name,
                    live=context.live,
                    url=options.url,
                    app_id=options.app_id,
                    emit_json=options.emit_json,
                    report_file=options.report_file,
                )
            ],
            artifacts=[],
        ),
    )
```

Add a CLI test that runs:

```bash
automation-runner run --workflow-factory tests.runner.fixtures:create_context_workflow --json --url https://example.test/damai --app-id cn.damai --report-file <tmp>
```

Expected report action message: `context_action`.

- [ ] **Step 2: Run failing test**

Run:

```bash
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_passes_context_and_options_to_custom_workflow_factory --no-cov -q
```

Expected: fail because the CLI does not pass `context` and `options`.

- [ ] **Step 3: Implement context construction and factory call**

Create `WorkflowContext` and `WorkflowOptions` from merged config and pass them
to custom workflow factories.

- [ ] **Step 4: Preserve compatibility fallback**

If the custom factory rejects `context` or `options`, retry with
`session_factory` only. This keeps older custom factories working.

- [ ] **Step 5: Verify**

Run:

```bash
.venv/bin/python -m pytest tests/runner -q --no-cov
```

Expected: runner tests pass.

## Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the new custom workflow factory signature**

Show both supported shapes:

```python
def create_workflow(session_factory):
    ...


def create_workflow(session_factory, context, options):
    ...
```

- [ ] **Step 2: Run verification**

Run:

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all tests pass and diff has no whitespace errors.

- [ ] **Step 3: Run production review scripts**

Run:

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
git commit -m "feat: pass workflow context to custom factories"
git push origin main
```
