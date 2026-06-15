# automation-kit

Python-first automation application toolkit for composing reliable website and
Android app workflows.

## Positioning

`automation-kit` provides deterministic runtime primitives first:

- task lifecycle
- bounded retries
- driver/session contracts
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
