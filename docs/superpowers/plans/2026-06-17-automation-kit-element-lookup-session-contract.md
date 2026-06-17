# Element Lookup Session Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the core element lookup protocol so it matches the real Selenium/Appium lookup signature.

**Architecture:** Keep the change in `automation_core.drivers` because the protocol defines a core contract. Update tests to reflect the new contract shape. Leave Selenium/Appium adapter behavior unchanged and keep the boundary business-agnostic.

**Tech Stack:** Python protocols/dataclasses, pytest, existing adapter and driver contract tests.

---

### Task 1: Add Failing Core Contract Test

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/tests/drivers/test_contracts.py`

- [ ] **Step 1: Update the fake lookup session signature**

Change:

```python
class FakeLookupSession(FakeSession):
    def find_element(self, selector: str):
        self.selector = selector
        return FakeElement()
```

to:

```python
class FakeLookupSession(FakeSession):
    def find_element(self, by: str | None, selector: str):
        self.lookup = (by, selector)
        return FakeElement()
```

- [ ] **Step 2: Update the lookup-session test**

Change:

```python
element = session.find_element("button.login")
assert session.selector == "button.login"
```

to:

```python
element = session.find_element("css selector", "button.login")
assert session.lookup == ("css selector", "button.login")
```

- [ ] **Step 3: Run red verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/drivers/test_contracts.py --no-cov -q
```

Expected: fail because the core protocol still declares the old one-argument `find_element(...)` signature.

### Task 2: Update the Core Protocol

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/automation_core/drivers/contracts.py`
- Modify: `/Users/mango/project/codex/automation-kit/automation_core/drivers/__init__.py` if export ordering needs adjustment

- [ ] **Step 1: Update `ElementLookupSession`**

Replace:

```python
class ElementLookupSession(DriverSession, Protocol):
    def find_element(self, selector: str) -> ElementHandle:
        ...
```

with:

```python
class ElementLookupSession(DriverSession, Protocol):
    def find_element(self, by: Optional[str], selector: str) -> ElementHandle:
        ...
```

- [ ] **Step 2: Run focused green verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest tests/drivers/test_contracts.py tests/test_imports.py --no-cov -q
```

Expected: pass.

### Task 3: Documentation, Review, And Commit

**Files:**

- Modify: `/Users/mango/project/codex/automation-kit/docs/adding-a-workflow.md`
- Modify: `/Users/mango/project/codex/automation-kit/docs/development-log.md`

- [ ] **Step 1: Document the contract shape**

Add a short note near the adapter rules:

```markdown
`ElementLookupSession` models driver lookups with both an optional lookup
strategy and a selector so the core contract matches the real adapter shape.
```

- [ ] **Step 2: Run full verification**

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q
git diff --check
```

- [ ] **Step 3: Run production review scripts**

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/diff-line-map.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/detect-stack.py --repo /Users/mango/project/codex/automation-kit
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/run-safe-checks.py --repo /Users/mango/project/codex/automation-kit
```

- [ ] **Step 4: Record the slice**

Append a `2026-06-17: Element Lookup Session Contract Alignment` section to
`docs/development-log.md` with red/green results, full verification, production
review summary, and the boundary note that `automation_core` remains
business-agnostic.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/mango/project/codex/automation-kit
git add automation_core tests docs
git commit -m "fix: align element lookup session contract"
git push origin main
```
