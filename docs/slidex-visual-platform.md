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

The reviewed slidex implementation baseline is commit
`39d021e docs(阶段10): 记录 github 发布闭环`.

Slidex now includes `docs/automation-kit-vision-platform.md` as the committed
slidex-side canonical design document for this ecosystem boundary.

This baseline was re-reviewed after slidex committed and pushed its latest
vision-platform work. The committed implementation still matches the
automation-kit boundary: `slidex.vision` owns visual challenge contracts,
`slidex.ocr` owns OCR extraction, and `slidex.integrations.automation_kit`
performs one-way optional conversion into automation-kit-shaped results.

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

Implementation notes from the latest code review:

- `VisualChallengeSolver.solve()` routes `ocr_text` and `image_text` through the
  configured OCR extractor, defaulting to `FakeOcrExtractor` for offline tests.
- `slider_captcha` routes to `SliderSolver` through either `cdp` or
  `playwright_page` context.
- Unsupported challenge types and slider contexts return failed
  `VisualChallengeResult` values instead of raising as the default path.
- Slider solving closes the underlying `SliderSolver` in `finally`, including
  awaitable close methods.

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

Application repositories must keep their own optional integration checks close
to the app-layer helpers that construct slidex requests and convert slidex
results.

Current app compatibility slices:

```bash
cd /Users/mango/project/codex/automation-app-damai
PYTHONPATH=/Users/mango/project/codex/automation-app-damai:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex \
  /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'
PYTHONPATH=/Users/mango/project/codex/automation-app-damai:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex \
  /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'solve_slider_visual_challenge'

cd /Users/mango/project/codex/automation-app-dianping
PYTHONPATH=/Users/mango/project/codex/automation-app-dianping:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex \
  /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'visual_request or visual_result'
PYTHONPATH=/Users/mango/project/codex/automation-app-dianping:/Users/mango/project/codex/automation-kit:/Users/mango/project/codex/slidex \
  /opt/homebrew/bin/pytest -q -o addopts='' tests/test_workflow.py -k 'solve_android_screenshot_visual_challenge'
```

## Current Ecosystem Status

1. `automation-kit` core remains unchanged and does not import slidex.
2. `automation-app-damai` provides lazy app-layer helpers and
   `solve_slider_visual_challenge(...)` for production workflows that already
   own a real Playwright page.
3. `automation-app-dianping` provides lazy app-layer helpers and
   `solve_android_screenshot_visual_challenge(...)` for production workflows
   that already own Android screenshot bytes.
4. Both application repositories keep default offline tests independent from
   slidex and add optional compatibility slices that run with slidex and
   automation-kit on the same Python path.
5. The standalone OCR plugin path is archived in favor of slidex.
6. Live helper boundaries are implemented in the application repositories.
   Real target-site browser and Appium/ADB E2E validation remains opt-in and
   outside default tests.
7. The slidex canonical document and automation-kit integration baseline now
   point at the same reviewed slidex implementation baseline, so the previous
   "pending slidex commit" risk is closed. Later documentation-only commits may
   move repository heads without changing this API review baseline.

## Remaining Follow-Up Plan

1. Add opt-in Damai target-site Playwright E2E once a real challenge page is
   available.
2. Add opt-in Dianping Appium/ADB E2E once a real device workflow can capture
   screenshot bytes at the target moment.
3. Decide at each application report boundary whether to use slidex dict
   adapter output or native automation-kit dataclasses.
