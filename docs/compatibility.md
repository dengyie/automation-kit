# Compatibility

## Version Policy

- `automation-kit` publishes explicit versions.
- application repositories pin a compatible `automation-kit` version.
- optional capability repositories document the `automation-kit` ranges they
  support when they start depending on core-side contracts.

## Minimum Verification Matrix

- `automation-kit`: offline unit and runner suite
- `automation-app-damai`: offline workflow, config, and CLI suite
- `automation-app-dianping`: offline workflow and config suite
- `slidex`: visual challenge API, OCR API, and optional automation-kit
  integration suite once its platform API lands

## Current Local Verification Commands

```text
automation-kit:
  /Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest -q

automation-app-damai:
  /Users/mango/project/codex/automation-app-damai/.venv/bin/python -m pytest -q

automation-app-dianping:
  /Users/mango/project/codex/automation-app-dianping/.venv/bin/python -m pytest -q

slidex:
  /Users/mango/project/codex/slidex/.venv/bin/python -m pytest -q
```
