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
- `slidex`: visual challenge API, OCR API, manual fallback model, artifact
  contract, and optional automation-kit adapter suite

## Current Local Verification Commands

```text
automation-kit:
  /Users/mango/project/codex/automation-kit/.venv/bin/python -m pytest -q

automation-app-damai:
  /Users/mango/project/codex/automation-app-damai/.venv/bin/python -m pytest -q

automation-app-dianping:
  /Users/mango/project/codex/automation-app-dianping/.venv/bin/python -m pytest -q

slidex:
  cd /Users/mango/project/codex/slidex
  /opt/homebrew/bin/pytest -q
  PYTHONPATH=/Users/mango/project/codex/automation-kit /opt/homebrew/bin/pytest -q tests/test_automation_kit_integration.py

Damai slidex compatibility:
  cd /Users/mango/project/codex/automation-app-damai
  PYTHONPATH=/Users/mango/project/codex/automation-app-damai:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'

Dianping slidex compatibility:
  cd /Users/mango/project/codex/automation-app-dianping
  PYTHONPATH=/Users/mango/project/codex/automation-app-dianping:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'
```

See `docs/slidex-visual-platform.md` for the current integration baseline.
