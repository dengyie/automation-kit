# Automation Kit Technical Landscape

## Goal

`automation-kit` should be a Python-first automation application base for
building reliable web and Android app automation workflows.

It should learn from existing GitHub projects without copying their scope:

- keep deterministic code paths for production workflows,
- expose business-agnostic runtime primitives,
- support website and Android app adapters,
- make AI optional and bounded instead of the default control plane.

## Related Projects

| Project | Primary Focus | Useful Ideas | Avoid Copying |
| --- | --- | --- | --- |
| Browser Use | AI-native browser agents with Python API and native core | recovery loops, browser harness, agent-facing action space | making AI the only execution model |
| Stagehand | Playwright plus natural language browser actions | mix precise code with natural language for brittle pages | browser-only scope and TypeScript-first assumptions |
| Skyvern | LLM + computer vision browser workflows and no-code workflow builder | selector-light fallback, workflow artifact mindset | heavyweight platform/no-code product scope |
| Vercel agent-browser | CLI for browser automation aimed at AI agents | stable command vocabulary, snapshots, batch execution, provider abstraction | browser-only CLI as the whole architecture |
| Playwright | deterministic web automation and testing | strong browser primitives, trace/screenshot/debug tooling | treating browser testing APIs as the full product layer |
| Appium | WebDriver-based mobile, desktop, IoT automation | driver plugin ecosystem, multi-language contract, device session model | leaking target app capabilities into core |
| Maestro | YAML flows for mobile and web E2E automation | simple workflow format, fast onboarding, cross-platform flow vocabulary | test-only mental model if the goal is automation apps |
| Appium MCP projects | AI-integrated mobile automation control | device discovery and LLM/tool integration patterns | MCP-first architecture before the core runtime is stable |

## Design Lessons

### 1. Separate Runtime From Intelligence

Browser Use, Stagehand, and Skyvern show that AI can make UI automation more
flexible. They also show a risk: once AI owns every action, repeatability,
testing, cost, and debugging become harder.

`automation-kit` should keep this split:

- deterministic task runner,
- deterministic driver/session adapters,
- deterministic retry, timeout, and artifact handling,
- optional AI-assisted action resolvers behind explicit interfaces.

The core should never require an LLM key.

### 2. Use Driver Contracts, Not Driver Lock-In

Playwright and Appium both prove the value of stable driver APIs. Appium also
proves that mobile automation needs a session/capability boundary.

`automation-kit` should define contracts such as:

- `DriverSession`
- `ElementHandle`
- `ActionExecutor`
- `ArtifactSink`
- `TaskRunner`

Concrete adapters can then implement these contracts for Selenium, Appium, and
later Playwright.

### 3. Make Observability A First-Class Feature

agent-browser and Playwright both put operational artifacts close to the user:
snapshots, screenshots, traces, command output, and debug handles.

`automation-kit` should standardize:

- run IDs,
- structured events,
- screenshot/page-source/UI-tree artifacts,
- retry attempt logs,
- task result JSON.

This matters more than a large action library in the first version.

### 4. Keep Workflow Format Optional In V1

Maestro's YAML flows are excellent for onboarding, but a workflow DSL becomes a
product by itself.

`automation-kit` should not start with a YAML/DSL commitment. The first version
should provide Python task composition. A workflow file format can come later
after two real adapters prove the repeated shape.

### 5. Treat Android As A First-Class Channel

Most browser-agent projects are browser-only. The current Damai and Dianping
projects both need Android automation for workflows that are unavailable or
fragile on the web.

`automation-kit` should model web and Android equally:

- shared task runner,
- shared retry/timeout/event/artifact model,
- separate driver adapters,
- separate selector/action capability sets.

## Recommended Positioning

`automation-kit` should be positioned as:

> A Python-first automation application toolkit for composing reliable website
> and Android app workflows with testable runtime primitives and optional AI
> assistance.

It is not:

- a pure browser agent,
- a no-code workflow platform,
- an Appium wrapper only,
- a testing framework only,
- an LLM agent framework.

## Initial Repository Shape

Recommended sibling path:

```text
/Users/mango/project/codex/automation-kit/
```

Recommended GitHub repo:

```text
github.com/dengyie/automation-kit
```

Initial package:

```text
automation_core/
  config/
  drivers/
  tasks/
  actions/
  state/
  events/
  retries/
  artifacts/
examples/
  damai_web/
  damai_android/
docs/
tests/
```

The current `ticket-purchase` repository should be treated as a source adapter
and migration reference, not as the long-term home for the base.

## Borrow / Avoid Checklist

Borrow:

- Browser Use: recovery loop ideas.
- Stagehand: code-first with selective natural language actions.
- Skyvern: artifact-rich workflow execution.
- agent-browser: command vocabulary, snapshots, batch execution.
- Playwright: trace/debug discipline.
- Appium: device session boundaries.
- Maestro: approachable flow vocabulary, later.

Avoid:

- unbounded AI control loops,
- business selectors in core,
- global config objects,
- hidden live-device requirements in default tests,
- workflow DSL before stable Python APIs,
- browser-only architecture,
- Android capability leakage into core.

## References

- Browser Use: https://github.com/browser-use/browser-use
- Stagehand: https://github.com/browserbase/stagehand
- Skyvern: https://github.com/skyvern-ai/skyvern
- Vercel agent-browser: https://github.com/vercel-labs/agent-browser
- Playwright: https://github.com/microsoft/playwright
- Appium: https://github.com/appium/appium
- Maestro: https://github.com/mobile-dev-inc/maestro
- Appium MCP topic example: https://github.com/topics/mobile-testing?l=python
