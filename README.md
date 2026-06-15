# automation-kit

Python-first automation application toolkit for composing reliable website and
Android app workflows.

## Positioning

`automation-kit` provides deterministic runtime primitives first:

- task lifecycle
- bounded retries
- driver/session contracts
- action requests and batches
- structured events
- artifacts

AI assistance, business workflows, selectors, and platform-specific
capabilities belong in adapters or examples, not in `automation_core`.

## Development

```bash
poetry install
poetry run pytest -q
```

Default tests must not require Chrome, Appium, ADB, Android devices, or
network.

## Workflow Shape

Business workflows live outside `automation_core`. A workflow factory should
return an object with a `run()` method:

```python
from examples.damai_web import create_workflow

workflow = create_workflow(
    session_factory=make_session,
    url="https://example.test/damai",
)
result = workflow.run()
```

The runner keeps live execution opt-in:

```bash
automation-runner examples --dry-run
automation-runner run damai-web-smoke --json \
  --url https://example.test/damai
automation-runner run damai-web-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --url https://example.test/damai
```

See `docs/adding-a-workflow.md` for package boundaries, report fields, and
adapter rules. See `docs/artifacts.md` for screenshot, page-source, UI-tree,
trace, and log artifact conventions.
