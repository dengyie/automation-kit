# Module Entrypoint Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct test coverage for the `python -m automation_runner` entrypoint wrapper without changing CLI behavior.

**Architecture:** Keep the entrypoint wrapper in `automation_runner.__main__` and delegate to `automation_runner.cli.main`. Add a tiny `run()` wrapper so tests can verify delegation in-process while the existing subprocess smoke test continues to cover real module execution.

**Tech Stack:** Python standard library, pytest, existing `automation_runner` package.

---

### Task 1: Add Failing Entrypoint Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_module_entrypoint.py`

- [x] **Step 1: Add direct delegation tests**

Append these tests:

```python
import runpy
from unittest.mock import Mock

import pytest

import automation_runner.__main__ as module_entrypoint
import automation_runner.cli as cli


def test_module_entrypoint_run_delegates_to_cli_main(monkeypatch):
    fake_main = Mock(return_value=7)
    monkeypatch.setattr(module_entrypoint, "main", fake_main)

    assert module_entrypoint.run() == 7

    fake_main.assert_called_once_with()


def test_module_entrypoint_script_exits_with_delegated_code(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda: 4)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(module_entrypoint.__file__, run_name="__main__")

    assert exc_info.value.code == 4
```

- [x] **Step 2: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_module_entrypoint.py --no-cov -q
```

Expected: fail because `automation_runner.__main__.run` does not exist.

### Task 2: Implement Testable Entrypoint Wrapper

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/__main__.py`

- [x] **Step 1: Add `run()`**

Change the file to:

```python
from automation_runner.cli import main


def run() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
```

- [x] **Step 2: Run green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_module_entrypoint.py --no-cov -q
```

Expected: all module entrypoint tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document the slice**

Add a `2026-06-17: Module Entrypoint Coverage` section that records:

- the new testable `run()` wrapper,
- the unchanged subprocess module-entrypoint behavior,
- focused and full verification results,
- production review results.

- [x] **Step 2: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [x] **Step 3: Run production review scripts**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Commit and push**

Run:

```bash
git add automation_runner tests docs
git commit -m "test: cover runner module entrypoint"
git push origin main
```
