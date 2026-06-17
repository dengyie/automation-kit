# Compatibility

## Version Policy

- `automation-kit` publishes explicit versions.
- application repositories pin a compatible `automation-kit` version.
- plugin repositories document the `automation-kit` ranges they support when
  they start depending on core-side contracts.

## Minimum Verification Matrix

- `automation-kit`: offline unit and runner suite
- `automation-app-damai`: offline workflow, config, and CLI suite
- `automation-app-dianping`: offline workflow and config suite
- `automation-plugin-ocr`: offline plugin API suite

## Current Local Verification Commands

```text
automation-kit:
  /Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest -q

automation-app-damai:
  /Users/mango/project/codex/automation-app-damai/.venv/bin/python -m pytest -q

automation-app-dianping:
  /Users/mango/project/codex/automation-app-dianping/.venv/bin/python -m pytest -q

automation-plugin-ocr:
  /Users/mango/project/codex/automation-plugin-ocr/.venv/bin/python -m pytest -q
```
