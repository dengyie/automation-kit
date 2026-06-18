# Slidex Visual Platform Integration

This document records the automation-kit-side development baseline for consuming
`dengyie/slidex` after its visual platform upgrade.

## Decision

`slidex` is the only visual capability platform in the automation-kit ecosystem.
It owns OCR, slider captcha solving, screenshot recognition, visual evidence,
telemetry, and manual visual fallback contracts.

`automation-kit` remains business-agnostic and visual-platform-agnostic:

- `automation_core` must not import `slidex`
- `automation_runner` must not require `slidex`
- official examples may mention `slidex`, but should not make default tests
  require browser, device, network, or `slidex`
- application repositories decide whether to install and instantiate `slidex`

## Latest Slidex Contract

The current local slidex baseline is commit
`aa48a12 Fix visual solver cleanup and artifacts`.

The public surfaces automation-kit consumers should use are:

```python
from slidex.vision import (
    ChallengeType,
    VisionContext,
    VisualChallengeRequest,
    VisualChallengeResult,
    VisualChallengeSolver,
)
from slidex.integrations.automation_kit import (
    to_action_result,
    to_artifacts,
    to_events,
)
```

Supported challenge types:

- `slider_captcha`
- `ocr_text`
- `image_text`
- `visual_element`
- `manual_fallback`

Supported contexts:

- `playwright_page`
- `cdp`
- `image_bytes`
- `image_path`
- `android_screenshot_bytes`
- `manual`

`VisualChallengeResult.to_dict()` redacts cookies and sensitive metadata keys.
The compatibility adapters preserve that rule.

## Adapter Shape

`slidex.integrations.automation_kit` is optional and one-way. It maps slidex
results outward to automation-kit-shaped objects, while automation-kit itself
does not map inward to slidex.

Default dict mode:

- `to_action_result(result)` returns an `ActionResult`-shaped dict
- `to_artifacts(result)` returns JSON-serializable artifact dicts
- `to_events(result, task_id=...)` returns event-envelope-shaped dicts

Native mode:

- `to_action_result(result, prefer_native=True)` returns
  `automation_core.drivers.ActionResult`
- `to_artifacts(result, prefer_native=True)` returns
  `automation_core.drivers.ArtifactHandle`
- `to_events(result, task_id=..., prefer_native=True)` returns
  `automation_core.events.EventEnvelope`

Native mode requires `automation-kit` import visibility in the slidex process.
Application repositories can provide that through an editable install,
published package dependency, or `PYTHONPATH` during local compatibility tests.

## Resource Ownership

When an application passes an existing Playwright page to slidex:

```python
request = VisualChallengeRequest(
    challenge_type=ChallengeType.SLIDER_CAPTCHA,
    context=VisionContext.PLAYWRIGHT_PAGE,
    page=page,
    page_url="https://example.test",
)
result = await VisualChallengeSolver().solve(request)
```

Ownership rules:

- the application owns the Playwright browser, context, and page
- slidex may attach response listeners and a CDP session during solving
- slidex must clean its own listener and CDP session before returning
- the application must continue to close its own browser resources

This boundary is important for long-lived automation-kit workflows that reuse
the same browser page across multiple tasks.

## Workflow Integration Pattern

Application workflows should inject visual solving explicitly:

```python
class DamaiWorkflow:
    def __init__(self, session, visual_solver=None):
        self.session = session
        self.visual_solver = visual_solver

    async def solve_visual_challenge(self, page):
        if self.visual_solver is None:
            return None

        result = await self.visual_solver.solve(
            VisualChallengeRequest(
                challenge_type=ChallengeType.SLIDER_CAPTCHA,
                context=VisionContext.PLAYWRIGHT_PAGE,
                page=page,
                provider="auto",
            )
        )
        return result
```

The workflow can then convert the result at the boundary where automation-kit
reports are assembled:

```python
action = to_action_result(result)
artifacts = to_artifacts(result)
events = to_events(result, task_id=task_id)
```

For native report objects:

```python
action = to_action_result(result, prefer_native=True)
artifacts = to_artifacts(result, prefer_native=True)
events = to_events(result, task_id=task_id, prefer_native=True)
```

## Automation-Kit Boundaries

Do not add these to `automation_core`:

- `slidex` imports
- OCR abstractions
- captcha abstractions
- visual provider manifests
- website or Android app visual challenge logic
- Playwright, CDP, Appium, or browser-specific visual challenge state

Allowed automation-kit work:

- generic `ActionResult`, `ArtifactHandle`, and `EventEnvelope` contracts
- report serialization and redaction
- workflow composition helpers
- examples that show optional dependency injection
- documentation that points applications to slidex

## Compatibility Verification

Minimum local checks:

```bash
cd /Users/mango/project/codex/automation-kit
.venv/bin/python -m pytest -q

cd /Users/mango/project/codex/slidex
/opt/homebrew/bin/pytest -q
PYTHONPATH=/Users/mango/project/codex/automation-kit \
  /opt/homebrew/bin/pytest -q tests/test_automation_kit_integration.py
```

Application repositories should add their own optional integration checks once
they inject slidex in real workflows.

## Current Follow-Up Plan

1. Keep automation-kit core unchanged.
2. Update application repositories to inject slidex only at workflow boundaries.
3. Add app-level compatibility tests that run with slidex and automation-kit on
   the same Python path.
4. Keep slidex as the single visual platform and do not restore a standalone
   OCR plugin path.
