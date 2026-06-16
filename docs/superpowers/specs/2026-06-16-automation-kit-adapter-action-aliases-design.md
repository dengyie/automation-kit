# Adapter Action Aliases Design

## Goal

Give Selenium and Appium adapter sessions a small, stable set of
business-agnostic action names that workflow authors can use before reaching
for raw driver APIs.

## Problem

Adapters currently pass most action names directly to concrete driver methods.
That is useful as an escape hatch, but it makes simple workflows depend on
Selenium/Appium method names. The project needs a thin common vocabulary for
basic web and Android automation while keeping `automation_core` free of
platform-specific concepts.

## Proposed Shape

Add adapter-layer aliases only:

- Selenium:
  - `open(url=...)`
  - `click(selector=..., by="css selector")`
  - `type_text(selector=..., text=..., by="css selector", clear=True)`
- Appium:
  - `tap(x=..., y=...)`
  - `tap(selector=..., by="accessibility id")`
  - `type_text(selector=..., text=..., by="accessibility id", clear=True)`

Unknown actions continue to use the existing driver-method fallback.

## Boundaries

- No changes to `automation_core`.
- No imports from Selenium or Appium packages.
- No Damai, Dianping, selector, URL, package-name, order, or review logic.
- No live browser or device requirement in default tests.

## Testing Strategy

- Add fake driver and fake element tests for alias behavior.
- Verify focused adapter tests fail before implementation and pass after.
- Run the full suite and production review scripts.
