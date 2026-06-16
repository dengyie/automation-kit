# automation-kit

Python-first automation application toolkit for composing reliable website and
Android app workflows.

## Positioning

`automation-kit` provides deterministic runtime primitives first:

- task lifecycle
- deterministic task runner
- run state
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
automation-runner examples --json
automation-runner --version
automation-runner run damai-web-smoke --json \
  --url https://example.test/damai
automation-runner run damai-web-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --url https://example.test/damai
automation-runner run --workflow-factory my_package.workflow:create_workflow \
  --json \
  --param account=test-user \
  --param city=shanghai
automation-runner report-schema --version 1
```

Runner options can also come from environment variables. Explicit CLI
arguments take precedence:

```bash
AUTOMATION_RUNNER_JSON=true \
AUTOMATION_RUNNER_URL=https://example.test/damai \
automation-runner run damai-web-smoke
```

Custom workflow parameters can also come from config. Environment values use a
JSON object string, and CLI `--param` values override matching config keys:

```bash
AUTOMATION_RUNNER_JSON=true \
AUTOMATION_RUNNER_WORKFLOW_FACTORY=my_package.workflow:create_workflow \
AUTOMATION_RUNNER_PARAMETERS='{"account":"config-user","city":"beijing"}' \
automation-runner run --param city=shanghai
```

Custom workflow factories can accept either the legacy `session_factory`
signature or the typed runner context:

```python
def create_workflow(session_factory):
    ...


def create_workflow(session_factory, context, options):
    ...
```

JSON reports include a safe `workflow_context` summary for runner metadata.
Custom workflow inputs can use repeated `--param KEY=VALUE` flags. The runner
passes those strings through as `options.parameters` and leaves workflow-specific
validation to the workflow package.

See `docs/adding-a-workflow.md` for package boundaries, report fields, and
adapter rules. `automation-runner report-schema --version 1` prints the
packaged machine-readable runner report contract, which is also documented in
`docs/report-schema-v1.json`. See `docs/artifacts.md` for screenshot,
page-source, UI-tree, trace, and log artifact conventions.
