# Automation Kit Development System

## Purpose

`automation-kit` is a Python-first, business-agnostic automation application
base for building reliable website and Android app automation workflows.

The current `ticket-purchase` repository remains the source of ideas and
migration reference material. The long-term home for the base is the sibling
repository `automation-kit`.

## Project Decision

- Name: `automation-kit`
- Recommended local path: `/Users/mango/project/codex/automation-kit/`
- Recommended GitHub repo: `github.com/dengyie/automation-kit`
- Current repo role: migration reference and example source, not the base repo

## Product Positioning

`automation-kit` should be:

- Python-first
- business-agnostic in `automation_core`
- capable of website and Android app automation
- deterministic by default
- optionally AI-assisted through explicit adapters

`automation-kit` should not be:

- a browser-only agent platform
- a no-code workflow product
- an Appium wrapper only
- a testing framework only
- an LLM-first control plane

## Technical Landscape

Relevant GitHub assets and what to borrow from them:

- `browser-use`: recovery loops and agent-facing browser actions
- `Stagehand`: code-first browser automation with selective natural language help
- `Skyvern`: artifact-rich workflows and selector-light fallback ideas
- `agent-browser`: command vocabulary, snapshots, and batch execution discipline
- `Playwright`: traces, screenshots, and deterministic browser primitives
- `Appium`: device session boundaries and multi-language driver contracts
- `Maestro`: approachable flow vocabulary for later, not V1

What to avoid:

- unbounded AI control loops
- business selectors in core
- browser-only architecture
- workflow DSL before the runtime primitives are stable
- leaking Android capabilities into the core package

## Architecture Boundary

### `automation_core`

Allowed:

- driver lifecycle contracts
- task lifecycle and cancellation
- structured events
- config source and validation contracts
- retry policies
- generic action primitives
- artifact handling

Forbidden:

- business selectors
- app package names
- target URLs
- order/publish/review flows
- AI prompt logic
- captcha logic
- console UI/routes

### Adapters

Adapters may know target apps and frameworks.

Examples:

- Damai web adapter
- Damai Android adapter
- future Dianping examples

### Examples

Examples show how to compose the core for one business domain without moving
business logic into `automation_core`.

## Documentation Set

Keep these documents distinct:

1. `docs/automation-kit-development-system.md`
   - system-wide decisions and boundaries
2. `docs/automation-kit-technical-landscape.md`
   - GitHub research and design tradeoffs
3. `docs/superpowers/specs/*`
   - validated product/design specs
4. `docs/superpowers/plans/*`
   - step-by-step implementation plans

## Development Rules

1. Keep `automation_core` business-agnostic.
2. Keep retry behavior bounded by default.
3. Do not catch `BaseException` in retry helpers unless interruption is
   re-raised immediately.
4. Make live browser/device tests opt-in.
5. Keep diffs small and phase work so each change has one clear consumer.
6. Prefer deterministic artifacts and logs over hidden automation state.

## Phase Roadmap

### Phase 0: New Repository Bootstrap

- create the `automation-kit` repo
- define package layout
- set up baseline tests and coverage
- add core skeleton

### Phase 1: Retry and Task Foundations

- add bounded retry primitives
- define task lifecycle primitives
- prove one low-risk consumer path

### Phase 2: Driver Contracts

- add browser and Android session abstractions
- wire adapters through the contracts

### Phase 3: Artifacts and Observability

- add structured events
- add run artifacts
- add debug snapshots and reports

### Phase 4: Examples

- add Damai and other example adapters
- keep them thin and domain-specific

## Verification Baseline

- unit tests for core behavior
- import tests for package presence
- no-live-system by default
- optional browser/device integration tests
- coverage for the new core package

## Review Gate

Before any implementation phase:

- confirm the target repository path
- confirm the package name
- confirm the first consumer path
- confirm live-system test policy
- confirm the retry contract boundary

