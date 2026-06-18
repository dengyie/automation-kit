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

External repositories should depend on:

- `automation_core` for runtime contracts
- `automation_runner` for workflow authoring helpers

Built-in examples remain thin references and are not the long-term home for
business workflows.

## Repositories

- core: [dengyie/automation-kit](https://github.com/dengyie/automation-kit)
- app: [dengyie/automation-app-damai](https://github.com/dengyie/automation-app-damai)
- app: [dengyie/automation-app-dianping](https://github.com/dengyie/automation-app-dianping)
- visual platform: [dengyie/slidex](https://github.com/dengyie/slidex)

All ecosystem repositories are intended to stay public so application and
capability authors can consume the same baseline contracts directly.

The current slidex integration baseline is documented in
[`docs/slidex-visual-platform.md`](docs/slidex-visual-platform.md).

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

`automation-runner examples --json` lists built-in workflow metadata including
`name`, `description`, `platform`, `required_options`, and `supports_dry_run`.

Runner options can also come from environment variables. Explicit CLI
arguments take precedence:

```bash
AUTOMATION_RUNNER_JSON=true \
AUTOMATION_RUNNER_URL=https://example.test/damai \
automation-runner run damai-web-smoke
```

Explicit CLI values for `--factory`, `--workflow-factory`, `--url`, and
`--app-id` must contain at least one non-whitespace character.

Dictionary-backed runner config must provide string values for `factory`,
`workflow_factory`, `url`, and `app_id`; invalid types fail before factories are
loaded. Those config-backed string values must contain at least one
non-whitespace character.

Custom workflow parameters can also come from config. Environment values use a
JSON object string, and CLI `--param` values override matching config keys.
Config-backed parameter keys must contain at least one non-whitespace
character:

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
validation to the workflow package. The `KEY` portion must contain at least one
non-whitespace character.
Cancelled workflows keep `success=false`, but their top-level report `status`
and `run_state.status` are both `cancelled` so orchestrators can distinguish an
intentional stop from a failure. The CLI also returns exit code `130` for
cancelled runs, while ordinary workflow failures still return `1`.
Use either a built-in workflow name or `--workflow-factory`, not both. A
positional workflow name overrides a config-provided workflow factory because
CLI arguments take precedence over environment defaults.

See `docs/adding-a-workflow.md` for package boundaries, report fields, and
adapter rules. `automation-runner report-schema --version 1` prints the
packaged machine-readable runner report contract, which is also documented in
`docs/report-schema-v1.json`. See `docs/artifacts.md` for screenshot,
page-source, UI-tree, trace, and log artifact conventions. See
`docs/ecosystem.md` for repository roles and `docs/compatibility.md` for
cross-repo versioning and verification expectations.
