# Runner Version CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `automation-runner --version` and `python -m automation_runner --version` so installed runner environments can report the automation-kit version.

**Architecture:** Keep the version flag in `automation_runner.cli` as a top-level argparse option. Reuse `automation_core.__version__` as the single existing version constant and leave runner report schema versioning unchanged.

**Tech Stack:** Python argparse, pytest, existing `automation_core.__version__`, existing runner tests.

---

### Task 1: Add Failing Version Tests

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_cli.py`
- Modify: `/Users/mango/project/codex/automation-kit/tests/runner/test_module_entrypoint.py`

- [x] **Step 1: Add CLI version test**

Add this test near the other CLI parser tests:

```python
from automation_core import __version__ as AUTOMATION_KIT_VERSION


def test_cli_prints_runner_version(capsys):
    exit_code = main(["--version"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == f"automation-runner {AUTOMATION_KIT_VERSION}\n"
    assert captured.err == ""
```

- [x] **Step 2: Add module version test**

Add this test near the module-entrypoint subprocess test:

```python
from automation_core import __version__ as AUTOMATION_KIT_VERSION


def test_runner_module_entrypoint_prints_version():
    result = subprocess.run(
        [sys.executable, "-m", "automation_runner", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"automation-runner {AUTOMATION_KIT_VERSION}\n"
    assert result.stderr == ""
```

- [x] **Step 3: Run red verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_prints_runner_version tests/runner/test_module_entrypoint.py::test_runner_module_entrypoint_prints_version --no-cov -q
```

Expected: fail because top-level `--version` is not registered.

### Task 2: Implement Version Flag

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_runner/cli.py`

- [x] **Step 1: Import the package version**

Add this import near the other automation-core imports:

```python
from automation_core import __version__ as AUTOMATION_KIT_VERSION
```

- [x] **Step 2: Register top-level version flag**

In `build_parser()`, after creating the parser, add:

```python
parser.add_argument(
    "--version",
    action="version",
    version=f"automation-runner {AUTOMATION_KIT_VERSION}",
)
```

- [x] **Step 3: Run green verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/runner/test_cli.py::test_cli_prints_runner_version tests/runner/test_module_entrypoint.py::test_runner_module_entrypoint_prints_version --no-cov -q
```

Expected: both version tests pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/README.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [x] **Step 1: Document the version command**

Add `automation-runner --version` to the README runner command list.

- [x] **Step 2: Record the slice**

Add a `2026-06-17: Runner Version CLI` section to
`docs/development-log.md` with:

- red and green focused test results,
- full verification result,
- production review result,
- boundary note that report `schema_version` is unchanged.

- [x] **Step 3: Run full verification**

Run:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [x] **Step 4: Run production review scripts**

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
git commit -m "feat: add runner version flag"
git push origin main
```
